"""Automatic imports: remembered column mappings and link sources that are fetched on a schedule."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    WorkspaceScopedMixin,
)


class MappingProfile(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """A column mapping the owner confirmed, found again by the file's header fingerprint."""

    __tablename__ = "mapping_profiles"
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)

    fingerprint: Mapped[str] = mapped_column(String(64))  # sha256 of the normalised, sorted headers
    name: Mapped[str] = mapped_column(String(200))
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON)  # {"fields": {...}, "date_order": "dmy"}
    uses: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportSource(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """A public link (for example a published Google Sheet) fetched into the workspace."""

    __tablename__ = "import_sources"

    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(600))
    schedule: Mapped[str] = mapped_column(String(10), default="daily")  # manual | hourly | daily
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(
        String(12), default="never"
    )  # never, running, ok, unchanged, failed
    last_message: Mapped[str | None] = mapped_column(Text)
    last_hash: Mapped[str | None] = mapped_column(String(64))
    last_new_orders: Mapped[int] = mapped_column(Integer, default=0)
    failures: Mapped[int] = mapped_column(Integer, default=0)  # consecutive
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class SourceRun(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, CreatedAtMixin, Base):
    __tablename__ = "source_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_sources.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(12))
    message: Mapped[str | None] = mapped_column(Text)
    new_orders: Mapped[int] = mapped_column(Integer, default=0)
    rows_total: Mapped[int | None] = mapped_column(Integer)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="SET NULL")
    )
