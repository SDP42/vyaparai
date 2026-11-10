"""Campaign consent, launching, the outbox people send from, and measured results."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import AdminCtx, AnalystCtx, DbSession, ViewerCtx
from app.core.errors import AppError
from app.models.campaign import Campaign
from app.services import audit, campaign_runs
from app.services.campaigns import Language

router = APIRouter(prefix="/workspaces/{workspace_id}/campaigns", tags=["campaign-runs"])
MAX_BYTES = 5 * 1024 * 1024


class ContactIn(BaseModel):
    customer_key: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    consent: str | None = Field(default=None, pattern="^(granted|denied|unknown)$")
    source: str | None = Field(default=None, max_length=80)


class OptOutIn(BaseModel):
    customer_key: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class LaunchIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    segment: str = Field(max_length=30)
    holdout_pct: int = Field(default=10, ge=0, le=50)
    window_days: int = Field(default=14, ge=3, le=60)
    max_discount: int | None = Field(default=None, ge=0, le=50)
    margin_floor: int = Field(default=15, ge=0, le=90)
    language: Language = "hinglish"
    valid_days: int = Field(default=7, ge=1, le=30)


class MarkSent(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


def _c(c: Campaign) -> dict[str, Any]:
    return {"id": str(c.id), "name": c.name, "segment": c.segment, "status": c.status, "window_days": c.window_days, "holdout_pct": c.holdout_pct,
            "started_on": c.started_on.isoformat() if c.started_on else None, "counts": c.counts, "created_at": c.created_at.isoformat()}  # fmt: skip


@router.get("/contacts/summary")
def contacts_summary(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return campaign_runs.contacts_summary(db, ctx.workspace_id)


@router.get("/contacts")
def list_contacts(
    ctx: AnalystCtx, db: DbSession, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> list[dict[str, Any]]:
    return campaign_runs.list_contacts(db, ctx.workspace_id, limit)


@router.put("/contacts")
def put_contact(data: ContactIn, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    c = campaign_runs.upsert_contact(
        db,
        ctx.workspace_id,
        data.customer_key,
        phone=data.phone,
        consent=data.consent,
        source=data.source,
    )
    audit.record(
        db,
        action="contact.consent_set",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="contact",
        entity_id=None,
        details={"consent": c.consent, "source": c.consent_source},
    )
    db.commit()
    return {"customer_key": c.customer_key, "consent": c.consent}


@router.post("/contacts/import")
async def import_contacts(
    ctx: AnalystCtx, db: DbSession, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise AppError("The file is larger than 5 MB.")
    res = campaign_runs.import_contacts(db, ctx.workspace_id, content)
    audit.record(
        db,
        action="contact.imported",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="contact",
        entity_id=None,
        details=res,
    )
    db.commit()
    return res


@router.post("/contacts/opt-out")
def opt_out(data: OptOutIn, ctx: AnalystCtx, db: DbSession) -> dict[str, int]:
    if not data.customer_key and not data.phone:
        raise AppError("Give a customer key or a phone number")
    n = campaign_runs.opt_out(db, ctx.workspace_id, key=data.customer_key, phone=data.phone)
    audit.record(
        db,
        action="contact.opted_out",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="contact",
        entity_id=None,
        details={"count": n},
    )
    db.commit()
    return {"opted_out": n}


@router.post("/runs", status_code=status.HTTP_201_CREATED)
def launch(data: LaunchIn, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    c = campaign_runs.launch(db, ctx.workspace, ctx.user.id, name=data.name, segment=data.segment, holdout_pct=data.holdout_pct, window_days=data.window_days,
                             max_discount=data.max_discount, margin_floor=data.margin_floor, language=data.language, valid_days=data.valid_days)  # fmt: skip
    return _c(c)


@router.get("/runs")
def runs(ctx: ViewerCtx, db: DbSession) -> list[dict[str, Any]]:
    return [_c(c) for c in campaign_runs.listing(db, ctx.workspace_id)]


@router.get("/runs/{cid}")
def get_run(cid: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return _c(campaign_runs.get(db, ctx.workspace_id, cid))


@router.get("/runs/{cid}/outbox")
def outbox(
    cid: uuid.UUID, ctx: AdminCtx, db: DbSession, limit: Annotated[int, Query(ge=1, le=100)] = 25
) -> dict[str, Any]:
    return campaign_runs.outbox(
        db, ctx.workspace_id, campaign_runs.get(db, ctx.workspace_id, cid), limit
    )


@router.post("/runs/{cid}/mark-sent")
def mark_sent(cid: uuid.UUID, data: MarkSent, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    return campaign_runs.mark_sent(
        db, ctx.workspace_id, campaign_runs.get(db, ctx.workspace_id, cid), data.ids, ctx.user.id
    )


@router.get("/runs/{cid}/results")
def results(cid: uuid.UUID, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return campaign_runs.results(db, ctx.workspace_id, campaign_runs.get(db, ctx.workspace_id, cid))
