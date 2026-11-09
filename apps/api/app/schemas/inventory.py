from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    sku: str
    name: str
    category: str | None
    snapshot_date: date
    snapshot_on_hand: Decimal
    sold_since: Decimal
    on_hand: Decimal
    daily_rate: Decimal
    cover_days: Decimal | None
    run_out_date: date | None
    lead_time_days: int
    pack_size: Decimal
    status: str  # urgent | reorder | ok | overstock | dead
    reason: str
    order_qty: Decimal
    unit_cost: Decimal | None
    order_cost: Decimal | None
    cash_tied: Decimal | None
    excess_cash: Decimal | None
    forecast_based: bool


class InventoryOverview(BaseModel):
    as_of: date | None
    items: list[InventoryItem]
    summary: dict[str, Any]
    has_forecast: bool
    service: Decimal | None = None
    review_days: int | None = None


class ImportResult(BaseModel):
    imported: int
    unmatched: int
    unmatched_skus: list[str]
    rejected_count: int
    rejected: list[dict[str, Any]]


class ItemUpdate(BaseModel):
    on_hand: Decimal | None = Field(default=None, ge=0)
    as_of: date | None = None
    lead_time_days: int | None = Field(default=None, ge=0, le=90)
    safety_days: int | None = Field(default=None, ge=0, le=60)
    pack_size: Decimal | None = Field(default=None, gt=0)
