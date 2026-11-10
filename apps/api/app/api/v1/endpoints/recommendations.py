"""Recommendations: ranked suggestions with reasons, impact ranges and an approval trail."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.models.recommendation import Recommendation
from app.services.recommend import service

router = APIRouter(prefix="/workspaces/{workspace_id}/recommendations", tags=["recommendations"])


class Decision(BaseModel):
    note: str | None = Field(default=None, max_length=300)


def _r(r: Recommendation) -> dict[str, Any]:
    return {
        "id": str(r.id), "kind": r.kind, "title": r.title, "why": r.why, "evidence": r.evidence, "impact": r.impact,
        "effort": r.effort, "confidence": r.confidence, "score": round(r.score, 1), "link": r.link, "status": r.status,
        "note": r.note, "first_seen": r.first_seen.isoformat(), "last_seen": r.last_seen.isoformat(),
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
    }  # fmt: skip


@router.post("/refresh")
def refresh(ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    return service.refresh(db, ctx.workspace)


@router.get("")
def listing(
    ctx: ViewerCtx, db: DbSession,
    status: Annotated[str, Query(pattern="^(proposed|approved|done|dismissed|stale|all)$")] = "proposed",
) -> list[dict[str, Any]]:  # fmt: skip
    return [_r(r) for r in service.listing(db, ctx.workspace_id, status)]


@router.get("/summary")
def summary(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.summary(db, ctx.workspace_id)


def _decide(
    action: str, rec_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, data: Decision | None
) -> dict[str, Any]:
    return _r(
        service.decide(
            db, ctx.workspace_id, rec_id, action, ctx.user.id, data.note if data else None
        )
    )


@router.post("/{rec_id}/approve")
def approve(
    rec_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, data: Decision | None = None
) -> dict[str, Any]:
    return _decide("approve", rec_id, ctx, db, data)


@router.post("/{rec_id}/dismiss")
def dismiss(
    rec_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, data: Decision | None = None
) -> dict[str, Any]:
    return _decide("dismiss", rec_id, ctx, db, data)


@router.post("/{rec_id}/done")
def done(
    rec_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, data: Decision | None = None
) -> dict[str, Any]:
    return _decide("done", rec_id, ctx, db, data)


@router.post("/{rec_id}/reopen")
def reopen(
    rec_id: uuid.UUID, ctx: AnalystCtx, db: DbSession, data: Decision | None = None
) -> dict[str, Any]:
    return _decide("reopen", rec_id, ctx, db, data)
