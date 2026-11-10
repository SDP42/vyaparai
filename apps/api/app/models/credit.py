"""Udhaar (credit) ledger: money customers owe the shop, and what they paid back."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class CreditEntry(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "credit_entries"
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)

    fingerprint: Mapped[str] = mapped_column(String(64))  # makes re-importing a file safe
    party_key: Mapped[str] = mapped_column(String(120), index=True)  # normalised name
    party_name: Mapped[str] = mapped_column(String(120))  # as written
    phone: Mapped[str | None] = mapped_column(
        String(15)
    )  # digits only; used to open WhatsApp, never sent by us
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(8))  # credit (they owe more) | payment (they paid)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | import
