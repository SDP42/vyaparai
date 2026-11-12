"""The small things a shop does every day, made quick: write an expense, close the galla, watch what is about to
expire, send suppliers an order list, and say an udhaar or expense in one sentence.

Everything here is a record or a calculation for a person to check. Nothing is sent, paid or ordered: the order
list is text for the owner to share, and a spoken entry is shown back before it is saved.
"""

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.alert import Alert
from app.models.bill import PurchaseBill, PurchaseBillLine
from app.models.commerce import Product
from app.models.credit import CreditEntry
from app.models.daily import DayClose, Expense, ExpiryItem
from app.models.workspace import Workspace
from app.services import credit, inventory
from app.services.analytics import queries as q
from app.services.analytics import service as analytics
from app.services.assistant import numbers

D = Decimal
CENT = D("0.01")
CATEGORIES = {
    "rent": ("Rent", "Kiraya", "किराया"),
    "electricity": ("Electricity", "Bijli", "बिजली"),
    "salary": ("Salary", "Tankhwah", "तनख्वाह"),
    "transport": ("Transport", "Bhada", "भाड़ा"),
    "tea": ("Tea and snacks", "Chai-nashta", "चाय-नाश्ता"),
    "repairs": ("Repairs", "Marammat", "मरम्मत"),
    "supplies": ("Shop supplies", "Dukaan ka saaman", "दुकान का सामान"),
    "other": ("Other", "Aur", "अन्य"),
}
PAID_BY = {"cash", "upi", "card", "bank"}


def _money(v: Any) -> Decimal:
    try:
        d = D(str(v)).quantize(CENT)
    except Exception as exc:
        raise AppError("That is not an amount") from exc
    if d < 0 or d > D("10000000"):
        raise AppError("Amounts must be between 0 and 1 crore")
    return d


# ------------------------------------------------------------------ expenses


def add_expense(
    db: Session,
    ws: uuid.UUID,
    user: uuid.UUID | None,
    *,
    spent_on: date,
    category: str,
    amount: Any,
    paid_by: str = "cash",
    note: str | None = None,
) -> Expense:
    if category not in CATEGORIES:
        raise AppError("Unknown expense category")
    if paid_by not in PAID_BY:
        raise AppError("Paid by must be cash, upi, card or bank")
    amt = _money(amount)
    if amt <= 0:
        raise AppError("Amount must be more than zero")
    e = Expense(
        workspace_id=ws,
        spent_on=spent_on,
        category=category,
        amount=amt,
        paid_by=paid_by,
        note=(note or "").strip()[:200] or None,
        created_by_id=user,
    )
    db.add(e)
    db.commit()
    return e


def expenses(db: Session, ws: uuid.UUID, start: date, end: date) -> dict[str, Any]:
    rows = db.scalars(
        select(Expense)
        .where(Expense.workspace_id == ws, Expense.spent_on >= start, Expense.spent_on <= end)
        .order_by(Expense.spent_on.desc(), Expense.created_at.desc())
    ).all()
    by_cat: dict[str, Decimal] = {}
    for r in rows:
        by_cat[r.category] = by_cat.get(r.category, D(0)) + r.amount
    return {
        "from": start.isoformat(), "to": end.isoformat(),
        "total": sum((r.amount for r in rows), D(0)),
        "by_category": [{"category": k, "amount": v} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])],
        "items": [{"id": str(r.id), "spent_on": r.spent_on.isoformat(), "category": r.category, "amount": r.amount, "paid_by": r.paid_by, "note": r.note} for r in rows],
    }  # fmt: skip


def delete_expense(db: Session, ws: uuid.UUID, expense_id: uuid.UUID) -> None:
    e = db.get(Expense, expense_id)
    if e is None or e.workspace_id != ws:
        raise NotFoundError("Expense not found")
    db.delete(e)
    db.commit()


# ------------------------------------------------------------------ day close (galla tally)


def _file_sales(db: Session, ws: Workspace, day: date) -> Decimal | None:
    """Net sales for the day from the imported sales file, if that day is in it."""
    f = analytics.resolve_filters(db, ws.id, day, day)
    agg = q.daily(db, ws.id, f).get(day)
    return None if agg is None else D(str(agg.net)).quantize(CENT)


def _cash_expenses(db: Session, ws: uuid.UUID, day: date) -> Decimal:
    v = db.scalar(
        select(func.sum(Expense.amount)).where(
            Expense.workspace_id == ws, Expense.spent_on == day, Expense.paid_by == "cash"
        )
    )
    return D(str(v or 0)).quantize(CENT)


def _udhaar(db: Session, ws: uuid.UUID, day: date) -> tuple[Decimal, Decimal]:
    """(given on credit that day, received back that day)."""
    out = {"credit": D(0), "payment": D(0)}
    for kind, total in db.execute(
        select(CreditEntry.kind, func.sum(CreditEntry.amount))
        .where(CreditEntry.workspace_id == ws, CreditEntry.entry_date == day)
        .group_by(CreditEntry.kind)
    ).all():
        out[kind] = D(str(total or 0))
    return out["credit"].quantize(CENT), out["payment"].quantize(CENT)


def _gross_margin_pct(db: Session, ws: Workspace, day: date) -> Decimal | None:
    """The last 30 days' gross margin, for a rough day profit; None without cost data."""
    try:
        f = analytics.resolve_filters(db, ws.id, day - timedelta(days=29), day)
        totals, _ = q.build_totals(db, ws.id, f)
    except AppError:
        return None
    covered = getattr(totals, "covered_net", None)
    cogs = getattr(totals, "cogs", None)
    if not covered or cogs is None or D(str(covered)) <= 0:
        return None
    return ((D(str(covered)) - D(str(cogs))) / D(str(covered))).quantize(D("0.0001"))


def close_view(db: Session, ws: Workspace, day: date) -> dict[str, Any]:
    """Everything needed to close a day; includes the saved close if there is one."""
    saved = db.scalars(
        select(DayClose).where(DayClose.workspace_id == ws.id, DayClose.day == day)
    ).first()
    prev = db.scalars(
        select(DayClose)
        .where(DayClose.workspace_id == ws.id, DayClose.day < day)
        .order_by(DayClose.day.desc())
    ).first()
    given, received = _udhaar(db, ws.id, day)
    out: dict[str, Any] = {
        "day": day.isoformat(),
        "file_sales": _file_sales(db, ws, day),
        "suggested_opening": prev.counted_cash - prev.taken_out
        if prev and prev.counted_cash >= prev.taken_out
        else (prev.counted_cash if prev else None),
        "cash_expenses": _cash_expenses(db, ws.id, day),
        "udhaar_given": given,
        "udhaar_received": received,
        "saved": None,
    }
    if saved is not None:
        out["saved"] = _close_result(db, ws, saved, out)
    return out


def _close_result(db: Session, ws: Workspace, c: DayClose, ctx: dict[str, Any]) -> dict[str, Any]:
    typed = c.cash_sales + c.upi_sales + c.card_sales
    expected = (
        c.opening_cash + c.cash_sales + ctx["udhaar_received"] - ctx["cash_expenses"] - c.taken_out
    )
    diff = (c.counted_cash - expected).quantize(CENT)
    margin = _gross_margin_pct(db, ws, c.day)
    all_exp = (
        db.scalar(
            select(func.sum(Expense.amount)).where(
                Expense.workspace_id == ws.id, Expense.spent_on == c.day
            )
        )
        or 0
    )
    profit = None if margin is None else (typed * margin - D(str(all_exp))).quantize(CENT)
    file_sales = ctx["file_sales"]
    return {
        "opening_cash": c.opening_cash, "cash_sales": c.cash_sales, "upi_sales": c.upi_sales, "card_sales": c.card_sales,
        "taken_out": c.taken_out, "counted_cash": c.counted_cash, "note": c.note,
        "typed_sales": typed, "expected_cash": expected.quantize(CENT), "difference": diff,
        "status": "matches" if abs(diff) < 1 else ("extra" if diff > 0 else "short"),
        "file_gap": None if file_sales is None else (typed - file_sales).quantize(CENT),
        "rough_profit": profit, "margin_used_pct": None if margin is None else (margin * 100).quantize(D("0.1")),
    }  # fmt: skip


def save_close(
    db: Session,
    ws: Workspace,
    user: uuid.UUID | None,
    *,
    day: date,
    opening_cash: Any,
    cash_sales: Any,
    upi_sales: Any,
    card_sales: Any,
    taken_out: Any,
    counted_cash: Any,
    note: str | None,
) -> dict[str, Any]:
    if day > datetime.now(UTC).date() + timedelta(days=1):
        raise AppError("You cannot close a day in the future")
    c = db.scalars(
        select(DayClose).where(DayClose.workspace_id == ws.id, DayClose.day == day)
    ).first()
    if c is None:
        c = DayClose(workspace_id=ws.id, day=day, counted_cash=D(0))
        db.add(c)
    c.opening_cash, c.cash_sales, c.upi_sales, c.card_sales = (
        _money(opening_cash),
        _money(cash_sales),
        _money(upi_sales),
        _money(card_sales),
    )
    c.taken_out, c.counted_cash = _money(taken_out), _money(counted_cash)
    c.note = (note or "").strip()[:200] or None
    c.closed_by_id = user
    db.commit()
    return close_view(db, ws, day)


def close_history(db: Session, ws: Workspace, days: int = 30) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DayClose)
        .where(DayClose.workspace_id == ws.id)
        .order_by(DayClose.day.desc())
        .limit(days)
    ).all()
    out = []
    for c in rows:
        _, received = _udhaar(db, ws.id, c.day)
        ctx = {
            "udhaar_received": received,
            "cash_expenses": _cash_expenses(db, ws.id, c.day),
            "file_sales": None,
        }
        r = _close_result(db, ws, c, ctx)
        out.append(
            {
                "day": c.day.isoformat(),
                "typed_sales": r["typed_sales"],
                "difference": r["difference"],
                "status": r["status"],
            }
        )
    return out


# ------------------------------------------------------------------ expiry watch


def add_expiry(
    db: Session,
    ws: uuid.UUID,
    *,
    name: str,
    expires_on: date,
    quantity: Any = None,
    batch: str | None = None,
    note: str | None = None,
) -> ExpiryItem:
    name = (name or "").strip()
    if not name:
        raise AppError("Give the item's name")
    pid = db.scalar(
        select(Product.id).where(
            Product.workspace_id == ws, func.lower(Product.name) == name.lower()
        )
    )
    item = ExpiryItem(
        workspace_id=ws, name=name[:160], product_id=pid, expires_on=expires_on,
        quantity=None if quantity in (None, "") else D(str(quantity)), batch=(batch or "").strip()[:40] or None,
        note=(note or "").strip()[:200] or None,
    )  # fmt: skip
    db.add(item)
    db.commit()
    return item


def expiry_list(db: Session, ws: uuid.UUID, today: date) -> dict[str, Any]:
    rows = db.scalars(
        select(ExpiryItem)
        .where(ExpiryItem.workspace_id == ws, ExpiryItem.cleared_at.is_(None))
        .order_by(ExpiryItem.expires_on)
    ).all()

    def bucket(d: date) -> str:
        left = (d - today).days
        return (
            "expired"
            if left < 0
            else "this_week"
            if left <= 7
            else "this_month"
            if left <= 30
            else "later"
        )

    items = [
        {"id": str(r.id), "name": r.name, "batch": r.batch, "expires_on": r.expires_on.isoformat(), "days_left": (r.expires_on - today).days,
         "bucket": bucket(r.expires_on), "quantity": r.quantity, "note": r.note}
        for r in rows
    ]  # fmt: skip
    counts = {
        b: sum(1 for i in items if i["bucket"] == b)
        for b in ("expired", "this_week", "this_month", "later")
    }
    return {"as_of": today.isoformat(), "counts": counts, "items": items}


def clear_expiry(db: Session, ws: uuid.UUID, item_id: uuid.UUID, how: str) -> None:
    if how not in {"sold", "returned", "discounted", "thrown"}:
        raise AppError("Say how it went: sold, returned, discounted or thrown")
    item = db.get(ExpiryItem, item_id)
    if item is None or item.workspace_id != ws:
        raise NotFoundError("Item not found")
    item.cleared_at = datetime.now(UTC)
    item.cleared_how = how
    db.commit()


# ------------------------------------------------------------------ supplier order lists


def order_lists(db: Session, ws: Workspace, lang: str = "hinglish") -> dict[str, Any]:
    """What to order, grouped by the supplier who last billed each product, as text ready to share."""
    ov = inventory.overview(db, ws)
    need = [i for i in ov["items"] if D(str(i.get("order_qty") or 0)) > 0]
    supplier_of: dict[uuid.UUID, str] = {}
    for pid, supplier in db.execute(
        select(PurchaseBillLine.product_id, PurchaseBill.supplier)
        .join(PurchaseBill, PurchaseBill.id == PurchaseBillLine.bill_id)
        .where(
            PurchaseBill.workspace_id == ws.id,
            PurchaseBill.status == "confirmed",
            PurchaseBillLine.product_id.is_not(None),
        )
        .order_by(PurchaseBill.bill_date.asc().nulls_first(), PurchaseBill.created_at.asc())
    ).all():
        if pid is not None and supplier:
            supplier_of[pid] = supplier  # ascending, so the latest bill wins
    pid_by_sku = dict(
        db.execute(select(Product.sku, Product.id).where(Product.workspace_id == ws.id)).all()
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    for i in need:
        pid = pid_by_sku.get(i["sku"])
        sup = (supplier_of.get(pid, "") if pid is not None else "") or ""
        groups.setdefault(sup, []).append(
            {"sku": i["sku"], "name": i["name"], "qty": i["order_qty"], "status": i["status"]}
        )
    hello = {
        "en": "Hello {s}, please send:",
        "hinglish": "Namaste {s}, kripya yeh bhejiye:",
        "hi": "नमस्ते {s}, कृपया यह भेजिए:",
    }
    thanks = {"en": "Thank you, {shop}", "hinglish": "Dhanyavaad, {shop}", "hi": "धन्यवाद, {shop}"}
    out = []
    for sup, items in sorted(groups.items(), key=lambda g: (g[0] == "", g[0].lower())):
        lines = [hello.get(lang, hello["en"]).format(s=sup or "ji").replace("  ", " ")]
        lines += [f"- {it['name']} × {_qty(it['qty'])}" for it in items]
        lines.append(thanks.get(lang, thanks["en"]).format(shop=ws.name))
        text = "\n".join(lines)
        out.append(
            {
                "supplier": sup or None,
                "items": items,
                "text": text,
                "share_url": "https://wa.me/?text=" + quote(text),
            }
        )
    return {"as_of": ov.get("as_of"), "groups": out, "has_forecast": ov.get("has_forecast", False)}


def _qty(v: Any) -> str:
    d = D(str(v))
    return str(int(d)) if d == d.to_integral_value() else str(d.normalize())


# ------------------------------------------------------------------ one-sentence entries


_CREDIT = re.compile(
    r"(?:^|\s)(?:ko|को)(?=\s).*?(?:udhaar|udhar|उधार|baaki|बाकी|diya|दिया|de diya)", re.I
)
_PAID = re.compile(
    r"(?:^|\s)(?:ne|ने)(?=\s).*?(?:diye|diya|दिए|दिया|jama|जमा|wapas|वापस|lautaye|chukaye|चुकाए)",
    re.I,
)
_EXPENSE = re.compile(r"(?:kharcha|kharch|kharche|खर्च|खर्चा|expense|spent)", re.I)
_CAT_WORDS = {
    "rent": ("kiraya", "किराया", "rent"), "electricity": ("bijli", "बिजली", "light", "electricity"),
    "salary": ("tankhwah", "tankha", "salary", "पगार", "तनख्वाह", "pagar"), "transport": ("bhada", "भाड़ा", "auto", "tempo", "transport", "rickshaw"),
    "tea": ("chai", "चाय", "nashta", "नाश्ता", "tea"), "repairs": ("marammat", "repair", "मरम्मत"),
    "supplies": ("thaili", "bag", "polythene", "packing", "थैली"),
}  # fmt: skip


def parse_entry(text: str) -> dict[str, Any]:
    """Read "Ramesh ko 200 udhaar", "Ramesh ne 500 diye" or "chai 60 kharcha" into an entry to confirm."""
    t = " ".join((text or "").split())
    if not t:
        raise AppError("Say or type one entry")
    amount = numbers.first(t)
    if not amount:
        return {"understood": False, "reason": "no_amount", "text": t}
    lower = t.lower()
    if _EXPENSE.search(lower):
        cat = next(
            (c for c, words in _CAT_WORDS.items() if any(w in lower for w in words)), "other"
        )
        return {
            "understood": True,
            "kind": "expense",
            "category": cat,
            "amount": D(amount),
            "note": t,
            "text": t,
        }
    for kind, pat, marker in (
        ("credit", _CREDIT, r"(?:^|\s)(?:ko|को)(?=\s)"),
        ("payment", _PAID, r"(?:^|\s)(?:ne|ने)(?=\s)"),
    ):
        if pat.search(lower):
            name = re.split(marker, t, maxsplit=1, flags=re.I)[0].strip(" ,.-")
            if not name or numbers.first(name):
                return {"understood": False, "reason": "no_name", "text": t}
            return {
                "understood": True,
                "kind": kind,
                "party": name[:120],
                "amount": D(amount),
                "text": t,
            }
    return {"understood": False, "reason": "no_kind", "text": t}


def save_entry(
    db: Session, ws: uuid.UUID, user: uuid.UUID | None, entry: dict[str, Any], day: date
) -> dict[str, Any]:
    kind = entry.get("kind")
    if kind == "expense":
        e = add_expense(
            db,
            ws,
            user,
            spent_on=day,
            category=entry.get("category") or "other",
            amount=entry["amount"],
            note=entry.get("note"),
        )
        return {"saved": "expense", "id": str(e.id)}
    if kind in {"credit", "payment"}:
        c = credit.add_entry(
            db,
            ws,
            party=str(entry.get("party") or ""),
            entry_date=day,
            kind=kind,
            amount=_money(entry["amount"]),
            note="said on " + day.isoformat(),
            source="quick",
        )
        db.commit()
        return {"saved": kind, "id": str(c.id) if c else None, "duplicate": c is None}
    raise AppError("Nothing to save")


# ------------------------------------------------------------------ today


def today(db: Session, ws: Workspace, day: date, *, can: set[str]) -> dict[str, Any]:
    """The first screen of the day: a few numbers and a short list of things to do, each from an existing feature."""
    _, last = q.workspace_bounds(db, ws.id)
    out: dict[str, Any] = {"day": day.isoformat(), "shop": ws.name}
    if last is not None:
        f = analytics.resolve_filters(db, ws.id, last - timedelta(days=7), last)
        series = q.daily(db, ws.id, f)
        now = series.get(last)
        week_ago = series.get(last - timedelta(days=7))
        net = None if now is None else D(str(now.net)).quantize(CENT)
        prev = None if week_ago is None else D(str(week_ago.net)).quantize(CENT)
        out["sales"] = {
            "day": last.isoformat(), "net": net, "bills": None if now is None else now.orders,
            "vs_same_day_last_week_pct": None if not prev or net is None else ((net - prev) / prev * 100).quantize(D("0.1")),
        }  # fmt: skip
    else:
        out["sales"] = None
    if "credit" in can:
        s = credit.summary(db, ws.id, day)
        out["udhaar"] = (
            {
                "outstanding": s["outstanding"],
                "overdue": s["overdue"],
                "call_first": s["biggest"][:3],
            }
            if s["has_data"]
            else None
        )
    if "stock" in can:
        ov = inventory.overview(db, ws)
        need = [i for i in ov["items"] if D(str(i.get("order_qty") or 0)) > 0]
        out["order"] = {
            "count": len(need),
            "top": [{"name": i["name"], "qty": i["order_qty"]} for i in need[:4]],
        }
        ex = expiry_list(db, ws.id, day)
        out["expiry"] = {
            "expired": ex["counts"]["expired"],
            "this_week": ex["counts"]["this_week"],
            "soonest": ex["items"][:3],
        }
    if "cash" in can:
        yesterday = day - timedelta(days=1)
        closed = db.scalar(
            select(func.count())
            .select_from(DayClose)
            .where(DayClose.workspace_id == ws.id, DayClose.day == yesterday)
        )
        month = expenses(db, ws.id, day.replace(day=1), day)
        out["cash"] = {
            "yesterday_closed": bool(closed),
            "yesterday": yesterday.isoformat(),
            "month_expenses": month["total"],
        }
    out["alerts"] = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.workspace_id == ws.id, Alert.status == "open", Alert.severity == "high")
        )
        or 0
    )
    return out
