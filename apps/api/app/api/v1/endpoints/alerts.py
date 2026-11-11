"""Alerts: sales drops, margin leaks, discount creep, products that stopped selling.

GET  /workspaces/{id}/alerts                 recompute and list (status=open|dismissed|resolved|all)
GET  /workspaces/{id}/alerts/summary         open counts by severity, without recomputing
POST /workspaces/{id}/alerts/{alert}/dismiss hide one while it lasts (analyst)
POST /workspaces/{id}/alerts/{alert}/reopen  bring it back (analyst)
"""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.core.errors import NotFoundError
from app.models.alert import Alert
from app.schemas.alerts import AlertList, AlertRead
from app.services import alerts as service
from app.services import audit

router = APIRouter(
    prefix="/workspaces/{workspace_id}/alerts", tags=["alerts"], route_class=MaskedRoute
)


@router.get("", response_model=AlertList)
def list_alerts(
    ctx: ViewerCtx,
    db: DbSession,
    status: Annotated[str, Query(pattern="^(open|dismissed|resolved|all)$")] = "open",
    as_of: date | None = None,
) -> dict[str, Any]:
    res = service.refresh(db, ctx.workspace, as_of=as_of)
    return {
        "as_of": res["as_of"],
        "counts": service.counts(db, ctx.workspace_id),
        "items": service.listing(db, ctx.workspace_id, status),
    }


@router.get("/summary")
def summary(ctx: ViewerCtx, db: DbSession) -> dict[str, int]:
    return service.counts(db, ctx.workspace_id)


def _get(db: DbSession, ws: uuid.UUID, alert_id: uuid.UUID) -> Alert:
    a = db.get(Alert, alert_id)
    if a is None or a.workspace_id != ws:
        raise NotFoundError("Alert not found")
    return a


@router.post("/{alert_id}/dismiss", response_model=AlertRead)
def dismiss(alert_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> Alert:
    a = _get(db, ctx.workspace_id, alert_id)
    if a.status == "open":
        a.status, a.dismissed_at, a.dismissed_by_id = "dismissed", datetime.now(UTC), ctx.user.id
        audit.record(
            db,
            action="alert.dismissed",
            actor_user_id=ctx.user.id,
            workspace_id=ctx.workspace_id,
            entity_type="alert",
            entity_id=a.id,
            details={"key": a.key},
        )
        db.commit()
    return a


@router.post("/{alert_id}/reopen", response_model=AlertRead)
def reopen(alert_id: uuid.UUID, ctx: AnalystCtx, db: DbSession) -> Alert:
    a = _get(db, ctx.workspace_id, alert_id)
    if a.status == "dismissed":
        a.status, a.dismissed_at, a.dismissed_by_id = "open", None, None
        audit.record(
            db,
            action="alert.reopened",
            actor_user_id=ctx.user.id,
            workspace_id=ctx.workspace_id,
            entity_type="alert",
            entity_id=a.id,
            details={"key": a.key},
        )
        db.commit()
    return a
