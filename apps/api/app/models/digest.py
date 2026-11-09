"""Owner digest: per-workspace delivery settings and a history of what was generated."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    WorkspaceScopedMixin,
)


class DigestSettings(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "digest_settings"

    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    frequency: Mapped[str] = mapped_column(String(10), default="daily")  # daily | weekly | both
    send_hour: Mapped[int] = mapped_column(Integer, default=8)  # local hour, 0-23
    weekday: Mapped[int] = mapped_column(Integer, default=0)  # for weekly digests, 0 = Monday
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_daily_for: Mapped[date | None] = mapped_column(Date)  # local date already handled
    last_weekly_for: Mapped[date | None] = mapped_column(Date)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class Digest(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, CreatedAtMixin, Base):
    __tablename__ = "digests"

    kind: Mapped[str] = mapped_column(String(10))  # daily | weekly
    period_end: Mapped[date] = mapped_column(Date)
    subject: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    sent_to: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20))  # sent | not_configured | failed | stored
    error: Mapped[str | None] = mapped_column(Text)
