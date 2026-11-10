"""Targets for a shop: reach this much of a measure by the end of a period, or keep a measure under a limit."""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class Goal(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "goals"

    name: Mapped[str] = mapped_column(String(120))
    metric: Mapped[str] = mapped_column(
        String(30)
    )  # net_sales | orders | gross_profit | gross_margin | aov | discount_rate | udhaar_overdue
    target: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10), default="at_least")  # at_least | at_most
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
