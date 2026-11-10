import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

Schedule = Literal["manual", "hourly", "daily"]


class SourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=600)
    schedule: Schedule = "daily"


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    schedule: Schedule | None = None
    enabled: bool | None = None


class SourceRead(ORMModel):
    id: uuid.UUID
    name: str
    url: str
    schedule: str
    enabled: bool
    last_run_at: datetime | None
    last_status: str
    last_message: str | None
    last_new_orders: int
    failures: int
    created_at: datetime


class SourceRunRead(ORMModel):
    id: uuid.UUID
    status: str
    message: str | None
    new_orders: int
    rows_total: int | None
    created_at: datetime
