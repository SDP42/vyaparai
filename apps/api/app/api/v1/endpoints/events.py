"""Festivals, holidays and cricket: what is coming, what it touches in your shop, what it did before.

GET /workspaces/{id}/events/upcoming    events in the next N days with your matching products and stock cover
GET /workspaces/{id}/events/calendar    every event in a date range for your region
GET /workspaces/{id}/events/effects     what past events did to your sales (needs a quiet month before each)
GET /workspaces/{id}/events/coverage    how far the dated table reaches and how sure it is
"""

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ViewerCtx
from app.schemas.events import EffectRow, EventOut, EventsCoverage, UpcomingEvent
from app.services import events, events_insight

router = APIRouter(prefix="/workspaces/{workspace_id}/events", tags=["events"])


def _out(e: events.Event) -> dict[str, Any]:
    return {
        "id": e.id, "name": e.name, "start": e.start, "end": e.end, "category": e.category,
        "tier": e.tier, "scope": e.scope, "regions": sorted(e.regions), "lead": e.lead,
        "tail": e.tail, "demand": list(e.demand), "notes": e.notes, "basis": e.basis,
        "confidence": e.confidence, "sources": list(e.sources),
    }  # fmt: skip


@router.get("/upcoming", response_model=list[UpcomingEvent])
def upcoming(
    ctx: ViewerCtx,
    db: DbSession,
    days: Annotated[int, Query(ge=7, le=365)] = 90,
    include_cricket: bool = True,
) -> list[dict[str, Any]]:
    rows = events_insight.upcoming(db, ctx.workspace, days=days, include_cricket=include_cricket)
    return [{**r, "event": _out(r["event"])} for r in rows]


@router.get("/calendar", response_model=list[EventOut])
def calendar(
    ctx: ViewerCtx,
    start: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    tier_max: Annotated[int, Query(ge=1, le=3)] = 2,
    include_cricket: bool = True,
) -> list[dict[str, Any]]:
    a = start or date.today()
    b = to or a + timedelta(days=120)
    return [
        _out(e)
        for e in events_insight.calendar(
            ctx.workspace, a, b, include_cricket=include_cricket, tier_max=tier_max
        )
    ]


@router.get("/effects", response_model=list[EffectRow])
def effects(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return events_insight.observed_effects(db, ctx.workspace)


@router.get("/coverage", response_model=EventsCoverage)
def coverage(ctx: ViewerCtx) -> dict[str, Any]:
    return events.coverage()
