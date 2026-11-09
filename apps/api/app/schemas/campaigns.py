"""Response contracts for campaign planning."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class PlaybookEntry(BaseModel):
    segment: str
    help: str
    kind: str
    goal: str
    idea: str
    customers: int
    default_max_discount: int
    assumed_redemption: Decimal


class OfferRow(BaseModel):
    sku: str
    name: str
    segment_units: Decimal
    price: Decimal
    margin_pct: Decimal | None
    safe_discount_pct: Decimal | None
    discount_pct: Decimal
    margin_after_pct: Decimal | None
    flag: str | None


class AudienceRow(BaseModel):
    key: str
    city: str | None
    last_order: date
    recency_days: int
    orders: int
    net: Decimal
    overdue_ratio: Decimal | None
    reason: str
    product: str
    discount_pct: Decimal
    holdout: bool
    consent_status: str
    message: str


class CampaignPlan(BaseModel):
    segment: str
    kind: str
    goal: str
    idea: str
    as_of: date
    currency: str
    audience: dict[str, int]
    params: dict[str, Any]
    ladder: list[dict[str, Any]]
    offers: list[OfferRow]
    projection: dict[str, Any]
    consent_note: str
    warnings: list[str]
    rows: list[AudienceRow]
    total_rows: int
    limit: int
    offset: int
