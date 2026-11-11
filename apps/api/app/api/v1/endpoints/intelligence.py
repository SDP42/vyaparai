"""Customer and product intelligence (read-only, viewer and up, workspace-scoped).

    GET /workspaces/{id}/analytics/customers/summary      RFM segments, status, repeat rate
GET /workspaces/{id}/analytics/customers/list         scored customers with filters, sorting, paging
GET /workspaces/{id}/analytics/customers/cohorts      first-purchase-month retention matrix
GET /workspaces/{id}/analytics/customers/export.csv   the filtered customer list as CSV
GET /workspaces/{id}/analytics/products               margin, discounts, ABC, portfolio quadrants
GET /workspaces/{id}/analytics/products/export.csv    the product table as CSV
GET /workspaces/{id}/analytics/basket                 products bought together
"""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import DbSession, ViewerCtx, require_capability
from app.api.masking import MaskedRoute
from app.schemas.intelligence import (
    BasketResponse,
    Cohorts,
    CustomerList,
    CustomersSummary,
    ProductsResponse,
)
from app.services.analytics import intelligence as svc
from app.services.analytics import service
from app.services.analytics.types import CompareMode

router = APIRouter(
    prefix="/workspaces/{workspace_id}/analytics", tags=["intelligence"], route_class=MaskedRoute
)

AsOf = Annotated[
    date | None, Query(description="Evaluate customers as of this day (default: latest order)")
]
Lookback = Annotated[
    int, Query(ge=7, le=1095, description="Days of history used for frequency and spend")
]
NewDays = Annotated[int, Query(ge=1, le=365)]
ActiveDays = Annotated[int, Query(ge=1, le=365)]
LapseDays = Annotated[int, Query(ge=2, le=730)]
DateFrom = Annotated[date | None, Query(alias="from")]
DateTo = Annotated[date | None, Query(alias="to")]
Multi = Annotated[list[str] | None, Query()]
# Kept as static Literals so OpenAPI lists the values; a test checks they match SEGMENTS/STATUSES.
SegmentName = Literal[
    "Champions",
    "Loyal",
    "New",
    "Promising",
    "Needs attention",
    "Can't lose",
    "At risk",
    "Hibernating",
]
StatusName = Literal["Active", "Cooling", "Lapsed"]


@router.get(
    "/customers/summary",
    dependencies=[Depends(require_capability("customers"))],
    response_model=CustomersSummary,
)
def customers_summary(
    ctx: ViewerCtx,
    db: DbSession,
    as_of: AsOf = None,
    lookback_days: Lookback = 365,
    new_days: NewDays = 30,
    active_days: ActiveDays = 30,
    lapse_days: LapseDays = 45,
) -> dict[str, Any]:
    return svc.customers_summary(
        db, ctx.workspace, as_of, lookback_days, new_days, active_days, lapse_days
    )


@router.get(
    "/customers/list",
    dependencies=[Depends(require_capability("customers"))],
    response_model=CustomerList,
)
def customers_list(
    ctx: ViewerCtx,
    db: DbSession,
    as_of: AsOf = None,
    lookback_days: Lookback = 365,
    new_days: NewDays = 30,
    active_days: ActiveDays = 30,
    lapse_days: LapseDays = 45,
    segment: Annotated[SegmentName | None, Query()] = None,
    status: Annotated[StatusName | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=60)] = None,
    sort: Annotated[Literal["net", "orders", "recency", "last_order", "name"], Query()] = "net",
    descending: bool = True,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return svc.customers_list(
        db, ctx.workspace, as_of, lookback_days, new_days, active_days, lapse_days,
        segment=segment, status=status, search=search, sort=sort, descending=descending,
        limit=limit, offset=offset,
    )  # fmt: skip


@router.get(
    "/customers/cohorts",
    dependencies=[Depends(require_capability("customers"))],
    response_model=Cohorts,
)
def customer_cohorts(
    ctx: ViewerCtx,
    db: DbSession,
    as_of: AsOf = None,
    months: Annotated[int, Query(ge=2, le=36)] = 12,
) -> dict[str, Any]:
    return svc.cohorts(db, ctx.workspace, as_of, months)


@router.get(
    "/customers/export.csv",
    dependencies=[Depends(require_capability("customers"))],
    response_class=StreamingResponse,
)
def customers_export(
    ctx: ViewerCtx,
    db: DbSession,
    as_of: AsOf = None,
    lookback_days: Lookback = 365,
    new_days: NewDays = 30,
    active_days: ActiveDays = 30,
    lapse_days: LapseDays = 45,
    segment: Annotated[SegmentName | None, Query()] = None,
    status: Annotated[StatusName | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=60)] = None,
) -> StreamingResponse:
    _, rows = svc.scored(db, ctx.workspace, as_of, lookback_days, new_days, active_days, lapse_days)
    rows = svc.filter_rows(rows, segment, status, search)
    rows.sort(key=lambda r: r.net, reverse=True)
    label = str(segment) if segment else "all"
    name = f"customers_{label.lower().replace(' ', '_').replace(chr(39), '')}.csv"
    return StreamingResponse(
        svc.customers_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/products", response_model=ProductsResponse)
def products(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    compare: Annotated[CompareMode, Query()] = "previous_period",
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
) -> dict[str, Any]:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region,
    )  # fmt: skip
    return svc.products_overview(db, ctx.workspace, f, compare)


@router.get("/products/export.csv", response_class=StreamingResponse)
def products_export(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    compare: Annotated[CompareMode, Query()] = "previous_period",
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
) -> StreamingResponse:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region,
    )  # fmt: skip
    data = svc.products_overview(db, ctx.workspace, f, compare)
    return StreamingResponse(
        svc.products_csv(data["items"]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="products.csv"'},
    )


@router.get("/basket", response_model=BasketResponse)
def basket(
    ctx: ViewerCtx,
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    min_orders: Annotated[
        int, Query(ge=2, le=1000, description="Minimum orders containing the pair")
    ] = 5,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Multi = None,
    channel: Multi = None,
    region: Multi = None,
) -> dict[str, Any]:
    f = service.resolve_filters(
        db, ctx.workspace_id, date_from, date_to,
        categories=category, channels=channel, regions=region,
    )  # fmt: skip
    return svc.basket_overview(db, ctx.workspace, f, min_orders, limit)
