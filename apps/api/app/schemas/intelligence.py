"""Response contracts for customer and product intelligence."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.schemas.analytics import Meta


class CustomerParams(BaseModel):
    as_of: date
    lookback_days: int
    new_days: int
    active_days: int
    lapse_days: int


class SegmentRow(BaseModel):
    segment: str
    help: str
    customers: int
    share: Decimal | None
    net: Decimal
    net_share: Decimal | None
    avg_orders: Decimal | None
    avg_recency_days: Decimal | None


class CustomersSummary(BaseModel):
    params: CustomerParams
    currency: str
    customers: int
    net: Decimal
    repeat_customers: int
    repeat_rate: Decimal | None
    revenue_per_customer: Decimal | None
    avg_orders_per_customer: Decimal | None
    top_decile_share: Decimal | None
    lapsed_regulars: int
    walk_in_share: Decimal | None
    status_counts: dict[str, int]
    segments: list[SegmentRow]
    rfm_grid: list[list[int]]
    warnings: list[str]


class CustomerOut(BaseModel):
    key: str
    region: str | None
    city: str | None
    first_order: date
    last_order: date
    orders: int
    net: Decimal
    aov: Decimal
    recency_days: int
    r: int
    f: int
    m: int
    segment: str
    status: str


class CustomerList(BaseModel):
    params: CustomerParams
    total: int
    limit: int
    offset: int
    items: list[CustomerOut]


class CohortRowOut(BaseModel):
    cohort: str
    size: int
    counts: list[int]
    retention: list[Decimal | None]


class Cohorts(BaseModel):
    as_of: date
    months: int
    cohorts: list[CohortRowOut]
    warnings: list[str]


class ProductItem(BaseModel):
    key: str
    name: str
    category: str | None
    units: Decimal
    net: Decimal
    gross: Decimal
    discount: Decimal
    discount_rate: Decimal | None
    discounted_line_share: Decimal | None
    margin_amount: Decimal | None
    margin_pct: Decimal | None
    cost_coverage_pct: Decimal | None
    share: Decimal | None
    cumulative_share: Decimal
    abc: str
    quadrant: str
    previous_net: Decimal | None
    change_pct: Decimal | None
    flags: list[str]


class CategoryPerf(BaseModel):
    category: str
    products: int
    units: Decimal
    net: Decimal
    share: Decimal | None
    discount_rate: Decimal | None
    margin_amount: Decimal | None
    margin_pct: Decimal | None
    cost_coverage_pct: Decimal | None
    previous_net: Decimal | None
    change_pct: Decimal | None


class QuadrantRow(BaseModel):
    quadrant: str
    help: str
    products: int
    net: Decimal


class Portfolio(BaseModel):
    quadrants: list[QuadrantRow]
    abc: dict[str, int]
    discount_heavy: int
    declining: int
    rising: int


class ProductsResponse(BaseModel):
    meta: Meta
    overall_margin_pct: Decimal | None
    overall_discount_rate: Decimal | None
    items: list[ProductItem]
    categories: list[CategoryPerf]
    portfolio: Portfolio
    warnings: list[str]


class BasketPair(BaseModel):
    a: str
    a_name: str
    b: str
    b_name: str
    orders: int
    support: Decimal
    confidence_a_to_b: Decimal
    confidence_b_to_a: Decimal
    lift: Decimal


class BasketResponse(BaseModel):
    meta: Meta
    orders: int
    multi_item_orders: int
    multi_item_share: Decimal | None
    avg_items_per_order: Decimal | None
    pairs: list[BasketPair]
    pairs_found: int
    min_orders: int
    note: str
    extra: dict[str, Any] = {}
