"""Udhaar: who owes what, for how long, who to remind first, and a polite message to send.

Rules (docs/UDHAAR.md):
- balance = credits given minus payments received, per person;
- payments settle the OLDEST credit first (FIFO), so what is still owed has an honest age;
- age buckets 0-30, 31-60, 61-90, 90+ days; "overdue" means older than 30 days;
- reminders are drafted for a person to send; nothing is sent automatically.
"""

import csv
import hashlib
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.credit import CreditEntry
from app.services.bills.parser import parse_date, to_decimal

D = Decimal
BUCKETS = [(0, 30, "0-30"), (31, 60, "31-60"), (61, 90, "61-90"), (91, 100000, "90+")]
OVERDUE_DAYS = 30
MAX_ROWS = 20_000

HEADERS = {
    "date": {"date", "dt", "entry date", "tarikh", "तारीख"},
    "party": {"party", "name", "customer", "customer name", "party name", "naam", "नाम", "grahak"},
    "phone": {"phone", "mobile", "mobile no", "phone no", "contact", "number", "whatsapp"},
    "kind": {"type", "kind", "entry", "transaction", "txn", "nature"},
    "amount": {"amount", "amt", "rs", "value", "rupees", "रकम"},
    "credit": {"credit", "given", "udhaar", "udhar", "debit", "gave", "diya", "उधार"},
    "payment": {"payment", "received", "paid", "jama", "got", "wapas", "जमा"},
    "note": {"note", "notes", "remark", "remarks", "narration", "details", "item"},
}  # fmt: skip
CREDIT_WORDS = {"credit", "given", "udhaar", "udhar", "gave", "sale", "debit", "diya", "उधार", "dr"}
PAYMENT_WORDS = {
    "payment",
    "received",
    "paid",
    "jama",
    "cash",
    "upi",
    "return",
    "wapas",
    "जमा",
    "cr",
    "got",
}


class BadLedgerError(AppError):
    status_code = 422
    code = "bad_ledger_file"


def party_key(name: str) -> str:
    return re.sub(r"[^a-z0-9ऀ-ॿ]+", " ", name.lower()).strip()[:120]


def clean_phone(raw: str | None) -> str | None:
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 10:
        d = "91" + d  # Indian mobile without country code
    return d if 11 <= len(d) <= 15 else None


def _fp(ws: uuid.UUID, party: str, d: date, kind: str, amount: Decimal, note: str | None) -> str:
    return hashlib.sha256(
        f"{ws}|{party_key(party)}|{d}|{kind}|{amount}|{(note or '').lower()}".encode()
    ).hexdigest()


# ------------------------------------------------------------------ import and entry


def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeError:
            continue
    raise BadLedgerError("The file could not be read. Save it as CSV (UTF-8).")


def _map(headers: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for i, h in enumerate(headers):
        k = re.sub(r"[_\-]+", " ", h.strip().lower())
        for field_, names in HEADERS.items():
            if k in names and field_ not in found:
                found[field_] = i
    return found


def add_entry(
    db: Session, ws: uuid.UUID, *, party: str, entry_date: date, kind: str, amount: Decimal,
    phone: str | None = None, note: str | None = None, source: str = "manual",
) -> CreditEntry | None:  # fmt: skip
    """Returns None if an identical entry already exists (safe to re-import)."""
    if kind not in {"credit", "payment"}:
        raise AppError("Kind must be credit or payment")
    if amount <= 0:
        raise AppError("Amount must be more than zero")
    if not party_key(party):
        raise AppError("Give the person's name")
    fp = _fp(ws, party, entry_date, kind, amount, note)
    if db.scalars(
        select(CreditEntry.id).where(CreditEntry.workspace_id == ws, CreditEntry.fingerprint == fp)
    ).first():
        return None
    e = CreditEntry(
        workspace_id=ws, fingerprint=fp, party_key=party_key(party), party_name=party.strip()[:120],
        phone=clean_phone(phone), entry_date=entry_date, kind=kind, amount=amount.quantize(D("0.01")),
        note=(note or None) and note.strip()[:200], source=source,
    )  # fmt: skip
    db.add(e)
    return e


def import_ledger(db: Session, ws: uuid.UUID, content: bytes) -> dict[str, Any]:
    rows = list(csv.reader(io.StringIO(_decode(content))))
    if len(rows) < 2:
        raise BadLedgerError("The file has no entries.")
    c = _map(rows[0])
    if (
        "party" not in c
        or "date" not in c
        or not ({"amount"} <= set(c) or {"credit", "payment"} & set(c))
    ):
        raise BadLedgerError(
            "Needed columns: Date, Name, and an Amount (with a Type), or separate Credit and Payment columns."
        )
    if len(rows) - 1 > MAX_ROWS:
        raise BadLedgerError(f"Too many rows (limit {MAX_ROWS}).")
    added = dupes = 0
    rejects: list[dict[str, Any]] = []

    def cell(r: list[str], f: str) -> str:
        i = c.get(f)
        return r[i].strip() if i is not None and i < len(r) else ""

    for n, r in enumerate(rows[1:], start=2):
        if not any(x.strip() for x in r):
            continue
        d = parse_date(cell(r, "date"))
        party = cell(r, "party")
        entries: list[tuple[str, Decimal]] = []
        if "amount" in c:
            amt = to_decimal(cell(r, "amount").replace("Rs", "").replace("rs", "").strip() or "x")
            kw = set(re.findall(r"[a-zऀ-ॿ]+", cell(r, "kind").lower()))
            kind = "credit" if kw & CREDIT_WORDS else "payment" if kw & PAYMENT_WORDS else None
            if amt is not None and amt < 0:  # a negative amount is a repayment in many exports
                kind, amt = kind or "payment", -amt
            if amt is not None and kind:
                entries.append((kind, amt))
        else:
            for k in ("credit", "payment"):
                v = to_decimal(cell(r, k) or "x") if k in c else None
                if v is not None and v > 0:
                    entries.append((k, v))
        if d is None or not party or not entries:
            rejects.append({"row": n, "reason": "date, name, or amount/type not understood"})
            continue
        for kind, amt in entries:
            try:
                e = add_entry(db, ws, party=party, entry_date=d, kind=kind, amount=amt,
                              phone=cell(r, "phone"), note=cell(r, "note"), source="import")  # fmt: skip
            except AppError as exc:
                rejects.append({"row": n, "reason": exc.message})
                continue
            if e is None:
                dupes += 1
            else:
                added += 1
                db.flush()
    db.commit()
    return {
        "added": added,
        "duplicates": dupes,
        "rejected": rejects[:30],
        "rejected_count": len(rejects),
    }


# ------------------------------------------------------------------ ageing


@dataclass(slots=True)
class Open:
    date: date
    amount: Decimal


@dataclass(slots=True)
class Party:
    key: str
    name: str
    phone: str | None = None
    credits: list[tuple[date, Decimal]] = field(default_factory=list)
    payments: list[tuple[date, Decimal]] = field(default_factory=list)


def settle(
    credits: list[tuple[date, Decimal]], payments: list[tuple[date, Decimal]]
) -> tuple[list[Open], Decimal]:
    """FIFO: payments settle the oldest credit first. Returns (still-owed pieces, advance paid)."""
    owed = [Open(d, a) for d, a in sorted(credits)]
    paid = sum((a for _, a in payments), D(0))
    for o in owed:
        take = min(o.amount, paid)
        o.amount -= take
        paid -= take
    return [o for o in owed if o.amount > 0], paid


def _bucket(age: int) -> str:
    return next(label for lo, hi, label in BUCKETS if lo <= age <= hi)


def _parties(db: Session, ws: uuid.UUID) -> dict[str, Party]:
    out: dict[str, Party] = {}
    for e in db.scalars(
        select(CreditEntry).where(CreditEntry.workspace_id == ws).order_by(CreditEntry.entry_date)
    ):
        p = out.setdefault(e.party_key, Party(e.party_key, e.party_name))
        p.name = e.party_name
        p.phone = e.phone or p.phone
        (p.credits if e.kind == "credit" else p.payments).append((e.entry_date, e.amount))
    return out


def _row(p: Party, today: date) -> dict[str, Any]:
    pieces, advance = settle(p.credits, p.payments)
    owed = sum((o.amount for o in pieces), D(0))
    oldest = min((o.date for o in pieces), default=None)
    age = (today - oldest).days if oldest else 0
    last_pay = max((d for d, _ in p.payments), default=None)
    since_pay = (today - last_pay).days if last_pay else None
    if owed == 0:
        behaviour = "settled"
    elif since_pay is not None and since_pay <= 30:
        behaviour = "paying"
    elif age > 60 and (since_pay is None or since_pay > 60):
        behaviour = "stalled"
    else:
        behaviour = "slow"
    buckets = {label: D(0) for _, _, label in BUCKETS}
    for o in pieces:
        buckets[_bucket((today - o.date).days)] += o.amount
    # chase the person where amount and age together matter most (rupees x months, capped at 4)
    priority = float(owed) * min(4.0, max(0.5, age / 30))
    return {
        "key": p.key, "name": p.name, "phone": p.phone, "owed": owed, "oldest_days": age,
        "last_payment": last_pay.isoformat() if last_pay else None, "behaviour": behaviour,
        "advance": advance, "buckets": buckets, "priority": priority,
        "oldest_date": oldest.isoformat() if oldest else None,
    }  # fmt: skip


def parties(
    db: Session, ws: uuid.UUID, today: date, *, only_owing: bool = True
) -> list[dict[str, Any]]:
    rows = [_row(p, today) for p in _parties(db, ws).values()]
    if only_owing:
        rows = [r for r in rows if r["owed"] > 0]
    return sorted(rows, key=lambda r: -r["priority"])


def summary(db: Session, ws: uuid.UUID, today: date) -> dict[str, Any]:
    rows = parties(db, ws, today)
    buckets = {label: D(0) for _, _, label in BUCKETS}
    for r in rows:
        for k, v in r["buckets"].items():
            buckets[k] += v
    total = sum((r["owed"] for r in rows), D(0))
    overdue = sum((v for k, v in buckets.items() if k != "0-30"), D(0))
    q = D("0.01")
    return {
        "as_of": today.isoformat(), "outstanding": total.quantize(q), "parties_owing": len(rows),
        "overdue": overdue.quantize(q), "overdue_pct": float((overdue / total * 100).quantize(D("0.1"))) if total else 0.0,
        "buckets": {k: v.quantize(q) for k, v in buckets.items()},
        "stalled": sum(1 for r in rows if r["behaviour"] == "stalled"),
        "biggest": [{"name": r["name"], "owed": r["owed"].quantize(q), "oldest_days": r["oldest_days"]}
                    for r in sorted(rows, key=lambda r: -r["owed"])[:5]],
        "has_data": bool(_parties(db, ws)),
    }  # fmt: skip


def ledger(db: Session, ws: uuid.UUID, key: str, today: date) -> dict[str, Any]:
    ps = _parties(db, ws)
    if key not in ps:
        raise AppError("No such person in the ledger")
    entries = db.scalars(
        select(CreditEntry)
        .where(CreditEntry.workspace_id == ws, CreditEntry.party_key == key)
        .order_by(CreditEntry.entry_date.desc(), CreditEntry.created_at.desc())
    )
    return {**{k: v for k, v in _row(ps[key], today).items() if k != "buckets"},
            "entries": [{"date": e.entry_date.isoformat(), "kind": e.kind, "amount": str(e.amount), "note": e.note} for e in entries]}  # fmt: skip


# ------------------------------------------------------------------ reminders


def _inr(v: Decimal) -> str:
    return f"₹{int(v.quantize(D(1), rounding=ROUND_HALF_UP)):,}"


def draft(row: dict[str, Any], shop: str, lang: str) -> str:
    """A polite message, firmer as the dues get older. For a person to read and send."""
    name, amt, days = row["name"].split()[0], _inr(row["owed"]), row["oldest_days"]
    tone = "gentle" if days <= 30 else "firm" if days <= 60 else "final"
    t = {
        "en": {
            "gentle": f"Hello {name}, a small reminder from {shop}: {amt} is pending on your account. Please pay when convenient. Thank you!",
            "firm": f"Hello {name}, {amt} has been pending at {shop} for over {days // 30} month(s). Please clear it this week, or tell us when you can. Thank you.",
            "final": f"Hello {name}, {amt} at {shop} has been due for {days} days. We cannot give more credit until it is cleared. Please pay or speak to us.",
        },
        "hinglish": {
            "gentle": f"Namaste {name} ji, {shop} se yaad dilana tha: aapke khate mein {amt} baaki hai. Jab suvidha ho jama kar dijiye. Dhanyavaad!",
            "firm": f"Namaste {name} ji, {shop} mein {amt} {days // 30} mahine se zyada se baaki hai. Kripya is hafte jama kar dein, ya bata dein kab tak ho payega. Dhanyavaad.",
            "final": f"Namaste {name} ji, {shop} ka {amt} {days} din se baaki hai. Jab tak yeh jama nahi hota, hum aur udhaar nahi de payenge. Kripya jama karein ya baat kar lein.",
        },
        "hi": {
            "gentle": f"नमस्ते {name} जी, {shop} की ओर से याद दिलाना था: आपके खाते में {amt} बाकी है। सुविधा हो तब जमा कर दीजिए। धन्यवाद!",
            "firm": f"नमस्ते {name} जी, {shop} में {amt} {days // 30} महीने से ज्यादा से बाकी है। कृपया इस हफ्ते जमा कर दें या बता दें कब तक हो पाएगा। धन्यवाद।",
            "final": f"नमस्ते {name} जी, {shop} का {amt} {days} दिन से बाकी है। जब तक यह जमा नहीं होता, हम और उधार नहीं दे पाएंगे। कृपया जमा करें या बात कर लें।",
        },
    }
    return t.get(lang, t["en"])[tone]


def reminders(
    db: Session, ws: uuid.UUID, shop: str, today: date, lang: str, limit: int = 15
) -> list[dict[str, Any]]:
    out = []
    for r in parties(db, ws, today)[:limit]:
        if r["oldest_days"] < 7:
            continue  # too fresh to chase
        msg = draft(r, shop, lang)
        out.append(
            {"key": r["key"], "name": r["name"], "owed": r["owed"], "oldest_days": r["oldest_days"],
             "behaviour": r["behaviour"], "message": msg, "has_phone": bool(r["phone"]),
             "whatsapp": f"https://wa.me/{r['phone']}?text={quote(msg)}" if r["phone"] else None}
        )  # fmt: skip
    return out
