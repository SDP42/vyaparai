from datetime import date
from typing import Any

from pydantic import BaseModel


class EventOut(BaseModel):
    id: str
    name: str
    start: date
    end: date
    category: str
    tier: int
    scope: str
    regions: list[str]
    lead: int
    tail: int
    demand: list[str]
    notes: str
    basis: str
    confidence: str
    sources: list[str]
    relevance: str = "core"  # core | zone (observed in your zone, not named for your state)


class MatchedProduct(BaseModel):
    sku: str
    name: str
    daily_sales: float
    cover_days: float | None
    tracked: bool
    at_risk: bool


class UpcomingEvent(BaseModel):
    event: EventOut
    days_until: int
    status: str  # ahead | ramping | on | fading
    matching_products: int
    products: list[MatchedProduct]
    last_time: dict[str, Any] | None


class EffectRow(BaseModel):
    id: str
    name: str
    start: date
    end: date
    tier: int
    all_products: dict[str, float] | None
    matching_products: dict[str, float] | None
    matching_count: int


class EventsCoverage(BaseModel):
    first: date | None
    last: date | None
    events: int
    by_confidence: dict[str, int]
