"""Customer contacts and consent, and campaigns with a frozen recipient list.

Consent is recorded per customer, with where it came from; an opt-out is permanent until the customer
agrees again after it. Campaigns freeze who was in the treatment and holdout groups so the result can be
measured fairly later.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class CustomerContact(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "customer_contacts"
    __table_args__ = (UniqueConstraint("workspace_id", "customer_key"),)

    customer_key: Mapped[str] = mapped_column(String(120), index=True)  # Customer.external_key
    phone: Mapped[str | None] = mapped_column(
        String(15)
    )  # digits with country code; opens WhatsApp, never sent by us
    consent: Mapped[str] = mapped_column(
        String(10), default="unknown"
    )  # granted | denied | unknown
    consent_source: Mapped[str | None] = mapped_column(String(80))  # e.g. "asked at the counter"
    consent_date: Mapped[date | None] = mapped_column(Date)
    opted_out_at: Mapped[date | None] = mapped_column(Date)


class Campaign(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(120))
    segment: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(12), default="ready")  # ready | sending | closed
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    window_days: Mapped[int] = mapped_column(Integer, default=14)
    holdout_pct: Mapped[int] = mapped_column(Integer, default=10)
    started_on: Mapped[date | None] = mapped_column(Date)  # the day the first message went out
    counts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class CampaignRecipient(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "campaign_recipients"
    __table_args__ = (UniqueConstraint("campaign_id", "customer_key"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    customer_key: Mapped[str] = mapped_column(String(120), index=True)
    group: Mapped[str] = mapped_column(String(10))  # treatment | holdout
    message: Mapped[str] = mapped_column(Text)
    product: Mapped[str | None] = mapped_column(String(255))
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending | sent | skipped
    skip_reason: Mapped[str | None] = mapped_column(String(40))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
