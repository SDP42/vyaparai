"""Create a run, execute the workflow, store the trace and the result."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.agent import AgentRun
from app.models.workspace import Workspace
from app.services import audit
from app.services.agents import engine
from app.services.agents.workflows import WORKFLOWS


def run_workflow(
    db: Session, workspace: Workspace, user_id: uuid.UUID, workflow: str, params: dict[str, Any]
) -> AgentRun:
    spec = WORKFLOWS.get(workflow)
    if spec is None:
        raise AppError("Unknown workflow")
    clean = {k: v for k, v in params.items() if k in spec["params"] and v}
    run = engine.start(db, workspace.id, user_id, workflow, clean)
    rec = engine.Recorder(db, run)
    try:
        result = spec["run"](db, workspace, rec, clean)
        engine.finish(db, run, result)
    except Exception as exc:  # the run records the failure; the API still answers
        db.rollback()
        engine.finish(
            db, db.get(AgentRun, run.id) or run, None, f"{type(exc).__name__}: {exc}"[:500]
        )
    audit.record(
        db,
        action="agent.run",
        actor_user_id=user_id,
        workspace_id=workspace.id,
        entity_type="agent_run",
        entity_id=run.id,
        details={"workflow": workflow, "status": run.status},
    )
    db.commit()
    return run


def get_run(db: Session, ws: uuid.UUID, run_id: uuid.UUID) -> AgentRun:
    r = db.get(AgentRun, run_id)
    if r is None or r.workspace_id != ws:
        raise NotFoundError("Run not found")
    return r


def list_runs(db: Session, ws: uuid.UUID, limit: int = 20) -> list[AgentRun]:
    return list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.workspace_id == ws)
            .order_by(AgentRun.started_at.desc())
            .limit(limit)
        )
    )
