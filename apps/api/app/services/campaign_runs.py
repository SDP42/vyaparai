"""Consent, contacts, launching a campaign, the outbox a person sends from, and the measured result.

Rules that cannot be skipped:
- only customers with recorded consent, a phone number and no opt-out can be in a campaign;
- the holdout is drawn from that same eligible group (stable hash), so it is a fair comparison;
- nothing is sent by the product: each message is a WhatsApp link a person opens and sends, then marks as sent;
- an opt-out recorded after launch removes the person from the outbox at once;
- a daily cap limits how many can be marked sent, to keep messages personal and within platform norms.
"""

import csv
import io
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.campaign import Campaign, CampaignRecipient, CustomerContact
from app.models.commerce import Customer, Order, OrderItem, OrderStatus
from app.models.workspace import Workspace
from app.services import audit, campaigns, uplift
from app.services.credit import clean_phone

D = Decimal
GRANT_WORDS = {
    "yes",
    "y",
    "true",
    "1",
    "granted",
    "agreed",
    "opt in",
    "optin",
    "haan",
    "han",
    "हाँ",
    "हां",
}
DENY_WORDS = {
    "no",
    "n",
    "false",
    "0",
    "denied",
    "refused",
    "nahi",
    "nahin",
    "stop",
    "opt out",
    "optout",
    "नहीं",
}


def _today() -> date:
    return datetime.now(UTC).date()


# ------------------------------------------------------------------ contacts and consent


def mask(phone: str | None) -> str | None:
    return None if not phone else "•••• " + phone[-4:]


def upsert_contact(
    db: Session, ws: uuid.UUID, key: str, *, phone: str | None = None, consent: str | None = None,
    source: str | None = None, today: date | None = None,
) -> CustomerContact:  # fmt: skip
    today = today or _today()
    key = key.strip()
    if not key:
        raise AppError("Give the customer's key")
    c = db.scalars(
        select(CustomerContact).where(
            CustomerContact.workspace_id == ws, CustomerContact.customer_key == key
        )
    ).first()
    if c is None:
        c = CustomerContact(workspace_id=ws, customer_key=key, consent="unknown")
        db.add(c)
    if phone is not None:
        c.phone = clean_phone(phone)
    if consent is not None:
        if consent not in {"granted", "denied", "unknown"}:
            raise AppError("Consent must be granted, denied or unknown")
        if consent == "granted" and c.opted_out_at is not None and not source:
            raise AppError(
                "This customer opted out. Record where and when they agreed again before re-adding them."
            )
        c.consent = consent
        c.consent_date = today
        c.consent_source = (source or c.consent_source or "")[:80] or None
        if consent == "granted":
            c.opted_out_at = None  # an explicit new agreement after an opt-out
        elif consent == "denied":
            c.opted_out_at = c.opted_out_at or today
    return c


def opt_out(
    db: Session, ws: uuid.UUID, *, key: str | None, phone: str | None, today: date | None = None
) -> int:
    """Record a STOP. Matches by customer key or phone. Returns how many contacts were opted out."""
    today = today or _today()
    n = 0
    p = clean_phone(phone) if phone else None
    q_ = select(CustomerContact).where(CustomerContact.workspace_id == ws)
    for c in db.scalars(q_):
        if (key and c.customer_key == key.strip()) or (p and c.phone == p):
            c.consent, c.opted_out_at, c.consent_date = "denied", today, today
            n += 1
    if n == 0 and key:
        c = upsert_contact(
            db, ws, key, phone=phone, consent="denied", source="opt-out recorded", today=today
        )
        c.opted_out_at = today
        n = 1
    return n


def import_contacts(db: Session, ws: uuid.UUID, content: bytes) -> dict[str, Any]:
    text = None
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = content.decode(enc)
            break
        except UnicodeError:
            continue
    if text is None:
        raise AppError("The file could not be read. Save it as CSV (UTF-8).")
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        raise AppError("The file has no rows.")
    head = [re.sub(r"[_\-]+", " ", h.strip().lower()) for h in rows[0]]

    def col(names: set[str]) -> int | None:
        return next((i for i, h in enumerate(head) if h in names), None)

    ik = col({"customer", "customer key", "key", "id", "customer id", "name", "customer name"})
    ip = col({"phone", "mobile", "whatsapp", "phone no", "mobile no", "number"})
    ic = col({"consent", "agreed", "opt in", "whatsapp consent", "marketing consent"})
    isrc = col({"source", "consent source", "how"})
    if ik is None:
        raise AppError("Needed: a Customer column (the same key used in your sales file).")
    done = skipped = 0
    for r in rows[1:]:
        if not any(x.strip() for x in r):
            continue
        key = r[ik].strip() if ik < len(r) else ""
        if not key:
            skipped += 1
            continue
        raw = r[ic].strip().lower() if ic is not None and ic < len(r) else ""
        consent = "granted" if raw in GRANT_WORDS else "denied" if raw in DENY_WORDS else "unknown"
        phone = r[ip] if ip is not None and ip < len(r) else None
        src = r[isrc] if isrc is not None and isrc < len(r) else "imported list"
        try:
            upsert_contact(
                db, ws, key, phone=phone or None, consent=consent, source=src or "imported list"
            )
        except AppError:
            skipped += 1
            continue
        done += 1
    db.commit()
    return {"saved": done, "skipped": skipped}


def contacts_summary(db: Session, ws: uuid.UUID) -> dict[str, Any]:
    rows = list(db.scalars(select(CustomerContact).where(CustomerContact.workspace_id == ws)))
    total_customers = (
        db.scalar(select(func.count(Customer.id)).where(Customer.workspace_id == ws)) or 0
    )
    ok = [c for c in rows if c.consent == "granted" and c.phone and c.opted_out_at is None]
    return {
        "customers": int(total_customers), "recorded": len(rows),
        "reachable": len(ok), "granted": sum(c.consent == "granted" for c in rows),
        "denied": sum(c.consent == "denied" for c in rows), "unknown": sum(c.consent == "unknown" for c in rows),
        "opted_out": sum(c.opted_out_at is not None for c in rows), "no_phone": sum(1 for c in rows if not c.phone),
    }  # fmt: skip


def list_contacts(db: Session, ws: uuid.UUID, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(CustomerContact)
        .where(CustomerContact.workspace_id == ws)
        .order_by(CustomerContact.updated_at.desc())
        .limit(limit)
    )
    return [{"customer_key": c.customer_key, "phone": mask(c.phone), "consent": c.consent, "source": c.consent_source,
             "consent_date": c.consent_date.isoformat() if c.consent_date else None, "opted_out": c.opted_out_at is not None} for c in rows]  # fmt: skip


def eligible(db: Session, ws: uuid.UUID, keys: list[str]) -> dict[str, CustomerContact]:
    rows = db.scalars(
        select(CustomerContact).where(
            CustomerContact.workspace_id == ws, CustomerContact.customer_key.in_(keys)
        )
    )
    return {
        c.customer_key: c
        for c in rows
        if c.consent == "granted" and c.phone and c.opted_out_at is None
    }


# ------------------------------------------------------------------ launch and outbox


def launch(
    db: Session, workspace: Workspace, user_id: uuid.UUID, *, name: str, segment: str, holdout_pct: int, window_days: int,
    max_discount: int | None, margin_floor: int, language: campaigns.Language, valid_days: int,
) -> Campaign:  # fmt: skip
    p = campaigns.plan(
        db,
        workspace,
        segment=segment,
        as_of=None,
        lookback=365,
        max_discount=max_discount,
        margin_floor=margin_floor,
        holdout_pct=0,
        language=language,
        valid_days=valid_days,
    )
    rows = p["rows"]
    ok = eligible(db, workspace.id, [r["key"] for r in rows])
    elig = [r for r in rows if r["key"] in ok]
    if not elig:
        raise AppError(
            "Nobody in this segment has recorded consent and a phone number, so there is no one to message. Record consent first."
        )
    camp = Campaign(
        workspace_id=workspace.id, name=name.strip()[:120] or f"{segment} campaign", segment=segment, status="ready",
        params={**p["params"], "as_of": p["as_of"].isoformat()}, window_days=window_days, holdout_pct=holdout_pct, created_by_id=user_id,
        counts={"segment": len(rows), "eligible": len(elig), "no_consent_or_phone": len(rows) - len(elig)},
    )  # fmt: skip
    db.add(camp)
    db.flush()
    held = 0
    for r in elig:
        group = (
            "holdout"
            if campaigns.in_holdout(f"{segment}|{camp.id}", r["key"], holdout_pct)
            else "treatment"
        )
        held += group == "holdout"
        db.add(CampaignRecipient(workspace_id=workspace.id, campaign_id=camp.id, customer_key=r["key"], group=group, message=r["message"], product=r["product"], discount_pct=float(r["discount_pct"])))  # fmt: skip
    camp.counts = {**camp.counts, "treatment": len(elig) - held, "holdout": held}
    audit.record(
        db,
        action="campaign.launched",
        actor_user_id=user_id,
        workspace_id=workspace.id,
        entity_type="campaign",
        entity_id=camp.id,
        details=camp.counts,
    )
    db.commit()
    return camp


def get(db: Session, ws: uuid.UUID, cid: uuid.UUID) -> Campaign:
    c = db.get(Campaign, cid)
    if c is None or c.workspace_id != ws:
        raise NotFoundError("Campaign not found")
    return c


def listing(db: Session, ws: uuid.UUID) -> list[Campaign]:
    return list(
        db.scalars(
            select(Campaign).where(Campaign.workspace_id == ws).order_by(Campaign.created_at.desc())
        )
    )


def _sent_today(db: Session, ws: uuid.UUID, today: date) -> int:
    start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    return int(
        db.scalar(
            select(func.count(CampaignRecipient.id)).where(
                CampaignRecipient.workspace_id == ws,
                CampaignRecipient.status == "sent",
                CampaignRecipient.sent_at >= start,
            )
        )
        or 0
    )


def outbox(db: Session, ws: uuid.UUID, camp: Campaign, limit: int = 25) -> dict[str, Any]:
    """Pending treatment messages, with consent re-checked now. People who opted out meanwhile are skipped."""
    pend = list(
        db.scalars(
            select(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == camp.id,
                CampaignRecipient.group == "treatment",
                CampaignRecipient.status == "pending",
            )
            .order_by(CampaignRecipient.customer_key)
        )
    )
    ok = eligible(db, ws, [r.customer_key for r in pend])
    items = []
    for r in pend:
        if r.customer_key not in ok:
            r.status, r.skip_reason = "skipped", "opted_out_or_no_phone"
            continue
        c = ok[r.customer_key]
        items.append({"id": str(r.id), "customer_key": r.customer_key, "phone": mask(c.phone), "message": r.message, "product": r.product, "discount_pct": float(r.discount_pct),
                      "whatsapp": f"https://wa.me/{c.phone}?text={quote(r.message)}"})  # fmt: skip
    db.commit()
    cap = get_settings().campaign_daily_cap
    sent = _sent_today(db, ws, _today())
    return {
        "items": items[:limit],
        "pending": len(items),
        "sent_today": sent,
        "daily_cap": cap,
        "can_send_today": max(0, cap - sent),
    }


def mark_sent(
    db: Session, ws: uuid.UUID, camp: Campaign, ids: list[uuid.UUID], user_id: uuid.UUID
) -> dict[str, Any]:
    today = _today()
    room = get_settings().campaign_daily_cap - _sent_today(db, ws, today)
    if room <= 0:
        raise ConflictError("The daily limit of messages has been reached. Continue tomorrow.")
    recs = list(
        db.scalars(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == camp.id, CampaignRecipient.id.in_(ids)
            )
        )
    )
    ok = eligible(db, ws, [r.customer_key for r in recs])
    n = 0
    for r in recs:
        if r.group != "treatment" or r.status != "pending":
            continue
        if r.customer_key not in ok:
            r.status, r.skip_reason = "skipped", "opted_out_or_no_phone"
            continue
        if n >= room:
            break
        r.status, r.sent_at = "sent", datetime.now(UTC)
        n += 1
    if n and camp.started_on is None:
        camp.started_on, camp.status = today, "sending"
    audit.record(
        db,
        action="campaign.sent_marked",
        actor_user_id=user_id,
        workspace_id=ws,
        entity_type="campaign",
        entity_id=camp.id,
        details={"count": n},
    )
    db.commit()
    return {"marked": n, "left_today": max(0, room - n)}


# ------------------------------------------------------------------ results


def _spend(
    db: Session, ws: uuid.UUID, keys: list[str], start: date, end: date
) -> dict[str, tuple[float, float]]:
    """Per customer: (net revenue, profit) from completed orders in the window. Profit counts only lines with a cost."""
    net = OrderItem.quantity * OrderItem.unit_price - OrderItem.discount_amount
    cost = func.sum(func.coalesce(OrderItem.quantity * OrderItem.unit_cost_snapshot, 0))
    out: dict[str, tuple[float, float]] = {}
    for i in range(0, len(keys), 500):
        chunk = keys[i : i + 500]
        stmt = (
            select(Customer.external_key, func.sum(net), cost, func.sum(net * (OrderItem.unit_cost_snapshot.is_not(None))))
            .join(Order, Order.customer_id == Customer.id).join(OrderItem, OrderItem.order_id == Order.id)
            .where(Customer.workspace_id == ws, Customer.external_key.in_(chunk), Order.status == OrderStatus.COMPLETED, Order.business_date >= start, Order.business_date <= end)
            .group_by(Customer.external_key)
        )  # fmt: skip
        for k, n_, c_, costed_net in db.execute(stmt).all():
            revenue = float(n_ or 0)
            profit = float((costed_net or 0) - (c_ or 0))
            out[k] = (revenue, profit)
    return out


def results(
    db: Session, ws: uuid.UUID, camp: Campaign, today: date | None = None
) -> dict[str, Any]:
    today = today or _today()
    base: dict[str, Any] = {
        "campaign": camp.name,
        "status": camp.status,
        "counts": camp.counts,
        "window_days": camp.window_days,
    }
    if camp.started_on is None:
        return {
            **base,
            "ready": False,
            "message": "Nothing has been sent yet. Results are measured from the day the first message goes out.",
        }
    end = camp.started_on + timedelta(days=camp.window_days - 1)
    final = today > end
    window_end = min(end, today)
    recs = list(
        db.scalars(select(CampaignRecipient).where(CampaignRecipient.campaign_id == camp.id))
    )
    treated = [r.customer_key for r in recs if r.group == "treatment" and r.status == "sent"]
    held = [r.customer_key for r in recs if r.group == "holdout"]
    spend = _spend(db, ws, treated + held, camp.started_on, window_end)

    def person(k: str) -> uplift.Person:
        rev, pro = spend.get(k, (0.0, 0.0))
        return uplift.Person(k in spend, rev, pro)

    res = uplift.compare([person(k) for k in treated], [person(k) for k in held])
    unsent = sum(1 for r in recs if r.group == "treatment" and r.status == "pending")
    return {**base, "ready": True, "final": final, "from": camp.started_on.isoformat(), "to": window_end.isoformat(), "days_left": max(0, (end - today).days),
            "not_sent_yet": unsent, "skipped": sum(1 for r in recs if r.status == "skipped"), **res}  # fmt: skip
