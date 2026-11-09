import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class DigestPreview(BaseModel):
    kind: Literal["daily", "weekly"]
    as_of: date
    label: str
    subject: str
    versus: str
    headline: list[dict[str, Any]]
    action: dict[str, str]
    more_actions: list[dict[str, str]]
    watch: str | None
    notes: list[str]
    stale_days: int
    text: str
    html: str


class DigestSettingsIn(BaseModel):
    enabled: bool
    frequency: Literal["daily", "weekly", "both"]
    send_hour: int = Field(ge=0, le=23)
    weekday: int = Field(ge=0, le=6)
    recipients: list[EmailStr] = Field(max_length=5)


class DigestSettingsOut(BaseModel):
    enabled: bool
    frequency: str
    send_hour: int
    weekday: int
    recipients: list[str]
    email_configured: bool
    timezone: str
    last_daily_for: date | None
    last_weekly_for: date | None


class DigestRead(ORMModel):
    id: uuid.UUID
    kind: str
    period_end: date
    subject: str
    text: str
    status: str
    sent_to: list[str]
    error: str | None
    created_at: datetime
