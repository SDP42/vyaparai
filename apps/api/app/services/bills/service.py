"""Create, edit and confirm purchase bills; track what each supplier charged over time.

A bill starts as a draft read by the machine. A person checks and confirms it. Only confirmed
bills change anything: the product's unit cost is set from the newest confirmed bill, and the
price history per product and supplier is built from confirmed bills alone.
"""

import hashlib
import re
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.bill import PurchaseBill, PurchaseBillLine
from app.models.commerce import Product
from app.services import audit
from app.services.bills import parser, reader

D = Decimal
MATCH_MIN = 0.62
PRICE_ALERT_PCT = D(5)


class BillStateError(AppError):
    status_code = 409
    code = "invalid_state"


def _norm(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in {"the", "of", "and", "pack"}]


def match_score(a: str, b: str) -> float:
    ta, tb = _norm(a), _norm(b)
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    jaccard = len(sa & sb) / len(sa | sb)
    contain = len(sa & sb) / min(len(sa), len(sb))
    seq = SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return max(0.5 * jaccard + 0.5 * seq, 0.85 * contain if len(sa & sb) >= 2 else 0.0)


def match_product(description: str, products: list[Product]) -> uuid.UUID | None:
    best, best_id = 0.0, None
    for p in products:
        s = max(
            match_score(description, p.name),
            1.0 if description.strip().lower() == p.sku.lower() else 0.0,
        )
        if s > best:
            best, best_id = s, p.id
    return best_id if best >= MATCH_MIN else None


def _q(x: Decimal, places: str) -> Decimal:
    return x.quantize(D(places), rounding=ROUND_HALF_UP)


def create_from_file(
    db: Session, ws: uuid.UUID, user_id: uuid.UUID, content: bytes
) -> PurchaseBill:
    fh = hashlib.sha256(content).hexdigest()
    dup = db.scalars(
        select(PurchaseBill).where(PurchaseBill.workspace_id == ws, PurchaseBill.file_hash == fh)
    ).first()
    if dup is not None:
        raise ConflictError("This exact file was already added", details={"bill_id": str(dup.id)})
    res = reader.read_bill(content)
    parsed = parser.parse(res.lines)
    products = list(db.scalars(select(Product).where(Product.workspace_id == ws)))
    bill = PurchaseBill(
        workspace_id=ws, status="draft", supplier=parsed.supplier, gstin=parsed.gstin,
        bill_no=parsed.bill_no, bill_date=parsed.bill_date, total=parsed.total, engine=res.engine,
        file_hash=fh, raw_text="\n".join(res.lines)[:20000],
        warnings="\n".join(res.warnings + parsed.warnings), created_by_id=user_id,
    )  # fmt: skip
    for i, ln in enumerate(parsed.lines):
        bill.lines.append(
            PurchaseBillLine(
                workspace_id=ws, position=i, description=ln.description, quantity=ln.quantity,
                unit_price=ln.unit_price, amount=ln.amount, unit=ln.unit,
                confidence=ln.confidence, product_id=match_product(ln.description, products),
            )
        )  # fmt: skip
    db.add(bill)
    audit.record(
        db, action="bill.read", actor_user_id=user_id, workspace_id=ws,
        entity_type="purchase_bill", entity_id=None,
        details={"engine": res.engine, "lines": len(parsed.lines)},
    )  # fmt: skip
    db.commit()
    return bill


def get(db: Session, ws: uuid.UUID, bill_id: uuid.UUID) -> PurchaseBill:
    b = db.get(PurchaseBill, bill_id)
    if b is None or b.workspace_id != ws:
        raise NotFoundError("Bill not found")
    return b


def update(db: Session, bill: PurchaseBill, data: dict[str, Any]) -> PurchaseBill:
    if bill.status == "confirmed":
        raise BillStateError("A confirmed bill cannot be edited")
    for k in ("supplier", "gstin", "bill_no", "bill_date", "total"):
        if k in data:
            setattr(bill, k, data[k])
    if "lines" in data and data["lines"] is not None:
        products = {
            p.id
            for p in db.scalars(select(Product).where(Product.workspace_id == bill.workspace_id))
        }
        bill.lines.clear()
        db.flush()
        for i, ln in enumerate(data["lines"]):
            pid = ln.get("product_id")
            if pid is not None and pid not in products:
                raise AppError("A line points to a product that is not in this workspace")
            qty, rate = D(str(ln["quantity"])), D(str(ln["unit_price"]))
            bill.lines.append(
                PurchaseBillLine(
                    workspace_id=bill.workspace_id, position=i,
                    description=str(ln["description"])[:255], quantity=qty, unit_price=rate,
                    amount=_q(ln.get("amount") if ln.get("amount") is not None else qty * rate, "0.01"),
                    unit=ln.get("unit"), confidence="high", product_id=pid,
                )
            )  # fmt: skip
    db.commit()
    return bill


def confirm(db: Session, bill: PurchaseBill, actor_id: uuid.UUID) -> dict[str, Any]:
    if bill.status == "confirmed":
        raise BillStateError("This bill is already confirmed")
    if bill.bill_date is None:
        raise AppError("Set the bill date before confirming")
    if not bill.lines:
        raise AppError("Add at least one line before confirming")
    changes: list[dict[str, Any]] = []
    for ln in bill.lines:
        if ln.product_id is None:
            continue
        before = previous_price(db, bill.workspace_id, ln.product_id, bill.bill_date, bill.supplier)
        pct = (
            None
            if before is None or before == 0
            else _q((ln.unit_price - before) / before * 100, "0.1")
        )
        changes.append(
            {"product_id": str(ln.product_id), "description": ln.description,
             "price": str(ln.unit_price), "previous": None if before is None else str(before),
             "change_pct": None if pct is None else str(pct)}
        )  # fmt: skip
    bill.status = "confirmed"
    db.flush()
    for ln in bill.lines:
        if ln.product_id is None:
            continue
        newest = latest_confirmed_date(db, bill.workspace_id, ln.product_id)
        if newest is None or bill.bill_date >= newest:
            p = db.get(Product, ln.product_id)
            if p is not None:
                p.unit_cost = _q(ln.unit_price, "0.01")
    audit.record(
        db, action="bill.confirmed", actor_user_id=actor_id, workspace_id=bill.workspace_id,
        entity_type="purchase_bill", entity_id=bill.id,
        details={"lines": len(bill.lines), "matched": sum(1 for x in bill.lines if x.product_id)},
    )  # fmt: skip
    db.commit()
    return {"bill_id": str(bill.id), "changes": changes,
            "unmatched": sum(1 for x in bill.lines if x.product_id is None)}  # fmt: skip


def delete_draft(db: Session, bill: PurchaseBill, actor_id: uuid.UUID) -> None:
    if bill.status == "confirmed":
        raise BillStateError("A confirmed bill cannot be deleted")
    audit.record(
        db, action="bill.discarded", actor_user_id=actor_id, workspace_id=bill.workspace_id,
        entity_type="purchase_bill", entity_id=bill.id,
    )  # fmt: skip
    db.delete(bill)
    db.commit()


# ------------------------------------------------------------------ price history


def _confirmed_prices(
    db: Session, ws: uuid.UUID, product_id: uuid.UUID
) -> list[tuple[date, str | None, Decimal]]:
    rows = db.execute(
        select(PurchaseBill.bill_date, PurchaseBill.supplier, PurchaseBillLine.unit_price)
        .join(PurchaseBill, PurchaseBill.id == PurchaseBillLine.bill_id)
        .where(
            PurchaseBillLine.workspace_id == ws,
            PurchaseBillLine.product_id == product_id,
            PurchaseBill.status == "confirmed",
            PurchaseBill.bill_date.is_not(None),
        )
        .order_by(PurchaseBill.bill_date)
    ).all()
    return [(r[0], r[1], r[2]) for r in rows if r[0] is not None]


def latest_confirmed_date(db: Session, ws: uuid.UUID, product_id: uuid.UUID) -> date | None:
    prices = _confirmed_prices(db, ws, product_id)
    return prices[-1][0] if prices else None


def previous_price(
    db: Session, ws: uuid.UUID, product_id: uuid.UUID, before: date, supplier: str | None
) -> Decimal | None:
    """The last confirmed price strictly before this bill, preferring the same supplier."""
    prior = [p for p in _confirmed_prices(db, ws, product_id) if p[0] < before]
    same = [p for p in prior if p[1] == supplier]
    pick = same or prior
    return pick[-1][2] if pick else None


def price_moves(
    db: Session, ws: uuid.UUID, min_pct: Decimal = PRICE_ALERT_PCT
) -> list[dict[str, Any]]:
    """Products whose latest confirmed purchase price differs from the one before it."""
    names = {p.id: p for p in db.scalars(select(Product).where(Product.workspace_id == ws))}
    out: list[dict[str, Any]] = []
    for pid, p in names.items():
        hist = _confirmed_prices(db, ws, pid)
        if len(hist) < 2:
            continue
        (d0, _, old), (d1, sup, new) = hist[-2], hist[-1]
        if old <= 0:
            continue
        pct = (new - old) / old * 100
        if abs(pct) >= min_pct:
            out.append(
                {"product_id": str(pid), "sku": p.sku, "name": p.name, "supplier": sup,
                 "previous": str(old), "latest": str(new), "change_pct": float(_q(pct, "0.1")),
                 "previous_date": d0.isoformat(), "latest_date": d1.isoformat(),
                 "list_price": None if p.list_price is None else str(p.list_price)}
            )  # fmt: skip
    return sorted(out, key=lambda x: -abs(x["change_pct"]))


def history(db: Session, ws: uuid.UUID, product_id: uuid.UUID) -> list[dict[str, Any]]:
    if db.get(Product, product_id) is None:
        raise NotFoundError("Product not found")
    return [
        {"date": d.isoformat(), "supplier": s, "unit_price": str(p)}
        for d, s, p in _confirmed_prices(db, ws, product_id)
    ]
