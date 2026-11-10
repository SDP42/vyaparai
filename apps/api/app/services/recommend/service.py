"""Rank candidates, keep them with an approval lifecycle, and record who decided what.

Statuses: proposed -> approved (the owner will do it) -> done; or dismissed. An item whose cause has
gone away becomes stale. Approving never changes business data: it records the decision and keeps the
item on the to-do list; the action itself happens on the linked page, by a person.
"""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.recommendation import Recommendation
from app.models.workspace import Workspace
from app.services import audit
from app.services.recommend import candidates

CONF_W = {"high": 1.0, "medium": 0.7, "low": 0.4}
EFFORT_W = {"S": 1.0, "M": 1.6, "L": 2.5}
TRANSITIONS = {
    "approve": ({"proposed", "stale"}, "approved"),
    "dismiss": ({"proposed", "approved", "stale"}, "dismissed"),
    "done": ({"approved", "proposed"}, "done"),
    "reopen": ({"dismissed", "done", "approved"}, "proposed"),
}


def score(c: dict[str, Any]) -> float:
    exp = c["impact"].get("expected")
    if exp is None:
        return 0.0
    return float(exp) * CONF_W[c["confidence"]] / EFFORT_W[c["effort"]]


def refresh(db: Session, workspace: Workspace, today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for gen in candidates.GENERATORS:
        try:
            for c in gen(db, workspace, today):
                found[c["key"]] = c
        except Exception as exc:  # one broken signal must not hide the others
            errors.append(f"{gen.__name__}: {type(exc).__name__}")
    existing = {
        r.key: r
        for r in db.scalars(
            select(Recommendation).where(Recommendation.workspace_id == workspace.id)
        )
    }
    new = 0
    for key, c in found.items():
        r = existing.get(key)
        if r is None:
            r = Recommendation(
                workspace_id=workspace.id, key=key, first_seen=today, status="proposed"
            )
            db.add(r)
            new += 1
        elif r.status == "stale":
            r.status = "proposed"  # the cause is back
        r.kind, r.title, r.why, r.evidence, r.impact = (
            c["kind"],
            c["title"],
            c["why"],
            c["evidence"],
            c["impact"],
        )
        r.effort, r.confidence, r.link, r.last_seen, r.score = (
            c["effort"],
            c["confidence"],
            c["link"],
            today,
            score(c),
        )
    stale = 0
    for key, r in existing.items():
        if key not in found and r.status in {"proposed", "approved"} and not errors:
            r.status = "stale"
            stale += 1
    db.commit()
    return {"found": len(found), "new": new, "stale": stale, "errors": errors}


def listing(db: Session, ws: uuid.UUID, status: str) -> list[Recommendation]:
    stmt = select(Recommendation).where(Recommendation.workspace_id == ws)
    if status != "all":
        stmt = stmt.where(Recommendation.status == status)
    return sorted(db.scalars(stmt), key=lambda r: (-r.score, r.title))


def summary(db: Session, ws: uuid.UUID) -> dict[str, Any]:
    rows = list(db.scalars(select(Recommendation).where(Recommendation.workspace_id == ws)))
    counts = {
        s: sum(1 for r in rows if r.status == s)
        for s in ("proposed", "approved", "done", "dismissed", "stale")
    }
    prop = [r for r in rows if r.status == "proposed"]
    lo = sum((r.impact.get("low") or 0) for r in prop)
    exp = sum((r.impact.get("expected") or 0) for r in prop)
    hi = sum((r.impact.get("high") or 0) for r in prop)
    return {
        "counts": counts,
        "proposed_impact": {
            "low": lo,
            "expected": exp,
            "high": hi,
            "unestimated": sum(1 for r in prop if r.impact.get("expected") is None),
        },
    }


def decide(
    db: Session, ws: uuid.UUID, rec_id: uuid.UUID, action: str, user_id: uuid.UUID, note: str | None
) -> Recommendation:
    r = db.get(Recommendation, rec_id)
    if r is None or r.workspace_id != ws:
        raise NotFoundError("Recommendation not found")
    allowed, target = TRANSITIONS[action]
    if r.status not in allowed:
        raise AppError(f"A {r.status} item cannot be {action}d")
    r.status = target
    r.note = (note or None) and note.strip()[:300]
    r.decided_at = datetime.now(UTC)
    r.decided_by_id = user_id
    audit.record(
        db,
        action=f"recommendation.{action}",
        actor_user_id=user_id,
        workspace_id=ws,
        entity_type="recommendation",
        entity_id=r.id,
        details={"kind": r.kind, "to": target},
    )
    db.commit()
    return r
