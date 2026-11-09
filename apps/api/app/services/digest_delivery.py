"""Store digests, send them, and decide which are due. Run ``python -m app.digest_runner`` on a schedule."""

import uuid
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.digest import Digest, DigestSettings
from app.models.workspace import Workspace
from app.services import digest, mailer


class NoRecipientsError(AppError):
    status_code = 422
    code = "no_recipients"


class NoSalesError(AppError):
    status_code = 422
    code = "no_sales"


def get_or_create_settings(db: Session, ws: uuid.UUID) -> DigestSettings:
    row = db.scalars(select(DigestSettings).where(DigestSettings.workspace_id == ws)).first()
    if row is None:
        row = DigestSettings(workspace_id=ws, recipients=[])
        db.add(row)
        db.commit()
    return row


def deliver(
    db: Session,
    workspace: Workspace,
    kind: digest.Kind,
    recipients: list[str],
    *,
    today: Any = None,
) -> Digest | None:
    """Build, store and (when possible) email one digest. None when there are no sales yet."""
    built = digest.build(db, workspace, kind, today=today)
    if built is None:
        return None
    status, error = "stored", None
    if recipients:
        if not mailer.configured():
            status = "not_configured"
        else:
            try:
                mailer.send_email(recipients, built["subject"], built["text"], built["html"])
                status = "sent"
            except mailer.MailError as exc:
                status, error = "failed", str(exc)
    row = Digest(
        workspace_id=workspace.id,
        kind=kind,
        period_end=built["as_of"],
        subject=built["subject"],
        text=built["text"],
        payload={
            k: (v.isoformat() if isinstance(v, date) else v)
            for k, v in built.items()
            if k not in ("text", "html")
        },
        sent_to=recipients if status == "sent" else [],
        status=status,
        error=error,
    )
    db.add(row)
    db.commit()
    return row


def send_now(db: Session, workspace: Workspace, kind: digest.Kind) -> Digest:
    st = get_or_create_settings(db, workspace.id)
    if not st.recipients:
        raise NoRecipientsError("Add at least one recipient first.")
    row = deliver(db, workspace, kind, list(st.recipients))
    if row is None:
        raise NoSalesError("There are no completed sales to summarise yet.")
    return row


def run_due(db: Session, now: datetime | None = None) -> list[dict[str, Any]]:
    """Send every digest that is due at ``now`` (UTC) and has not been handled for the local date."""
    now = now or datetime.now(UTC)
    results: list[dict[str, Any]] = []
    for st in db.scalars(select(DigestSettings).where(DigestSettings.enabled.is_(True))).all():
        ws = db.get(Workspace, st.workspace_id)
        if ws is None:
            continue
        local = now.astimezone(ZoneInfo(ws.timezone))
        due: list[digest.Kind] = []
        if (
            st.frequency in ("daily", "both")
            and local.hour >= st.send_hour
            and st.last_daily_for != local.date()
        ):
            due.append("daily")
        if (
            st.frequency in ("weekly", "both")
            and local.weekday() == st.weekday
            and local.hour >= st.send_hour
            and st.last_weekly_for != local.date()
        ):
            due.append("weekly")
        for kind in due:
            row = deliver(db, ws, kind, list(st.recipients), today=local.date())
            if row is None:
                continue
            if kind == "daily":
                st.last_daily_for = local.date()
            else:
                st.last_weekly_for = local.date()
            db.commit()
            results.append({"workspace": str(ws.id), "kind": kind, "status": row.status})
    return results
