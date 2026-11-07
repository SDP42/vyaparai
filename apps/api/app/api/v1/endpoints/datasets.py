"""Dataset and job read endpoints.

Upload, mapping and import (POST) arrive in Phase 1 — see docs/ROADMAP.md.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ViewerCtx
from app.core.errors import NotFoundError
from app.models.dataset import Dataset, Job
from app.repositories.datasets import DatasetRepository, JobRepository
from app.schemas.common import Page
from app.schemas.dataset import DatasetRead, JobRead

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["datasets"])


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


@router.get("/datasets/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Dataset:
    dataset = DatasetRepository(db, ctx.workspace_id).get(dataset_id)
    if dataset is None:
        raise NotFoundError("Dataset not found")
    return dataset


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> Job:
    job = JobRepository(db, ctx.workspace_id).get(job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return job
