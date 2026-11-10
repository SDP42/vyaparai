"""Udhaar (credit): import a ledger, see who owes what and for how long, draft reminders."""

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import AnalystCtx, DbSession, ViewerCtx
from app.core.errors import AppError
from app.services import audit, credit

router = APIRouter(prefix="/workspaces/{workspace_id}/udhaar", tags=["udhaar"])
MAX_BYTES = 5 * 1024 * 1024


class EntryIn(BaseModel):
    party: str = Field(min_length=1, max_length=120)
    kind: str = Field(pattern="^(credit|payment)$")
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    entry_date: date | None = None
    phone: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=200)


def _today() -> date:
    return datetime.now(UTC).date()


def _ser(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        d = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in r.items() if k != "priority"}
        d["buckets"] = {k: str(v) for k, v in r.get("buckets", {}).items()}
        out.append(d)
    return out


@router.post("/import")
async def import_ledger(
    ctx: AnalystCtx, db: DbSession, file: Annotated[UploadFile, File()]
) -> dict[str, Any]:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise AppError("The file is larger than 5 MB.")
    res = credit.import_ledger(db, ctx.workspace_id, content)
    audit.record(
        db, action="udhaar.imported", actor_user_id=ctx.user.id, workspace_id=ctx.workspace_id,
        entity_type="udhaar", entity_id=None, details={"added": res["added"]},
    )  # fmt: skip
    db.commit()
    return res


@router.post("/entries", status_code=status.HTTP_201_CREATED)
def add_entry(data: EntryIn, ctx: AnalystCtx, db: DbSession) -> dict[str, Any]:
    e = credit.add_entry(
        db, ctx.workspace_id, party=data.party, entry_date=data.entry_date or _today(),
        kind=data.kind, amount=data.amount, phone=data.phone, note=data.note,
    )  # fmt: skip
    if e is None:
        raise AppError("That exact entry is already in the ledger")
    audit.record(
        db, action="udhaar.entry_added", actor_user_id=ctx.user.id, workspace_id=ctx.workspace_id,
        entity_type="udhaar", entity_id=None, details={"kind": data.kind},
    )  # fmt: skip
    db.commit()
    return {"ok": True}


@router.get("/summary")
def summary(ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    s = credit.summary(db, ctx.workspace_id, _today())
    return {**s, "outstanding": str(s["outstanding"]), "overdue": str(s["overdue"]),
            "buckets": {k: str(v) for k, v in s["buckets"].items()},
            "biggest": [{**b, "owed": str(b["owed"])} for b in s["biggest"]]}  # fmt: skip


@router.get("/parties")
def parties(
    ctx: ViewerCtx, db: DbSession, all_: Annotated[bool, Query(alias="all")] = False
) -> list[dict[str, Any]]:
    return _ser(credit.parties(db, ctx.workspace_id, _today(), only_owing=not all_))


@router.get("/parties/{key}")
def party(key: str, ctx: ViewerCtx, db: DbSession) -> dict[str, Any]:
    r = credit.ledger(db, ctx.workspace_id, key, _today())
    return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in r.items()}


@router.get("/reminders")
def reminders(
    ctx: AnalystCtx,
    db: DbSession,
    lang: Annotated[str, Query(pattern="^(en|hinglish|hi)$")] = "hinglish",
) -> list[dict[str, Any]]:
    rows = credit.reminders(db, ctx.workspace_id, ctx.workspace.name, _today(), lang)
    return [{**r, "owed": str(r["owed"])} for r in rows]


@router.get("/template.csv")
def template(ctx: ViewerCtx) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Name", "Phone", "Type", "Amount", "Note"])
    w.writerow(["2026-10-01", "Ramesh Sharma", "9876543210", "Credit", "850", "Monthly groceries"])
    w.writerow(["2026-10-12", "Ramesh Sharma", "9876543210", "Payment", "300", "UPI"])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="udhaar-template.csv"'})  # fmt: skip
