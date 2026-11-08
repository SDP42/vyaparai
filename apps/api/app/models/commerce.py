"""Commerce core: products, customers, orders and line items.

Money is stored as ``Numeric`` (never float). Quantity is ``Numeric`` too so loose goods
sold by weight (common in Indian kirana stores) are representable.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin

Money = Numeric(14, 2)
Quantity = Numeric(12, 3)


class OrderStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Product(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("workspace_id", "sku"),)

    sku: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Money)
    list_price: Mapped[Decimal | None] = mapped_column(Money)
    active: Mapped[bool] = mapped_column(default=True)


class Customer(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """Deliberately minimal PII: an external key and coarse location only."""

    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("workspace_id", "external_key"),)

    external_key: Mapped[str] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    marketing_consent: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(32), default="active")


class Order(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("workspace_id", "external_key"),
        Index("ix_orders_workspace_id_order_date", "workspace_id", "order_date"),
        Index("ix_orders_workspace_id_business_date", "workspace_id", "business_date"),
    )

    external_key: Mapped[str] = mapped_column(String(120))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="SET NULL"), index=True
    )
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Calendar day in the workspace timezone when the order was placed; analytics buckets by this.
    business_date: Mapped[date] = mapped_column(Date)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],
            validate_strings=True,
        ),
        default=OrderStatus.COMPLETED,
    )
    channel: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    shipping_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class OrderItem(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Quantity)
    unit_price: Mapped[Decimal] = mapped_column(Money)
    discount_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    unit_cost_snapshot: Mapped[Decimal | None] = mapped_column(Money)
