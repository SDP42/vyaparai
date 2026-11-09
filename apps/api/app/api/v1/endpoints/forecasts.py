"""Demand forecasts: run in the background, stored, read cheaply.

POST /workspaces/{id}/forecasts/run              start a forecast job (analyst)
GET  /workspaces/{id}/forecasts/latest           totals, accuracy, model card, movers (viewer)
GET  /workspaces/{id}/forecasts/products         per-product forecasts, filter/sort/page
GET  /workspaces/{id}/forecasts/products/{sku}   one product with history, range and backtest
GET  /workspaces/{id}/forecasts/export.csv       every product and day as CSV
GET  /workspaces/{id}/forecasts/runs             every version with accuracy and status (viewer)
POST /workspaces/{id}/forecasts/runs/{run}/activate  make a version the active one (admin)
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import AdminCtx, AnalystCtx, DbSession, ViewerCtx
from app.core.errors import NotFoundError
from app.models.dataset import Job
from app.schemas.dataset import JobRead
from app.schemas.forecast import (
    ForecastOverview,
    NoForecast,
    ProductForecastDetail,
    ProductForecastPage,
    RunVersion,
)
from app.services.forecasting import service

router = APIRouter(prefix="/workspaces/{workspace_id}/forecasts", tags=["forecasts"])


@router.post("/run", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def run_forecast(
    ctx: AnalystCtx,
    db: DbSession,
    background: BackgroundTasks,
    tune: Annotated[
        bool, Query(description="Also search for better model settings (slower)")
    ] = False,
    peak_uplift_pct: Annotated[
        int, Query(ge=0, le=50, description="Extra demand to assume near the festive season")
    ] = 0,
) -> Job:
    job = service.start_forecast(
        db, ctx.workspace, ctx.user, tune=tune, peak_uplift_pct=peak_uplift_pct
    )
    if job.status.value == "queued":
        background.add_task(service.run_forecast_job, db.get_bind(), job.id)  # type: ignore[arg-type]
    return job


@router.get("/runs", response_model=list[RunVersion])
def runs(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return service.runs_history(db, ctx.workspace_id)


@router.post("/runs/{run_id}/activate", response_model=RunVersion)
def activate(run_id: uuid.UUID, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    run = service.activate(db, ctx.workspace_id, run_id, ctx.user)
    return next(r for r in service.runs_history(db, ctx.workspace_id) if r["id"] == run.id)


@router.get("/latest", response_model=ForecastOverview | NoForecast)
def latest(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    run = service.latest_run(db, ctx.workspace_id)
    if run is None:
        return {"has_forecast": False, **service.status_for(db, ctx.workspace_id)}
    return service.overview(db, ctx.workspace, run)


@router.get("/products", response_model=ProductForecastPage)
def products(
    ctx: ViewerCtx,
    db: DbSession,
    search: Annotated[str | None, Query(max_length=60)] = None,
    confidence: Annotated[str | None, Query(pattern="^(high|medium|low)$")] = None,
    model: Annotated[str | None, Query(pattern="^(lightgbm|theta|seasonal_average)$")] = None,
    pattern: Annotated[str | None, Query(max_length=20)] = None,
    sort: Annotated[str, Query(pattern="^(units_next|change|wape|name)$")] = "units_next",
    descending: bool = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    run = service.latest_run(db, ctx.workspace_id)
    if run is None:
        raise NotFoundError("No forecast yet. Run one first.")
    return service.products_page(
        db, run, search=search, confidence=confidence, model=model, pattern=pattern,
        sort=sort, descending=descending, limit=limit, offset=offset,
    )  # fmt: skip


@router.get("/products/{sku}", response_model=ProductForecastDetail)
def product(sku: str, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    run = service.latest_run(db, ctx.workspace_id)
    if run is None:
        raise NotFoundError("No forecast yet. Run one first.")
    return service.product_detail(db, run, sku)


@router.get("/export.csv", response_class=StreamingResponse)
def export(ctx: ViewerCtx, db: DbSession) -> StreamingResponse:
    run = service.latest_run(db, ctx.workspace_id)
    if run is None:
        raise NotFoundError("No forecast yet. Run one first.")
    return StreamingResponse(
        service.export_csv(db, run),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="forecast.csv"'},
    )
