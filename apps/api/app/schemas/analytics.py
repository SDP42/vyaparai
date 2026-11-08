"""Response contracts for the analytics API. Money is a Decimal (serialised as a string)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel


class MetricDefOut(BaseModel):
    key: str
    label: str
    unit: Literal["inr", "count", "percent"]
    version: int
    definition: str
    includes: str
    excludes: str
    good_direction: Literal["up_good", "down_good", "neutral"]


class MetricRegistry(BaseModel):
    registry_version: int
    eligibility: str
    assumptions: list[str]
    metrics: list[MetricDefOut]


class Kpi(BaseModel):
    key: str
    label: str
    unit: Literal["inr", "count", "percent"]
    version: int
    value: Decimal | None
    previous: Decimal | None
    change: Decimal | None  # absolute (percentage points for percent metrics)
    change_pct: Decimal | None  # relative %, null when previous is 0 or the metric is a percentage
    good_direction: Literal["up_good", "down_good", "neutral"]
    compare_in_points: bool


class PeriodInfo(BaseModel):
    date_from: date
    date_to: date
    days: int


class CompareInfo(PeriodInfo):
    mode: Literal["previous_period", "previous_year"]
    label: str


class Freshness(BaseModel):
    last_order_date: date | None
    first_order_date: date | None
    last_import_at: datetime | None


class Coverage(BaseModel):
    days_in_period: int
    days_with_data: int
    compare_days_with_data: int | None
    cost_coverage_pct: Decimal | None
    excluded_orders_by_status: dict[str, int]
    anonymous_order_share: Decimal | None


class Meta(BaseModel):
    currency: str
    timezone: str
    has_data: bool
    period: PeriodInfo
    compare: CompareInfo | None
    granularity: Literal["day", "week", "month"]
    filters: dict[str, list[str]]
    metric_versions: dict[str, int]
    freshness: Freshness
    coverage: Coverage


class TrendPoint(BaseModel):
    start: date
    label: str
    net: Decimal
    orders: int
    units: Decimal
    aov: Decimal | None
    previous_net: Decimal | None
    previous_label: str | None


class MixRow(BaseModel):
    key: str
    label: str
    net: Decimal
    previous_net: Decimal | None
    delta: Decimal | None
    share: Decimal | None
    share_of_change: Decimal | None
    units: Decimal
    orders: int


class WeekdayRow(BaseModel):
    weekday: int  # 0 = Monday
    label: str
    avg_net: Decimal
    days: int


class ProductRow(BaseModel):
    sku: str
    name: str
    category: str | None
    net: Decimal
    previous_net: Decimal | None
    delta: Decimal | None
    units: Decimal
    previous_units: Decimal | None


class Insight(BaseModel):
    id: str
    tone: Literal["good", "bad", "neutral", "warning"]
    title: str
    body: str
    evidence: list[str]


class Overview(BaseModel):
    meta: Meta
    headline: list[Kpi]
    secondary: list[Kpi]
    trend: list[TrendPoint]
    category_mix: list[MixRow]
    channel_mix: list[MixRow]
    region_mix: list[MixRow]
    weekday: list[WeekdayRow]
    top_products: list[ProductRow]
    bottom_products: list[ProductRow]
    insights: list[Insight]
    warnings: list[str]


class DriverEffectOut(BaseModel):
    key: str
    label: str
    amount: Decimal
    explanation: str


class ProductMoveOut(BaseModel):
    sku: str
    name: str
    category: str | None
    units_prev: Decimal
    units_cur: Decimal
    net_prev: Decimal
    net_cur: Decimal
    delta: Decimal


class DriversResponse(BaseModel):
    meta: Meta
    net_sales_current: Decimal
    net_sales_previous: Decimal | None
    net_change: Decimal | None
    effects: list[DriverEffectOut]
    method: str
    caveat: str
    contributions: list[MixRow]
    contribution_dimension: str
    biggest_decliners: list[ProductMoveOut]
    biggest_gainers: list[ProductMoveOut]
    continuing_products: int
    new_products: int
    discontinued_products: int
    insights: list[Insight]
    warnings: list[str]


class TransactionRow(BaseModel):
    order_id: str
    date: date
    sku: str
    product: str
    category: str | None
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    net: Decimal
    customer: str | None
    channel: str | None


class TransactionsResponse(BaseModel):
    meta: Meta
    total_lines: int
    total_net: Decimal
    limit: int
    offset: int
    items: list[TransactionRow]


class FilterOptions(BaseModel):
    categories: list[str]
    channels: list[str]
    regions: list[str]
    first_order_date: date | None
    last_order_date: date | None
    default_from: date
    default_to: date
    has_data: bool
    extra: dict[str, Any] = {}
