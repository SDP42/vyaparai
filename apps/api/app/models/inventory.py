"""Stock on hand (as dated snapshots) and per-product ordering settings."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class StockSnapshot(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Units on the shelf on a date. History is kept so stock movement can be shown later."""

    __tablename__ = "stock_snapshots"
    __table_args__ = (UniqueConstraint("product_id", "as_of"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)
    on_hand: Mapped[Decimal] = mapped_column(Numeric(14, 3))


class InventorySetting(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """How a product is ordered: days to deliver, pack size and a safety buffer."""

    __tablename__ = "inventory_settings"
    __table_args__ = (UniqueConstraint("product_id"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, default=3)
    safety_days: Mapped[int] = mapped_column(Integer, default=2)
    pack_size: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal(1))
