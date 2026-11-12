"""Daily automations: the shop owner picks which automation agents run on their own, and at what hour.

`run_due` is called by the agent runner (cron every 15 minutes, like the digest). Each enabled agent runs at most
once per local day. A run is the same read-only workflow as a manual run; its result appears under Investigate.
"""

import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.agent import AgentSchedule
from app.models.workspace import Workspace
from app.services.agents import automations, runner
from app.services.agents.workflows import WORKFLOWS

AUTOMATIONS = list(automations.NEW)


def get(db: Session, ws: uuid.UUID) -> list[dict[str, Any]]:
    saved = {
        s.workflow: s
        for s in db.scalars(select(AgentSchedule).where(AgentSchedule.workspace_id == ws))
    }
    out = []
    for key in AUTOMATIONS:
        s = saved.get(key)
        out.append({
            "workflow": key, "title": WORKFLOWS[key]["title"], "about": WORKFLOWS[key]["about"],
            "enabled": bool(s and s.enabled), "hour": s.hour if s else 8,
            "last_run_for": s.last_run_for.isoformat() if s and s.last_run_for else None,
        })  # fmt: skip
    return out


def set_one(
    db: Session, ws: uuid.UUID, workflow: str, enabled: bool, hour: int
) -> list[dict[str, Any]]:
    if workflow not in AUTOMATIONS:
        raise AppError("Unknown automation")
    if not 0 <= hour <= 23:
        raise AppError("Hour must be 0 to 23")
    s = db.scalars(
        select(AgentSchedule).where(
            AgentSchedule.workspace_id == ws, AgentSchedule.workflow == workflow
        )
    ).first()
    if s is None:
        s = AgentSchedule(workspace_id=ws, workflow=workflow)
        db.add(s)
    s.enabled, s.hour = enabled, hour
    db.commit()
    return get(db, ws)


def run_due(db: Session, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(UTC)
    done: list[dict[str, Any]] = []
    for s in db.scalars(select(AgentSchedule).where(AgentSchedule.enabled.is_(True))).all():
        ws = db.get(Workspace, s.workspace_id)
        if ws is None:
            continue
        local = now.astimezone(ZoneInfo(ws.timezone))
        if local.hour < s.hour or s.last_run_for == local.date():
            continue
        run = runner.run_workflow(db, ws, None, s.workflow, {"today": local.date().isoformat()})
        s.last_run_for = local.date()
        db.commit()
        done.append({"workspace": str(ws.id), "workflow": s.workflow, "status": run.status})
    return done
