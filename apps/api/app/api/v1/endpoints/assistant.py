"""Ask the assistant a question in English, Hindi or Hinglish. Answers come from your own numbers."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DbSession, ViewerCtx
from app.services.assistant import service

router = APIRouter(prefix="/workspaces/{workspace_id}/assistant", tags=["assistant"])


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=300)


@router.post("/ask")
def ask(data: Ask, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.ask(db, ctx.workspace, data.question.strip())
