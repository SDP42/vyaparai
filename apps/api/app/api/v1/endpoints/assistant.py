"""Ask the assistant a question in English, Hindi or Hinglish. Answers come from your own numbers."""

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import DbSession, ViewerCtx
from app.services.assistant import service

router = APIRouter(prefix="/workspaces/{workspace_id}/assistant", tags=["assistant"])


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    context: dict[str, Any] | None = None  # the previous answer's `context`, for follow-ups


@router.post("/ask")
def ask(data: Ask, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.ask(db, ctx.workspace, data.question.strip(), ctx.role, context=data.context)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
def stream(data: Ask, ctx: ViewerCtx, db: DbSession) -> StreamingResponse:
    """The same answer as /ask, sent as server-sent events: each step the assistant took, then the reply.

    The answer is computed before streaming starts (the database session must not outlive the
    request), so the steps shown are the real recorded ones, not an animation.
    """
    out = service.ask(db, ctx.workspace, data.question.strip(), ctx.role, context=data.context)

    def events() -> Iterator[str]:
        for st in out["steps"]:
            yield _sse("step", st)
        yield _sse("answer", {"text": out["answer"], "note": out["note"]})
        yield _sse("evidence", out["evidence"])
        yield _sse("done", out)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
