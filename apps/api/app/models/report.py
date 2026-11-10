"""Saved reports: a frozen snapshot of the numbers at the time it was made, so it can be reopened and printed."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class SavedReport(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "saved_reports"

    title: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20), default="business_summary")
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
