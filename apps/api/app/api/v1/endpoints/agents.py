"""Agent workflows: run a bounded read-only investigation and read its step-by-step trace."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.models.agent import AgentRun
from app.services.agents import runner
from app.services.agents.workflows import WORKFLOWS

router = APIRouter(
    prefix="/workspaces/{workspace_id}/agents", tags=["agents"], route_class=MaskedRoute
)


class RunIn(BaseModel):
    workflow: str = Field(max_length=40)
    date_from: date | None = None
    date_to: date | None = None


def _run(r: AgentRun, detail: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(r.id), "workflow": r.workflow, "status": r.status, "params": r.params,
        "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        "error": r.error, "summary": (r.result or {}).get("summary"),
    }  # fmt: skip
    if detail:
        out["result"] = r.result
        out["steps"] = [
            {"position": s.position, "node": s.node, "status": s.status, "attempts": s.attempts, "ms": s.ms,
             "summary": s.summary, "error": s.error, "input": s.input, "output": s.output}
            for s in r.steps
        ]  # fmt: skip
    return out


@router.get("/workflows")
def workflows(ctx: ViewerCtx) -> list[dict[str, Any]]:
    return [
        {"key": k, "title": v["title"], "about": v["about"], "params": v["params"]}
        for k, v in WORKFLOWS.items()
    ]


@router.post("/runs")
def run(data: RunIn, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    params = {
        "from": data.date_from.isoformat() if data.date_from else None,
        "to": data.date_to.isoformat() if data.date_to else None,
    }
    r = runner.run_workflow(db, ctx.workspace, ctx.user.id, data.workflow, params)
    return _run(r, True)


@router.get("/runs")
def runs(
    ctx: ViewerCtx, db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[dict[str, Any]]:
    return [_run(r, False) for r in runner.list_runs(db, ctx.workspace_id, limit)]


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return _run(runner.get_run(db, ctx.workspace_id, run_id), True)
