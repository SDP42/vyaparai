"""Response contracts for stored forecasts."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class RunInfo(BaseModel):
    id: uuid.UUID
    created_at: datetime
    as_of: date
    horizon: int
    history_days: int
    n_series: int
    seconds: float


class ForecastKpis(BaseModel):
    units_next: float
    units_next_low: float
    units_next_high: float
    units_last: float
    units_change_pct: float | None
    net_next: float
    net_last_est: float
    net_change_pct: float | None


class Mover(BaseModel):
    sku: str
    name: str
    units_last: float
    units_next: float
    change_pct: float


class ForecastOverview(BaseModel):
    run: RunInfo
    currency: str
    stale: bool  # newer sales exist than the forecast has seen
    latest_data_date: date | None
    kpis: ForecastKpis
    totals: dict[str, Any]  # history, forecast (p10/p50/p90/net) and backtest
    accuracy: dict[str, Any]
    model_card: dict[str, Any]
    risers: list[Mover]
    fallers: list[Mover]
    confidence_counts: dict[str, int]
    warnings: list[str]
    signals: dict[str, Any] = {}  # outside signals tried, e.g. weather and whether it helped


class NoForecast(BaseModel):
    has_forecast: bool = False
    can_forecast: bool
    reason: str | None = None
    latest_data_date: date | None = None
    history_days: int = 0


class ProductForecastRow(BaseModel):
    sku: str
    name: str
    category: str | None
    model: str
    pattern: str
    confidence: str
    backtest_wape: float | None
    backtest_bias: float | None
    units_last: float
    units_next: float
    units_next_low: float
    units_next_high: float
    change_pct: float | None
    spark: list[float]  # recent actuals then the p50 forecast, for a sparkline


class ProductForecastPage(BaseModel):
    run_id: uuid.UUID
    horizon: int
    total: int
    limit: int
    offset: int
    items: list[ProductForecastRow]


class ProductForecastDetail(ProductForecastRow):
    data: dict[str, Any]
    net_per_unit: float | None
