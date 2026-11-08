"""Datasets and jobs: upload → inspect → map → validate → import.

POST /workspaces/{id}/datasets                    upload CSV/XLSX (analyst+)
GET  /workspaces/{id}/datasets                    list
GET  /workspaces/{id}/datasets/{dataset_id}       detail incl. inspection + validation
PUT  /workspaces/{id}/datasets/{dataset_id}/mapping
POST /workspaces/{id}/datasets/{dataset_id}/validate
GET  /workspaces/{id}/datasets/{dataset_id}/errors.csv
POST /workspaces/{id}/datasets/{dataset_id}/import   → 202 + job
GET  /workspaces/{id}/jobs/{job_id}
GET  /workspaces/{id}/data-summary
"""

import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import AnalystCtx, AppSettings, DbSession, ViewerCtx
from app.core.errors import NotFoundError
from app.models.dataset import Dataset, Job
from app.repositories.datasets import DatasetRepository, JobRepository
from app.schemas.common import Page
from app.schemas.dataset import DatasetDetail, DatasetRead, DataSummary, JobRead, MappingIn
from app.services import datasets as service
from app.services.ingestion.pipeline import iter_error_csv, validate_file

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["datasets"])


def _get(db: DbSession, workspace_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
    dataset = DatasetRepository(db, workspace_id).get(dataset_id)
    if dataset is None:
        raise NotFoundError("Dataset not found")
    return dataset


@router.post("/datasets", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    ctx: AnalystCtx,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File(description="CSV or XLSX export, one row per order line")],
    name: Annotated[str | None, Form(max_length=200)] = None,
) -> Dataset:
    return await service.create_dataset(db, settings, ctx.workspace, ctx.user, file, name)


@router.get("/datasets", response_model=Page[DatasetRead])
def list_datasets(
    ctx: ViewerCtx,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[DatasetRead]:
    repo = DatasetRepository(db, ctx.workspace_id)
    items = [DatasetRead.model_validate(d) for d in repo.list(limit=limit, offset=offset)]
    return Page(items=items, total=repo.count(), limit=limit, offset=offset)


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Dataset:
    return _get(db, ctx.workspace_id, dataset_id)


@router.put("/datasets/{dataset_id}/mapping", response_model=DatasetDetail)
def save_mapping(dataset_id: uuid.UUID, body: MappingIn, ctx: AnalystCtx, db: DbSession) -> Dataset:
    dataset = _get(db, ctx.workspace_id, dataset_id)
    return service.save_mapping(db, dataset, ctx.user, body.fields, body.date_order)


@router.post("/datasets/{dataset_id}/validate")
def validate_dataset(
    dataset_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, settings: AppSettings
) -> dict[str, Any]:
    dataset = _get(db, ctx.workspace_id, dataset_id)
    return service.run_validation(db, settings, dataset)


@router.get("/datasets/{dataset_id}/errors.csv", response_class=StreamingResponse)
def download_errors(
    dataset_id: uuid.UUID, ctx: ViewerCtx, db: DbSession, settings: AppSettings
) -> StreamingResponse:
    dataset = _get(db, ctx.workspace_id, dataset_id)
    if not dataset.column_mapping or dataset.status.value == "uploaded":
        raise service.PreconditionError("Confirm the column mapping first")
    v = validate_file(
        Path(dataset.storage_path or ""),
        dataset.file_type or "csv",
        dataset.column_mapping,
        settings.max_upload_rows,
    )
    filename = f"{Path(dataset.source_filename).stem}_errors.csv"
    return StreamingResponse(
        iter_error_csv(v),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/datasets/{dataset_id}/import", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED
)
def import_dataset(
    dataset_id: uuid.UUID,
    ctx: AnalystCtx,
    db: DbSession,
    settings: AppSettings,
    background: BackgroundTasks,
) -> Job:
    dataset = _get(db, ctx.workspace_id, dataset_id)
    job = service.start_import(db, dataset, ctx.user)
    if job.status.value == "queued":
        background.add_task(service.run_import_job, db.get_bind(), job.id, settings.max_upload_rows)  # type: ignore[arg-type]
    return job


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Job:
    job = JobRepository(db, ctx.workspace_id).get(job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return job


@router.get("/data-summary", response_model=DataSummary)
def data_summary(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.data_summary(db, ctx.workspace_id)
