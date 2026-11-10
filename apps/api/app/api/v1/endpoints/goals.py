"""Goals: set a target, see pace and a projected finish, and read benchmarks from your own history."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.services import goals

router = APIRouter(prefix="/workspaces/{workspace_id}/goals", tags=["goals"])


class GoalIn(BaseModel):
    name: str = Field(default="", max_length=120)
    metric: str = Field(max_length=30)
    target: float = Field(gt=0)
    period: str = Field(default="month", pattern="^(month|week|custom)$")
    date_from: date | None = None
    date_to: date | None = None


def _today() -> date:
    return datetime.now(UTC).date()


@router.get("/metrics")
def metrics(ctx: ViewerCtx) -> list[dict[str, Any]]:
    return [{"key": k, **v} for k, v in goals.METRICS.items()]


@router.get("")
def listing(ctx: ViewerCtx, db: DbSession, closed: bool = False) -> list[dict[str, Any]]:
    return goals.listing(db, ctx.workspace, _today(), closed)


@router.post("", status_code=status.HTTP_201_CREATED)
def create(data: GoalIn, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    g = goals.create(
        db,
        ctx.workspace,
        ctx.user.id,
        name=data.name,
        metric=data.metric,
        target=data.target,
        period=data.period,
        start=data.date_from,
        end=data.date_to,
        today=_today(),
    )
    return goals.progress(db, ctx.workspace, g, _today())


@router.get("/benchmarks")
def benchmarks(
    ctx: ViewerCtx,
    db: DbSession,
    metric: Annotated[str, Query(max_length=30)] = "net_sales",
    period: Annotated[str, Query(pattern="^(month|week)$")] = "month",
) -> dict[str, Any]:
    return goals.history(db, ctx.workspace, metric, period, _today())


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def close(goal_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> Response:
    goals.close(db, goals.get(db, ctx.workspace_id, goal_id), ctx.user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
