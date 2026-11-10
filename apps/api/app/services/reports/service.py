"""Create, list, read and delete saved reports."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.report import SavedReport
from app.models.workspace import Workspace
from app.services import audit
from app.services.reports import build as builder


def create(
    db: Session, workspace: Workspace, user_id: uuid.UUID, start: date | None, end: date | None
) -> SavedReport:
    try:
        content = builder.build(db, workspace, start, end)
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    p = content["period"]
    r = SavedReport(
        workspace_id=workspace.id, title=f"Business summary, {p['from']} to {p['to']}", period_start=date.fromisoformat(p["from"]),
        period_end=date.fromisoformat(p["to"]), content=content, created_by_id=user_id,
    )  # fmt: skip
    db.add(r)
    audit.record(
        db,
        action="report.created",
        actor_user_id=user_id,
        workspace_id=workspace.id,
        entity_type="report",
        entity_id=None,
        details={"from": p["from"], "to": p["to"]},
    )
    db.commit()
    return r


def get(db: Session, ws: uuid.UUID, rid: uuid.UUID) -> SavedReport:
    r = db.get(SavedReport, rid)
    if r is None or r.workspace_id != ws:
        raise NotFoundError("Report not found")
    return r


def listing(db: Session, ws: uuid.UUID, limit: int = 30) -> list[SavedReport]:
    return list(
        db.scalars(
            select(SavedReport)
            .where(SavedReport.workspace_id == ws)
            .order_by(SavedReport.created_at.desc())
            .limit(limit)
        )
    )


def remove(db: Session, r: SavedReport, user_id: uuid.UUID) -> None:
    audit.record(
        db,
        action="report.deleted",
        actor_user_id=user_id,
        workspace_id=r.workspace_id,
        entity_type="report",
        entity_id=r.id,
    )
    db.delete(r)
    db.commit()
