"""Supplier purchase bills and their lines. A confirmed bill feeds supplier price history."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class PurchaseBill(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "purchase_bills"

    status: Mapped[str] = mapped_column(
        String(12), default="draft", index=True
    )  # draft | confirmed
    supplier: Mapped[str | None] = mapped_column(String(160))
    gstin: Mapped[str | None] = mapped_column(String(15))
    bill_no: Mapped[str | None] = mapped_column(String(40))
    bill_date: Mapped[date | None] = mapped_column(Date, index=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    engine: Mapped[str] = mapped_column(String(20), default="")  # pdf-text | rapidocr | tesseract
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    warnings: Mapped[str] = mapped_column(Text, default="")  # newline-separated
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )

    lines: Mapped[list["PurchaseBillLine"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", order_by="PurchaseBillLine.position"
    )


class PurchaseBillLine(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "purchase_bill_lines"

    bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_bills.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4))  # what the shop paid per unit
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    unit: Mapped[str | None] = mapped_column(String(12))
    confidence: Mapped[str] = mapped_column(String(8), default="high")
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="SET NULL"), index=True
    )

    bill: Mapped[PurchaseBill] = relationship(back_populates="lines")
