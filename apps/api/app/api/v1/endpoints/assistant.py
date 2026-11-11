"""Ask the assistant a question in English, Hindi or Hinglish. Answers come from your own numbers."""

import json
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import AppSettings, DbSession, ViewerCtx
from app.core.errors import AppError
from app.services import voice
from app.services.assistant import service

router = APIRouter(prefix="/workspaces/{workspace_id}/assistant", tags=["assistant"])


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    context: dict[str, Any] | None = None  # the previous answer's `context`, for follow-ups


@router.post("/ask")
def ask(data: Ask, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return service.ask(
        db,
        ctx.workspace,
        data.question.strip(),
        ctx.role,
        context=data.context,
        persona=ctx.persona,
    )


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/stream")
def stream(data: Ask, ctx: ViewerCtx, db: DbSession) -> StreamingResponse:
    """The same answer as /ask, sent as server-sent events: each step the assistant took, then the reply.

    The answer is computed before streaming starts (the database session must not outlive the
    request), so the steps shown are the real recorded ones, not an animation.
    """
    out = service.ask(
        db,
        ctx.workspace,
        data.question.strip(),
        ctx.role,
        context=data.context,
        persona=ctx.persona,
    )

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


@router.post("/voice")
def transcribe_voice(
    ctx: ViewerCtx,
    settings: AppSettings,
    audio: Annotated[UploadFile, File()],
    language: Annotated[str, Form(pattern="^(hi|en|mr|gu)$")] = "hi",
) -> dict[str, Any]:
    """Turn a short spoken question into text. The browser shows it for confirmation, then calls /ask.

    Send a 16-bit PCM WAV of at most a few seconds. The audio is processed in memory and discarded:
    it is not stored, and neither the audio nor the words are logged.
    """
    if not settings.voice_enabled:
        raise voice.VoiceUnavailable("Voice is switched off on this server.")
    data = audio.file.read(settings.voice_max_audio_kb * 1024 + 1)
    if len(data) > settings.voice_max_audio_kb * 1024:
        raise AppError("That recording is too long. Speak one short question.")
    clip = voice.decode_wav(data, settings.voice_max_seconds)
    t = voice.transcribe(clip, language, settings)
    return {
        "text": t.text, "language": t.language, "seconds": t.seconds, "ms": t.ms,
        "reason": t.reason, "confidence": t.confidence,
    }  # fmt: skip
