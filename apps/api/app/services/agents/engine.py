"""Run a workflow graph with a hard budget, bounded retries and a stored trace.

Why a graph and no language model: every node calls an existing, tested service and returns
numbers. That keeps each step inspectable and makes the workflow immune to instructions hidden
in data (reviews, documents), because no text is ever interpreted as a command.
Guarantees:
- only allow-listed read-only tools are reachable (``TOOLS`` in tools.py);
- at most MAX_NODES node executions and MAX_SECONDS in total; a failing node is retried up to
  MAX_ATTEMPTS times, then recorded as failed and the workflow goes on with what it has;
- every node is stored as an AgentStep with its input, output, attempts and time.
"""

import json
import time
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.agent import AgentRun, AgentStep

MAX_NODES = 16
MAX_SECONDS = 20.0
MAX_ATTEMPTS = 2


def jsonable(x: Any) -> Any:
    """Make a value safe to store as JSON (Decimal and dates become numbers and ISO strings)."""
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, date | datetime):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple | set):
        return [jsonable(v) for v in x]
    return x


class Recorder:
    """Writes one AgentStep per node and enforces the budget."""

    def __init__(self, db: Session, run: AgentRun) -> None:
        self.db, self.run = db, run
        self.n = 0
        self.t0 = time.perf_counter()

    def over_budget(self) -> str | None:
        if self.n >= MAX_NODES:
            return f"step limit ({MAX_NODES}) reached"
        if time.perf_counter() - self.t0 > MAX_SECONDS:
            return f"time limit ({MAX_SECONDS:.0f}s) reached"
        return None

    def add(self, step: AgentStep) -> None:
        step.position = self.n
        self.n += 1
        self.db.add(step)
        self.db.commit()  # the viewer can show progress, and a crash keeps the partial trace


NodeFn = Callable[[Any], dict[str, Any]]


def traced(
    rec: Recorder, name: str, fn: NodeFn, describe: Callable[[dict[str, Any]], str] | None = None
) -> NodeFn:
    """Wrap a node: budget check, bounded retries, and a stored step either way."""

    def node(state: Any) -> dict[str, Any]:
        base = AgentStep(
            workspace_id=rec.run.workspace_id,
            run_id=rec.run.id,
            node=name,
            input=jsonable({"params": state.get("params", {})}),
        )
        stop = rec.over_budget()
        if stop:
            base.status, base.error, base.attempts = "skipped", stop, 0
            rec.add(base)
            return {"notes": [f"{name} skipped: {stop}"]}
        t0 = time.perf_counter()
        last: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                out = fn(state)
            except Exception as exc:  # a node may fail; the run records it and carries on
                last = exc
                continue
            base.status, base.attempts = "ok", attempt
            base.output = jsonable(out)
            base.summary = (describe(out) if describe else "")[:300]
            base.ms = round((time.perf_counter() - t0) * 1000)
            rec.add(base)
            return out
        base.status, base.attempts = "failed", MAX_ATTEMPTS
        base.error = f"{type(last).__name__}: {last}"[:500]
        base.ms = round((time.perf_counter() - t0) * 1000)
        rec.add(base)
        return {"notes": [f"{name} could not be checked ({type(last).__name__})"]}

    return node


def start(
    db: Session, ws: uuid.UUID, user_id: uuid.UUID | None, workflow: str, params: dict[str, Any]
) -> AgentRun:
    run = AgentRun(workspace_id=ws, workflow=workflow, status="running", params=jsonable(params),
                   started_at=datetime.now(UTC), created_by_id=user_id)  # fmt: skip
    db.add(run)
    db.commit()
    return run


def finish(
    db: Session, run: AgentRun, result: dict[str, Any] | None, error: str | None = None
) -> None:
    run.status = "failed" if error else "done"
    run.result = None if result is None else json.loads(json.dumps(jsonable(result)))
    run.error = error
    run.finished_at = datetime.now(UTC)
    db.commit()
