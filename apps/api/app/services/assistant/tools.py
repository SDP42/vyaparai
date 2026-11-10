"""Typed, read-only tools. Each returns numbers computed by the existing services, never by text.

A tool result carries the facts to quote, an optional table, and a link to the page that shows
the same thing, so every answer can be checked.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commerce import Product
from app.models.workspace import Workspace
from app.services import alerts as alert_service
from app.services import credit, events_insight, inventory
from app.services.analytics import intelligence
from app.services.analytics import queries as q
from app.services.analytics import service as analytics
from app.services.assistant.nlu import Period
from app.services.bills import service as bills
from app.services.forecasting import service as forecasting
from app.services.reviews import service as reviews

D = Decimal


def inr(x: Decimal | float | str | None) -> str:
    """₹ with Indian digit grouping (12,34,567)."""
    if x is None:
        return "–"
    v = int(Decimal(str(x)).quantize(D(1), rounding=ROUND_HALF_UP))
    sign, s = ("-" if v < 0 else ""), str(abs(v))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}₹{s}"


def pct(x: Any, signed: bool = True) -> str:
    if x is None:
        return "–"
    v = float(x)
    return f"{v:+.1f}%" if signed else f"{v:.1f}%"


@dataclass(slots=True)
class Result:
    facts: dict[str, Any] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    link: str = "/app"
    note: str | None = None  # something the user must know (fallback used, no data)
    empty: bool = False
    period: tuple[date, date] | None = None
    extra: list[str] = field(default_factory=list)  # one-line evidence sentences


def _filters(db: Session, ws: uuid.UUID, period: Period | None) -> tuple[Any, str | None]:
    """Filters for the period; if it holds no sales, fall back to the latest 30 days and say so."""
    first, last = q.workspace_bounds(db, ws)
    if first is None or last is None:
        return None, "No sales have been imported yet."
    note = None
    if period is None:
        f = analytics.resolve_filters(db, ws, None, None)
    else:
        a, b = max(period.start, first), min(period.end, last)
        if a > b:
            f = analytics.resolve_filters(db, ws, None, None)
            note = (
                f"There are no sales in {period.label}. Your latest sales are from {last:%d %b %Y}, "
                "so this shows the most recent 30 days instead."
            )
        else:
            f = analytics.resolve_filters(db, ws, a, b)
            if (a, b) != (period.start, period.end):
                note = f"Your sales run from {first:%d %b %Y} to {last:%d %b %Y}; this covers {a:%d %b} to {b:%d %b}."
    return f, note


def sales(db: Session, workspace: Workspace, period: Period | None) -> Result:
    f, note = _filters(db, workspace.id, period)
    if f is None:
        return Result(empty=True, note=note, link="/app/data")
    ov = analytics.overview(db, workspace, f, "previous_period")
    k = {x["key"]: x for x in ov["headline"] + ov["secondary"]}
    return Result(
        facts={
            "net_sales": k["net_sales"]["value"], "net_change_pct": k["net_sales"]["change_pct"],
            "orders": k["orders"]["value"], "aov": k["aov"]["value"],
            "gross_profit": k["gross_profit"]["value"],
            "start": f.date_from, "end": f.date_to,
        },
        link="/app", note=note, period=(f.date_from, f.date_to),
        extra=[f"Net sales {inr(k['net_sales']['value'])}, {int(k['orders']['value'] or 0)} orders, "
               f"average order {inr(k['aov']['value'])}"],
    )  # fmt: skip


def why(db: Session, workspace: Workspace, period: Period | None) -> Result:
    f, note = _filters(db, workspace.id, period)
    if f is None:
        return Result(empty=True, note=note, link="/app/data")
    d = analytics.drivers(db, workspace, f, "previous_period")
    effects = sorted(d["effects"], key=lambda e: -abs(Decimal(e["amount"])))
    top = [e for e in effects if Decimal(e["amount"]) != 0][:3]
    losers = d["biggest_decliners"][:3]
    gainers = d["biggest_gainers"][:3]
    return Result(
        facts={
            "now": d["net_sales_current"], "before": d["net_sales_previous"],
            "change": d["net_change"], "effects": top, "decliners": losers, "gainers": gainers,
            "start": f.date_from, "end": f.date_to,
        },
        rows=[{"name": x["name"], "change": inr(x["delta"])} for x in (losers or gainers)],
        link="/app/sales", note=note, period=(f.date_from, f.date_to),
    )  # fmt: skip


def products(
    db: Session, workspace: Workspace, period: Period | None, n: int, slow: bool
) -> Result:
    f, note = _filters(db, workspace.id, period)
    if f is None:
        return Result(empty=True, note=note, link="/app/data")
    items = intelligence.products_overview(db, workspace, f, "previous_period")["items"]
    items = sorted(items, key=lambda x: Decimal(x["net"]), reverse=not slow)[:n]
    return Result(
        facts={"slow": slow, "start": f.date_from, "end": f.date_to},
        rows=[{"name": x["name"], "net": inr(x["net"]), "units": str(int(Decimal(x["units"]))),
               "margin": pct(x["margin_pct"], False) if x.get("margin_pct") else "–"} for x in items],
        link="/app/products", note=note, period=(f.date_from, f.date_to),
    )  # fmt: skip


def customers(db: Session, workspace: Workspace) -> Result:
    s = intelligence.customers_summary(db, workspace, None, 365, 30, 30, 45)
    return Result(
        facts={"customers": s["customers"], "repeat_rate": s["repeat_rate"],
               "lapsed_regulars": s["lapsed_regulars"], "as_of": s["params"]["as_of"],
               "status": s["status_counts"]},
        link="/app/customers",
    )  # fmt: skip


def stock(db: Session, workspace: Workspace) -> Result:
    ov = inventory.overview(db, workspace)
    s = ov["summary"]
    if s["tracked"] == 0:
        return Result(empty=True, link="/app/inventory", note="No stock counts yet.")
    need = [i for i in ov["items"] if i.get("status") in {"urgent", "reorder"}]
    need.sort(key=lambda i: (i["status"] != "urgent", i.get("cover_days") or 999))
    return Result(
        facts={"urgent": s["urgent"], "reorder": s["reorder"], "order_cost": s["order_cost"]},
        rows=[{"name": i["name"], "cover_days": i.get("cover_days"), "order": i.get("order_qty")} for i in need[:6]],
        link="/app/inventory",
    )  # fmt: skip


def dead_stock(db: Session, workspace: Workspace) -> Result:
    ov = inventory.overview(db, workspace)
    s = ov["summary"]
    if s["tracked"] == 0:
        return Result(empty=True, link="/app/inventory", note="No stock counts yet.")
    dead = [i for i in ov["items"] if i.get("status") == "dead"]
    return Result(
        facts={"dead": s["dead"], "dead_cash": s["dead_cash"], "excess_cash": s["excess_cash"]},
        rows=[{"name": i["name"]} for i in dead[:6]], link="/app/inventory",
    )  # fmt: skip


def forecast(db: Session, workspace: Workspace) -> Result:
    run = forecasting.latest_run(db, workspace.id)
    if run is None:
        return Result(empty=True, link="/app/forecasts", note="No forecast has been built yet.")
    o = forecasting.overview(db, workspace, run)
    k = o["kpis"]
    return Result(
        facts={"units_next": k["units_next"], "low": k["units_next_low"], "high": k["units_next_high"],
               "net_next": k["net_next"], "change_pct": k["units_change_pct"],
               "horizon": run.horizon, "as_of": run.as_of.isoformat(), "stale": o["stale"],
               "wape": o["accuracy"]["wape"]},
        rows=[{"name": r["name"], "change": pct(r["change_pct"])} for r in o["risers"][:3]],
        link="/app/forecasts",
    )  # fmt: skip


def alerts(db: Session, workspace: Workspace) -> Result:
    items = alert_service.listing(db, workspace.id, "open")
    return Result(
        facts={"count": len(items),
               "high": sum(a.severity == "high" for a in items), "medium": sum(a.severity == "medium" for a in items)},
        rows=[{"title": a.title, "severity": a.severity} for a in items[:5]], link="/app/alerts",
    )  # fmt: skip


def margin(db: Session, workspace: Workspace, period: Period | None) -> Result:
    f, note = _filters(db, workspace.id, period)
    if f is None:
        return Result(empty=True, note=note, link="/app/data")
    ov = intelligence.products_overview(db, workspace, f, "previous_period")
    leaks = alert_service.rule_margin(db, workspace.id, f.date_to)[0]
    return Result(
        facts={"margin_pct": ov["overall_margin_pct"], "leaks": len(leaks), "start": f.date_from, "end": f.date_to},
        rows=[{"title": x["title"]} for x in leaks[:4]], link="/app/costs", note=note, period=(f.date_from, f.date_to),
    )  # fmt: skip


def supplier(db: Session, workspace: Workspace) -> Result:
    moves = bills.price_moves(db, workspace.id)
    up = [m for m in moves if m["change_pct"] > 0]
    return Result(
        facts={"up": len(up), "moves": len(moves)},
        rows=[{"name": m["name"], "change": pct(m["change_pct"]), "from": inr(m["previous"]), "to": inr(m["latest"])} for m in up[:5]],
        link="/app/bills",
    )  # fmt: skip


def review_summary(db: Session, workspace: Workspace) -> Result:
    s = reviews.summary(db, workspace.id, 90)
    if s["total"] == 0:
        return Result(empty=True, link="/app/reviews", note="No reviews have been added yet.")
    worst = [t for t in s["themes"] if t["mentions"] >= 3][:3]
    return Result(
        facts={"total": s["in_window"], "positive": s["labels"]["positive"], "negative": s["labels"]["negative"]},
        rows=[{"theme": t["label"], "negative_pct": t["negative_pct"], "mentions": t["mentions"]} for t in worst],
        link="/app/reviews",
    )  # fmt: skip


def festivals(db: Session, workspace: Workspace) -> Result:
    ev = events_insight.upcoming(db, workspace, days=60, include_cricket=False, today=date.today())
    return Result(
        facts={"count": len(ev)},
        rows=[{"name": e["event"].name, "start": e["event"].start.isoformat(),
               "products": ", ".join(p["name"] for p in e.get("products", [])[:3])} for e in ev[:3]],
        link="/app/festivals",
    )  # fmt: skip


def udhaar(db: Session, workspace: Workspace) -> Result:
    s = credit.summary(db, workspace.id, date.today())
    if not s["has_data"]:
        return Result(empty=True, link="/app/udhaar", note="No udhaar ledger yet.")
    return Result(
        facts={"outstanding": s["outstanding"], "parties": s["parties_owing"], "overdue": s["overdue"],
               "overdue_pct": s["overdue_pct"], "stalled": s["stalled"]},
        rows=[{"name": b["name"], "owed": inr(b["owed"]), "days": f"{b['oldest_days']} days old"} for b in s["biggest"][:4]],
        link="/app/udhaar",
    )  # fmt: skip


def find_product(db: Session, ws: uuid.UUID, text: str) -> Product | None:
    """A product named in the question (best fuzzy match above a safe threshold)."""
    from app.services.bills.service import match_score

    best, hit = 0.0, None
    for p in db.scalars(select(Product).where(Product.workspace_id == ws)):
        s = max(match_score(text, p.name), 1.0 if p.sku.lower() in text.lower().split() else 0.0)
        if s > best:
            best, hit = s, p
    return hit if best >= 0.5 else None


# ------------------------------------------------------------------ product-specific tools

_NAME_STOP = {
    "the",
    "of",
    "and",
    "pack",
    "for",
    "with",
    "in",
    "a",
    "kg",
    "g",
    "gm",
    "ml",
    "l",
    "ltr",
    "litre",
}


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 4 and t.endswith("s") else t


def find_product_in_text(db: Session, ws: uuid.UUID, text: str) -> Product | None:
    """A product named in the question: its distinctive words must all (or mostly) appear."""
    import re

    qt = {_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower())}
    best: tuple[float, int, Product] | None = None
    for p in db.scalars(select(Product).where(Product.workspace_id == ws)):
        if p.sku.lower() in text.lower().split():
            return p
        words = [
            _stem(t)
            for t in re.findall(r"[a-z0-9]+", p.name.lower())
            if t not in _NAME_STOP and not t.isdigit()
        ]
        if not words:
            continue
        hit = [w for w in words if w in qt]
        frac = len(hit) / len(words)
        if not hit or max(len(w) for w in hit) < 4:
            continue
        need = 1.0 if len(words) <= 2 else 0.6
        if frac >= need and (best is None or (frac, len(hit)) > best[:2]):
            best = (frac, len(hit), p)
    return best[2] if best else None


def product_sales(db: Session, workspace: Workspace, period: Period | None, p: Product) -> Result:
    import dataclasses

    f, note = _filters(db, workspace.id, period)
    if f is None:
        return Result(empty=True, note=note, link="/app/data")
    f = dataclasses.replace(f, skus=(p.sku,))
    ov = analytics.overview(db, workspace, f, "previous_period")
    k = {x["key"]: x for x in ov["headline"] + ov["secondary"]}
    return Result(
        facts={"name": p.name, "net_sales": k["net_sales"]["value"], "change_pct": k["net_sales"]["change_pct"],
               "units": k["units"]["value"], "margin": k["gross_margin"]["value"],
               "start": f.date_from, "end": f.date_to},
        link="/app/products", note=note, period=(f.date_from, f.date_to),
    )  # fmt: skip


def product_stock(db: Session, workspace: Workspace, p: Product) -> Result:
    ov = inventory.overview(db, workspace)
    item = next((i for i in ov["items"] if i["sku"] == p.sku), None)
    if item is None:
        return Result(empty=True, link="/app/inventory", note="No stock count for this product.")
    return Result(
        facts={"name": p.name, "cover_days": item["cover_days"], "status": item["status"],
               "order_qty": item["order_qty"], "lead_time": item["lead_time_days"], "reason": item["reason"]},
        link="/app/inventory",
    )  # fmt: skip


def product_forecast(db: Session, workspace: Workspace, p: Product) -> Result:
    run = forecasting.latest_run(db, workspace.id)
    if run is None:
        return Result(empty=True, link="/app/forecasts", note="No forecast has been built yet.")
    try:
        d = forecasting.product_detail(db, run, p.sku)
    except Exception:
        return Result(empty=True, link="/app/forecasts", note="No forecast for this product.")
    return Result(
        facts={"name": p.name, "units_next": d["units_next"], "low": d["units_next_low"], "high": d["units_next_high"],
               "units_last": d["units_last"], "change_pct": d["change_pct"], "confidence": d["confidence"],
               "wape": d["backtest_wape"], "horizon": run.horizon},
        link="/app/forecasts",
    )  # fmt: skip
