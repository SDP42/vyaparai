"""Customer reviews and what we read from them (language, sentiment, themes)."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class Review(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)

    fingerprint: Mapped[str] = mapped_column(String(64))  # sha256 of source+date+rating+text
    source: Mapped[str] = mapped_column(String(60), default="upload")
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    product_hint: Mapped[str | None] = mapped_column(String(255))  # the SKU or name in the file
    review_date: Mapped[date | None] = mapped_column(Date, index=True)
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5 when the source has stars
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(12), default="en")  # en | hi | hinglish
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)  # -1 (negative) .. +1 (positive)
    label: Mapped[str] = mapped_column(String(10), default="neutral")  # negative|neutral|positive
    themes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)  # theme, polarity, snippet
    analysed_with: Mapped[str] = mapped_column(String(40), default="")  # model/lexicon version
