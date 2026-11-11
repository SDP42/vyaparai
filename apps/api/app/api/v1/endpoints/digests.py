"""Owner digest: preview it, choose when it goes out, send it now, see what was sent.

GET  /workspaces/{id}/digests/preview?kind=daily|weekly   build one now, nothing stored (viewer)
GET  /workspaces/{id}/digests/settings                    delivery settings (viewer)
PUT  /workspaces/{id}/digests/settings                    change them (admin)
POST /workspaces/{id}/digests/send-now?kind=...           store and email to the recipients (admin)
GET  /workspaces/{id}/digests/history                     the digests already generated (viewer)
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import AdminCtx, DbSession, ViewerCtx
from app.api.masking import MaskedRoute
from app.models.digest import Digest
from app.schemas.digest import DigestPreview, DigestRead, DigestSettingsIn, DigestSettingsOut
from app.services import audit, digest, digest_delivery, mailer

router = APIRouter(
    prefix="/workspaces/{workspace_id}/digests", tags=["digests"], route_class=MaskedRoute
)
KindQ = Annotated[digest.Kind, Query()]


def _settings_out(db: DbSession, ctx: ViewerCtx | AdminCtx) -> dict[str, Any]:
    st = digest_delivery.get_or_create_settings(db, ctx.workspace_id)
    return {
        "enabled": st.enabled,
        "frequency": st.frequency,
        "send_hour": st.send_hour,
        "weekday": st.weekday,
        "recipients": list(st.recipients or []),
        "email_configured": mailer.configured(),
        "timezone": ctx.workspace.timezone,
        "last_daily_for": st.last_daily_for,
        "last_weekly_for": st.last_weekly_for,
    }


@router.get("/preview", response_model=DigestPreview)
def preview(
    ctx: ViewerCtx, db: DbSession, kind: KindQ = "daily", as_of: date | None = None
) -> dict[str, Any]:
    built = digest.build(db, ctx.workspace, kind, as_of=as_of)
    if built is None:
        raise digest_delivery.NoSalesError("There are no completed sales to summarise yet.")
    return built


@router.get("/settings", response_model=DigestSettingsOut)
def get_settings_(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    return _settings_out(db, ctx)


@router.put("/settings", response_model=DigestSettingsOut)
def put_settings(data: DigestSettingsIn, ctx: AdminCtx, db: DbSession) -> dict[str, Any]:
    st = digest_delivery.get_or_create_settings(db, ctx.workspace_id)
    st.enabled, st.frequency = data.enabled, data.frequency
    st.send_hour, st.weekday = data.send_hour, data.weekday
    st.recipients = sorted({str(e).lower() for e in data.recipients})
    st.updated_by_id = ctx.user.id
    audit.record(
        db,
        action="digest.settings_changed",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="digest_settings",
        entity_id=st.id,
        details={
            "enabled": data.enabled,
            "frequency": data.frequency,
            "recipients": len(st.recipients),
        },
    )
    db.commit()
    return _settings_out(db, ctx)


@router.post("/send-now", response_model=DigestRead)
def send_now(ctx: AdminCtx, db: DbSession, kind: KindQ = "daily") -> Digest:
    row = digest_delivery.send_now(db, ctx.workspace, kind)
    audit.record(
        db,
        action="digest.sent",
        actor_user_id=ctx.user.id,
        workspace_id=ctx.workspace_id,
        entity_type="digest",
        entity_id=row.id,
        details={"kind": kind, "status": row.status, "recipients": len(row.sent_to)},
    )
    db.commit()
    return row


@router.get("/history", response_model=list[DigestRead])
def history(
    ctx: ViewerCtx, db: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[Digest]:
    stmt = (
        select(Digest)
        .where(Digest.workspace_id == ctx.workspace_id)
        .order_by(Digest.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
