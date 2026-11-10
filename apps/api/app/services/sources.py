"""Link sources: fetch a published sheet or file on a schedule and import what is new."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError
from app.models.dataset import Dataset, DatasetStatus, Job, JobStatus, JobType
from app.models.source import ImportSource, SourceRun
from app.models.workspace import Workspace
from app.services import mapping_profiles, safe_fetch
from app.services.datasets import run_import_job
from app.services.ingestion.pipeline import (
    MappingError,
    inspect_file,
    validate_file,
    validate_mapping,
)
from app.services.ingestion.reader import detect_type

SCHEDULES = {"manual": None, "hourly": timedelta(hours=1), "daily": timedelta(hours=23)}
PAUSE_AFTER_FAILURES = 5
KEEP_RUNS = 20


class TooManySourcesError(AppError):
    status_code = 422
    code = "too_many_sources"


def validate_link(url: str) -> str:
    """Check a link without touching the network and return its normalised form."""
    norm = safe_fetch.normalise_url(url)
    s = get_settings()
    import urllib.parse

    p = urllib.parse.urlparse(norm)
    if p.scheme != "https":
        raise safe_fetch.UnsafeUrlError("The link must start with https://")
    if p.username or p.password or "@" in (p.netloc or ""):
        raise safe_fetch.UnsafeUrlError("The link must not contain a user name or password.")
    host = (p.hostname or "").lower()
    if not host:
        raise safe_fetch.UnsafeUrlError("The link has no address.")
    if not s.source_allow_any_public_host and not safe_fetch._host_allowed(
        host, s.source_allowed_hosts
    ):
        raise safe_fetch.UnsafeUrlError(
            "That site is not on the allowed list. Use a Google Sheets, Drive or Dropbox link."
        )
    return norm


def create_source(
    db: Session, ws: uuid.UUID, user_id: uuid.UUID | None, name: str, url: str, schedule: str
) -> ImportSource:
    n = (
        db.scalar(
            select(func.count()).select_from(ImportSource).where(ImportSource.workspace_id == ws)
        )
        or 0
    )
    if n >= get_settings().max_sources_per_workspace:
        raise TooManySourcesError(
            f"You can connect up to {get_settings().max_sources_per_workspace} links."
        )
    src = ImportSource(
        workspace_id=ws,
        name=name.strip()[:120],
        url=validate_link(url),
        schedule=schedule,
        created_by_id=user_id,
    )
    db.add(src)
    db.commit()
    return src


def is_due(src: ImportSource, now: datetime) -> bool:
    gap = SCHEDULES.get(src.schedule)
    if not src.enabled or gap is None or src.last_status == "running":
        return False
    if src.last_run_at is None:
        return True
    last = src.last_run_at if src.last_run_at.tzinfo else src.last_run_at.replace(tzinfo=UTC)
    return now - last >= gap


def _finish(
    db: Session,
    src: ImportSource,
    run: SourceRun,
    status: str,
    message: str,
    *,
    new_orders: int = 0,
    total: int | None = None,
    dataset_id: uuid.UUID | None = None,
) -> None:
    now = datetime.now(UTC)
    run.status, run.message, run.new_orders, run.rows_total, run.dataset_id = (
        status,
        message,
        new_orders,
        total,
        dataset_id,
    )
    src.last_run_at, src.last_status, src.last_message, src.last_new_orders = (
        now,
        status,
        message,
        new_orders,
    )
    if status == "failed":
        src.failures += 1
        if src.failures >= PAUSE_AFTER_FAILURES:
            src.enabled = False
            src.last_message = f"{message} Paused after {PAUSE_AFTER_FAILURES} failed tries."
    else:
        src.failures = 0
    old = db.scalars(
        select(SourceRun.id)
        .where(SourceRun.source_id == src.id)
        .order_by(SourceRun.created_at.desc())
        .offset(KEEP_RUNS)
    ).all()
    for rid in old:
        r = db.get(SourceRun, rid)
        if r is not None:
            db.delete(r)
    db.commit()


def run_source(engine: Engine, source_id: uuid.UUID, *, fetcher: Any = None) -> None:
    """Fetch one source and import any new orders. Safe to run in the background."""
    settings = get_settings()
    with Session(bind=engine, expire_on_commit=False) as db:
        src = db.get(ImportSource, source_id)
        if src is None:
            return
        ws = db.get(Workspace, src.workspace_id)
        if ws is None:
            return
        src.last_status = "running"
        run = SourceRun(workspace_id=src.workspace_id, source_id=src.id, status="running")
        db.add(run)
        db.commit()
        try:
            body, digest = (fetcher or safe_fetch.fetch)(
                src.url, max_bytes=settings.max_upload_size_mb * 1024 * 1024
            )
            if digest == src.last_hash:
                _finish(db, src, run, "unchanged", "No new data since the last check.")
                return
            known = db.scalars(
                select(Dataset).where(Dataset.workspace_id == ws.id, Dataset.file_hash == digest)
            ).first()
            if known is not None:
                src.last_hash = digest
                _finish(
                    db,
                    src,
                    run,
                    "unchanged",
                    "This exact file was already imported.",
                    dataset_id=known.id,
                )
                return
            file_type = detect_type(
                "source.xlsx" if body[:2] == b"PK" else "source.csv", body[:8192]
            )
            root = Path(settings.storage_dir).resolve() / str(ws.id)
            root.mkdir(parents=True, exist_ok=True)
            dataset_id = uuid.uuid4()
            path = root / f"{dataset_id}.{file_type}"
            path.write_bytes(body)
            try:
                inspection = inspect_file(path, file_type, settings.max_upload_rows)
                headers: list[str] = inspection["headers"]
                profile = mapping_profiles.find(db, ws.id, headers)
                mapping = mapping_profiles.usable(profile, headers) if profile else None
                if mapping is None:
                    mapping = {"fields": inspection["suggested_mapping"], "date_order": "dmy"}
                try:
                    validate_mapping({"fields": mapping["fields"]}, headers)
                except MappingError as exc:
                    raise AppError(
                        f"Some columns could not be matched ({exc}). Upload this file once by hand and confirm the columns; we will remember them."
                    ) from exc
                v = validate_file(path, file_type, mapping, settings.max_upload_rows)
            except Exception:
                path.unlink(missing_ok=True)
                raise
            summary = v.summary()
            if summary["rows_valid"] == 0:
                path.unlink(missing_ok=True)
                raise AppError("None of the rows could be read with the saved column mapping.")
            if profile is not None:
                mapping_profiles.mark_used(profile)
            dataset = Dataset(
                id=dataset_id, workspace_id=ws.id, name=f"{src.name} ({datetime.now(UTC):%d %b %H:%M})"[:200],
                source_filename=f"{src.name}.{file_type}"[:255], file_hash=digest, file_size_bytes=len(body),
                file_type=file_type, storage_path=str(path), row_count=inspection["row_count"],
                status=DatasetStatus.VALIDATED, inspection=inspection, column_mapping=mapping,
                validation=summary, created_by_id=src.created_by_id,
            )  # fmt: skip
            db.add(dataset)
            job = Job(
                workspace_id=ws.id,
                job_type=JobType.IMPORT,
                status=JobStatus.QUEUED,
                dataset_id=dataset.id,
                rows_total=dataset.row_count,
                created_by_id=src.created_by_id,
            )
            db.add(job)
            src.last_hash = digest
            db.commit()
            run_import_job(engine, job.id, settings.max_upload_rows)
            db.refresh(job)
            if job.status != JobStatus.SUCCEEDED:
                raise AppError(job.error_message or "The import did not finish.")
            created = int((job.result or {}).get("orders_created", 0))
            skipped = int((job.result or {}).get("duplicate_orders_skipped", 0))
            msg = (
                f"{created} new orders added"
                + (f"; {skipped} already known" if skipped else "")
                + "."
            )
            _finish(
                db,
                src,
                run,
                "ok",
                msg,
                new_orders=created,
                total=job.rows_accepted,
                dataset_id=dataset.id,
            )
        except ConflictError:
            db.rollback()
            _finish(db, src, run, "unchanged", "This exact file was already imported.")
        except Exception as exc:
            db.rollback()
            src = db.get(ImportSource, source_id)
            run = db.get(SourceRun, run.id) or run
            if src is not None:
                _finish(db, src, run, "failed", safe_fetch.describe(exc))


def run_due(
    engine: Engine, now: datetime | None = None, *, fetcher: Any = None
) -> list[dict[str, Any]]:
    """Fetch every source whose schedule says it is due. Used by ``python -m app.import_runner``."""
    now = now or datetime.now(UTC)
    with Session(bind=engine, expire_on_commit=False) as db:
        due = [s.id for s in db.scalars(select(ImportSource)).all() if is_due(s, now)]
    out = []
    for sid in due:
        run_source(engine, sid, fetcher=fetcher)
        with Session(bind=engine) as db:
            s = db.get(ImportSource, sid)
            out.append(
                {
                    "source": str(sid),
                    "status": s.last_status if s else "gone",
                    "message": s.last_message if s else None,
                }
            )
    return out
