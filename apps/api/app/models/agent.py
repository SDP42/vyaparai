"""Agent runs and their step-by-step trace. Read-only workflows: they never change business data."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class AgentRun(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    workflow: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(10), default="running")  # running | done | failed
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentStep.position"
    )


class AgentStep(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "agent_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    node: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(10))  # ok | failed | skipped
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    summary: Mapped[str] = mapped_column(String(300), default="")
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    ms: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[AgentRun] = relationship(back_populates="steps")


class AgentSchedule(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Which automation agents run on their own each day, and at what local hour."""

    __tablename__ = "agent_schedules"
    __table_args__ = (UniqueConstraint("workspace_id", "workflow"),)

    workflow: Mapped[str] = mapped_column(String(40))
    enabled: Mapped[bool] = mapped_column(default=True)
    hour: Mapped[int] = mapped_column(default=8)
    last_run_for: Mapped[date | None] = mapped_column(Date)
