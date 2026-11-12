"""Small daily records a shop keeps by hand: expenses, the day-end cash count, and items about to expire."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin

Money = Numeric(14, 2)


class Expense(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "expenses"

    spent_on: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(
        String(20)
    )  # rent | electricity | salary | transport | tea | repairs | supplies | other
    amount: Mapped[Decimal] = mapped_column(Money)
    paid_by: Mapped[str] = mapped_column(String(10), default="cash")  # cash | upi | card | bank
    note: Mapped[str | None] = mapped_column(String(200))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class DayClose(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """The galla tally at the end of a day: what should be in the drawer against what is."""

    __tablename__ = "day_closes"
    __table_args__ = (UniqueConstraint("workspace_id", "day"),)

    day: Mapped[date] = mapped_column(Date, index=True)
    opening_cash: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    cash_sales: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    upi_sales: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    card_sales: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    taken_out: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))  # banked or taken home
    counted_cash: Mapped[Decimal] = mapped_column(Money)
    note: Mapped[str | None] = mapped_column(String(200))
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class ExpiryItem(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    """A reminder list of stock that will expire; not a pharmacy register."""

    __tablename__ = "expiry_items"

    name: Mapped[str] = mapped_column(String(160))
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="SET NULL")
    )
    batch: Mapped[str | None] = mapped_column(String(40))
    expires_on: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    note: Mapped[str | None] = mapped_column(String(200))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleared_how: Mapped[str | None] = mapped_column(
        String(20)
    )  # sold | returned | discounted | thrown
