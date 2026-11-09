"""Cost history: which costs moved, and where the price did not follow (margin leaks).

GET /workspaces/{id}/costs/overview        products ranked by margin leak, plus a summary
GET /workspaces/{id}/costs/{sku}/history   weekly cost and price per unit for one product
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ViewerCtx
from app.schemas.costs import CostHistory, CostOverview
from app.services import costs

router = APIRouter(prefix="/workspaces/{workspace_id}/costs", tags=["costs"])


@router.get("/overview", response_model=CostOverview)
def overview(
    ctx: ViewerCtx,
    db: DbSession,
    as_of: date | None = None,
    window_days: Annotated[int, Query(ge=14, le=90)] = 28,
) -> dict[str, Any]:
    return costs.overview(db, ctx.workspace_id, as_of, window_days)


@router.get("/{sku}/history", response_model=CostHistory)
def history(
    sku: str,
    ctx: ViewerCtx,
    db: DbSession,
    as_of: date | None = None,
    weeks: Annotated[int, Query(ge=4, le=52)] = 12,
) -> dict[str, Any]:
    return costs.history(db, ctx.workspace_id, sku, weeks, as_of)
