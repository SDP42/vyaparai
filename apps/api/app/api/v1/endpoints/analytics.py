"""Read-only analytics over imported sales. Every endpoint is workspace-scoped (viewer and up).

GET /workspaces/{id}/metrics                    the metric registry (definitions + versions)
GET /workspaces/{id}/analytics/filters          filter options and the default period
GET /workspaces/{id}/analytics/overview         KPIs, trend, mixes, top products, insights
GET /workspaces/{id}/analytics/drivers          volume / mix / price / discount attribution
GET /workspaces/{id}/analytics/transactions     drill-through to the order lines
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.core.errors import PermissionDeniedError
from app.schemas.analytics import (
    DriversResponse,
    FilterOptions,
    MetricRegistry,
    Overview,
    TransactionsResponse,
)
from app.services.analytics import service
from app.services.analytics.types import CompareMode, Dimension, Granularity

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["analytics"], route_class=MaskedRoute)

DateFrom = Annotated[date | None, Query(alias="from", description="First business day, inclusive")]
DateTo = Annotated[date | None, Query(alias="to", description="Last business day, inclusive")]
Compare = Annotated[CompareMode, Query(description="What to compare the period with")]
Multi = Annotated[list[str] | None, Query()]


@router.get("/metrics", response_model=MetricRegistry)
def metrics(_: ViewerCtx) -> dict[str, object]:
    return service.registry()


@router.get("/analytics/filters", response_model=FilterOptions)
def filters(ctx: ViewerCtx, db: DbSession) -> dict[str, object]:
    return service.filter_options(db, ctx.workspace)


@router.get("/analytics/overview", response_model=Overview)
def overview(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    compare: Compare = "previous_period",
    granularity: Annotated[Granularity | None, Query()] = None,
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
    sku: Multi = None,
) -> dict[str, object]:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region, skus=sku,
    )  # fmt: skip
    return service.overview(db, ctx.workspace, f, compare, granularity)


@router.get("/analytics/staff")
def staff(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
) -> dict[str, object]:
    """Sales by cashier or salesperson. Counter staff see only the name linked to their account."""
    p = ctx.persona
    only: str | None = None
    if p is not None and p.key == "cashier":
        if not ctx.staff_name:
            return {
                "meta": None,
                "has_staff": False,
                "rows": [],
                "own_only": True,
                "needs_link": True,
                "note": "Ask the owner to link your name on the bills to your account.",
            }
        only = ctx.staff_name
    elif p is not None and not p.can("staff"):
        raise PermissionDeniedError(f"Not part of the {p.label['en'].lower()} view.")
    f = service.resolve_filters(db, ctx.workspace_id, date_from, date_to)
    out = service.staff(db, ctx.workspace, f, only)
    return {**out, "own_only": only is not None, "needs_link": False}


@router.get("/analytics/drivers", response_model=DriversResponse)
def drivers(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    compare: Compare = "previous_period",
    by: Annotated[
        Dimension, Query(description="Dimension for the contribution table")
    ] = "category",
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
    sku: Multi = None,
) -> dict[str, object]:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region, skus=sku,
    )  # fmt: skip
    return service.drivers(db, ctx.workspace, f, compare, by)


@router.get("/analytics/transactions", response_model=TransactionsResponse)
def transactions(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=80)] = None,
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
    sku: Multi = None,
) -> dict[str, object]:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region, skus=sku,
    )  # fmt: skip
    return service.transactions(db, ctx.workspace, f, limit=limit, offset=offset, search=search)
