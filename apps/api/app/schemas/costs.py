from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class CostItem(BaseModel):
    sku: str
    name: str
    category: str | None
    status: str  # margin_leak | passed_on | cost_down | stable | no_cost | new | too_few
    cost_prev: Decimal | None = None
    cost_now: Decimal | None = None
    cost_change_pct: Decimal | None = None
    price_prev: Decimal | None = None
    price_now: Decimal | None = None
    price_change_pct: Decimal | None = None
    margin_prev_pct: Decimal | None = None
    margin_now_pct: Decimal | None = None
    units: Decimal | None = None
    leak_amount: Decimal | None = None
    suggested_price: Decimal | None = None
    suggested_increase_pct: Decimal | None = None


class CostOverview(BaseModel):
    as_of: date | None
    window_days: int
    current: dict[str, date] | None = None
    previous: dict[str, date] | None = None
    items: list[CostItem]
    summary: dict[str, Any]


class CostWeek(BaseModel):
    week_start: date
    units: Decimal
    cost: Decimal | None
    price: Decimal | None


class CostHistory(BaseModel):
    sku: str
    weeks: list[CostWeek]
