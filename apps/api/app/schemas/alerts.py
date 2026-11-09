import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AlertRead(ORMModel):
    id: uuid.UUID
    key: str
    rule: str
    severity: str
    title: str
    detail: str
    evidence: dict[str, Any]
    link: str
    status: str
    first_seen: date
    last_seen: date


class AlertList(BaseModel):
    as_of: date | None
    counts: dict[str, int]
    items: list[AlertRead]
