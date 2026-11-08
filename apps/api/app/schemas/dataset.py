import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.dataset import DatasetStatus, JobStatus, JobType
from app.schemas.common import ORMModel


class DatasetRead(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    source_filename: str
    file_type: str | None
    file_size_bytes: int | None
    row_count: int | None
    status: DatasetStatus
    column_mapping: dict[str, Any] | None
    created_at: datetime


class DatasetDetail(DatasetRead):
    inspection: dict[str, Any] | None
    validation: dict[str, Any] | None


class MappingIn(BaseModel):
    fields: dict[str, str | None] = Field(description="Canonical field → source column name")
    date_order: Literal["dmy", "mdy", "ymd"] = "dmy"


class JobRead(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    job_type: JobType
    status: JobStatus
    dataset_id: uuid.UUID | None
    progress: int
    rows_total: int | None
    rows_accepted: int | None
    rows_rejected: int | None
    error_message: str | None
    result: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class DataSummary(BaseModel):
    orders: int
    order_items: int
    products: int
    customers: int
    date_from: str | None
    date_to: str | None
    net_sales_completed: str


class AuditLogRead(ORMModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict[str, Any] | None
    request_id: str | None
    created_at: datetime
