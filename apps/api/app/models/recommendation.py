"""Suggested actions for the owner, each with its reasons, an impact range and an approval state."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class Recommendation(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("workspace_id", "key"),)

    key: Mapped[str] = mapped_column(
        String(120)
    )  # kind plus what it is about; stable across refreshes
    kind: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(200))
    why: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    impact: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # low, expected, high, basis, assumptions
    effort: Mapped[str] = mapped_column(String(1))  # S | M | L
    confidence: Mapped[str] = mapped_column(String(8))  # high | medium | low
    score: Mapped[float] = mapped_column(Float, default=0.0)
    link: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(
        String(10), default="proposed", index=True
    )  # proposed | approved | done | dismissed | stale
    note: Mapped[str | None] = mapped_column(String(300))
    first_seen: Mapped[date] = mapped_column(Date)
    last_seen: Mapped[date] = mapped_column(Date)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
