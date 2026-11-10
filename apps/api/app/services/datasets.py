"""Dataset lifecycle: upload → inspect → map → validate → import (background job)."""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ConflictError
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.user import User
from app.models.workspace import Workspace
from app.services import audit, mapping_profiles
from app.services.ingestion.pipeline import (
    import_lines,
    inspect_file,
    validate_file,
    validate_mapping,
)
from app.services.ingestion.reader import FileTooLargeError, detect_type

logger = logging.getLogger(__name__)
_READ_CHUNK = 1024 * 1024


class PreconditionError(AppError):
    status_code = 409
    code = "invalid_state"


def _storage_path(
    settings: Settings, workspace_id: uuid.UUID, dataset_id: uuid.UUID, ext: str
) -> Path:
    root = Path(settings.storage_dir).resolve() / str(workspace_id)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{dataset_id}.{ext}"


async def create_dataset(
    db: Session,
    settings: Settings,
    workspace: Workspace,
    user: User,
    upload: UploadFile,
    name: str | None,
) -> Dataset:
    filename = Path(upload.filename or "upload").name[:255]
    limit = settings.max_upload_size_mb * 1024 * 1024
    head = await upload.read(8192)
    file_type = detect_type(filename, head)

    # Stream to a temp file while hashing and enforcing the size limit.
    dataset_id = uuid.uuid4()
    target = _storage_path(settings, workspace.id, dataset_id, file_type)
    tmp = target.with_suffix(".part")
    digest = hashlib.sha256()
    size = 0
    try:
        with tmp.open("wb") as fh:
            chunk = head
            while chunk:
                size += len(chunk)
                if size > limit:
                    raise FileTooLargeError(f"File is larger than {settings.max_upload_size_mb} MB")
                digest.update(chunk)
                fh.write(chunk)
                chunk = await upload.read(_READ_CHUNK)
        if size == 0:
            raise AppError("The file is empty")
        file_hash = digest.hexdigest()
        existing = db.scalars(
            select(Dataset).where(
                Dataset.workspace_id == workspace.id, Dataset.file_hash == file_hash
            )
        ).one_or_none()
        if existing is not None:
            raise ConflictError(
                "This exact file was already uploaded",
                details={
                    "dataset_id": str(existing.id),
                    "name": existing.name,
                    "status": existing.status.value,
                },
            )
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)

    try:
        inspection = inspect_file(target, file_type, settings.max_upload_rows)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace.id,
        name=(name or Path(filename).stem)[:200],
        source_filename=filename,
        file_hash=file_hash,
        file_size_bytes=size,
        file_type=file_type,
        storage_path=str(target),
        row_count=inspection["row_count"],
        status=DatasetStatus.UPLOADED,
        inspection=inspection,
        column_mapping=remembered_or_suggested(db, workspace.id, inspection),
        created_by_id=user.id,
    )
    db.add(dataset)
    audit.record(
        db,
        action="dataset.uploaded",
        actor_user_id=user.id,
        workspace_id=workspace.id,
        entity_type="dataset",
        entity_id=dataset.id,
        details={"filename": filename, "rows": inspection["row_count"], "bytes": size},
    )
    db.commit()
    return dataset


def remembered_or_suggested(
    db: Session, ws: uuid.UUID, inspection: dict[str, Any]
) -> dict[str, Any]:
    """The mapping confirmed for this exact file layout before, else our best guess."""
    headers: list[str] = inspection["headers"]
    profile = mapping_profiles.find(db, ws, headers)
    saved = mapping_profiles.usable(profile, headers) if profile else None
    if profile is not None and saved is not None:
        mapping_profiles.mark_used(profile)
        return {**saved, "remembered": True, "profile_name": profile.name}
    return {"fields": inspection["suggested_mapping"], "date_order": "dmy", "suggested": True}


def save_mapping(
    db: Session, dataset: Dataset, user: User, fields: dict[str, str | None], date_order: str
) -> Dataset:
    if dataset.status == DatasetStatus.IMPORTED:
        raise PreconditionError("This dataset has already been imported")
    headers: list[str] = (dataset.inspection or {}).get("headers", [])
    clean = {k: v for k, v in fields.items() if v}
    validate_mapping({"fields": clean}, headers)
    dataset.column_mapping = {"fields": clean, "date_order": date_order}
    mapping_profiles.remember(
        db, dataset.workspace_id, headers, {"fields": clean, "date_order": date_order}, dataset.name
    )  # next file with these columns is recognised
    dataset.validation = None
    dataset.status = DatasetStatus.MAPPED
    audit.record(
        db,
        action="dataset.mapped",
        actor_user_id=user.id,
        workspace_id=dataset.workspace_id,
        entity_type="dataset",
        entity_id=dataset.id,
        details={"fields": sorted(clean)},
    )
    db.commit()
    return dataset


def run_validation(db: Session, settings: Settings, dataset: Dataset) -> dict[str, Any]:
    if dataset.status == DatasetStatus.IMPORTED:
        raise PreconditionError("This dataset has already been imported")
    if dataset.status == DatasetStatus.UPLOADED or not dataset.column_mapping:
        raise PreconditionError("Confirm the column mapping before validating")
    v = validate_file(
        Path(dataset.storage_path or ""),
        dataset.file_type or "csv",
        dataset.column_mapping,
        settings.max_upload_rows,
    )
    summary = v.summary()
    dataset.validation = summary
    dataset.status = DatasetStatus.VALIDATED if summary["rows_valid"] > 0 else DatasetStatus.MAPPED
    db.commit()
    return summary


def start_import(db: Session, dataset: Dataset, user: User) -> Job:
    if dataset.status == DatasetStatus.IMPORTED:
        raise PreconditionError("This dataset has already been imported")
    if dataset.status != DatasetStatus.VALIDATED:
        raise PreconditionError("Validate the dataset before importing")
    running = db.scalars(
        select(Job).where(
            Job.dataset_id == dataset.id, Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])
        )
    ).first()
    if running is not None:
        return running
    job = Job(
        workspace_id=dataset.workspace_id,
        job_type=JobType.IMPORT,
        status=JobStatus.QUEUED,
        dataset_id=dataset.id,
        rows_total=dataset.row_count,
        created_by_id=user.id,
    )
    db.add(job)
    audit.record(
        db,
        action="dataset.import_started",
        actor_user_id=user.id,
        workspace_id=dataset.workspace_id,
        entity_type="dataset",
        entity_id=dataset.id,
    )
    db.commit()
    return job


def run_import_job(engine: Engine, job_id: uuid.UUID, max_rows: int) -> None:
    """Background task: re-validate, import in one transaction, record the outcome on the job."""
    with Session(bind=engine, expire_on_commit=False) as db:
        job = db.get(Job, job_id)
        if job is None or job.dataset_id is None:
            return
        dataset = db.get(Dataset, job.dataset_id)
        workspace = db.get(Workspace, job.workspace_id)
        if dataset is None or workspace is None:
            return
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.progress = 10
        db.commit()
        try:
            v = validate_file(
                Path(dataset.storage_path or ""),
                dataset.file_type or "csv",
                dataset.column_mapping or {},
                max_rows,
            )
            res = import_lines(
                db,
                workspace_id=workspace.id,
                dataset_id=dataset.id,
                currency=workspace.currency,
                timezone=workspace.timezone,
                validation=v,
            )
            dataset.status = DatasetStatus.IMPORTED
            dataset.validation = v.summary()
            job.status = JobStatus.SUCCEEDED
            job.progress = 100
            job.rows_accepted = res.lines_imported
            job.rows_rejected = res.rows_rejected
            job.result = {
                "orders_created": res.orders_created,
                "lines_imported": res.lines_imported,
                "products_created": res.products_created,
                "customers_created": res.customers_created,
                "duplicate_orders_skipped": res.duplicate_orders,
            }
            job.finished_at = datetime.now(UTC)
            audit.record(
                db,
                action="dataset.imported",
                actor_user_id=job.created_by_id,
                workspace_id=workspace.id,
                entity_type="dataset",
                entity_id=dataset.id,
                details=job.result,
            )
            db.commit()
        except Exception as exc:  # record any failure on the job; never leave it "running"
            db.rollback()
            logger.exception("Import job %s failed", job_id)
            job = db.get(Job, job_id)
            dataset = db.get(Dataset, dataset.id)
            if job is not None:
                job.status = JobStatus.FAILED
                job.error_message = str(getattr(exc, "message", exc))[:1000]
                job.finished_at = datetime.now(UTC)
            if dataset is not None:
                dataset.status = DatasetStatus.FAILED
            db.commit()


def data_summary(db: Session, workspace_id: uuid.UUID) -> dict[str, Any]:
    def count(model: Any) -> int:
        return int(
            db.scalar(
                select(func.count()).select_from(model).where(model.workspace_id == workspace_id)
            )
            or 0
        )

    first, last = db.execute(
        select(func.min(Order.business_date), func.max(Order.business_date)).where(
            Order.workspace_id == workspace_id
        )
    ).one()
    net = db.scalar(
        select(
            func.coalesce(
                func.sum(OrderItem.quantity * OrderItem.unit_price - OrderItem.discount_amount), 0
            )
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(OrderItem.workspace_id == workspace_id, Order.status == OrderStatus.COMPLETED)
    )
    return {
        "orders": count(Order),
        "order_items": count(OrderItem),
        "products": count(Product),
        "customers": count(Customer),
        "date_from": first.isoformat() if first else None,
        "date_to": last.isoformat() if last else None,
        "net_sales_completed": str(round(float(net or 0), 2)),
    }
