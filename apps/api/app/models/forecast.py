"""Stored forecast results: one run per training job, one row per product series.

Forecasts are computed in a background job and *stored*, so reading them is a cheap query and a
forecast can be explained later (the run keeps its model card and accuracy figures).
"""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, WorkspaceScopedMixin


class ForecastRun(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, CreatedAtMixin, Base):
    __tablename__ = "forecast_runs"

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)  # last business date the model saw
    horizon: Mapped[int] = mapped_column(Integer)
    history_days: Mapped[int] = mapped_column(Integer)
    n_series: Mapped[int] = mapped_column(Integer)
    seconds: Mapped[float] = mapped_column(Float)
    # model card, accuracy (WAPE, bias, FVA, coverage), totals series and warnings
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class ForecastSeries(UUIDPrimaryKeyMixin, WorkspaceScopedMixin, Base):
    __tablename__ = "forecast_series"
    __table_args__ = (Index("ix_forecast_series_run_sku", "run_id", "sku", unique=True),)

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("forecast_runs.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(40))
    pattern: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[str] = mapped_column(String(10))
    backtest_wape: Mapped[float | None] = mapped_column(Float)
    backtest_bias: Mapped[float | None] = mapped_column(Float)
    units_last: Mapped[float] = mapped_column(Float)  # actual units in the last `horizon` days
    units_next: Mapped[float] = mapped_column(Float)  # forecast p50 over the next `horizon` days
    units_next_low: Mapped[float] = mapped_column(Float)
    units_next_high: Mapped[float] = mapped_column(Float)
    net_per_unit: Mapped[float | None] = mapped_column(Float)
    # history (recent actuals), forecast days with p10/p50/p90, backtest actual vs predicted
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
