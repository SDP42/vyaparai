# ruff: noqa: E501
"""Alert rules over recent sales. Every rule is explicit, explainable and has a fixed threshold.

A day is compared with the *same weekday* over the previous eight weeks, using the median and the
median absolute deviation (MAD) so one odd day does not distort the baseline (docs/research/ALERTS.md).
``refresh`` recomputes the rules and keeps the alert list in step: new problems open, problems that
went away resolve, and ones an owner dismissed stay dismissed while they last.
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.commerce import Order, OrderItem, Product
from app.models.source import ImportSource
from app.models.workspace import Workspace
from app.services import costs, events_insight, inventory
from app.services.analytics import intelligence
from app.services.analytics import queries as q
from app.services.analytics.queries import LINE_NET, _lines
from app.services.analytics.types import ZERO, Filters, dec, metric_values
from app.services.bills import service as bill_service
from app.services.reviews import service as review_service

D = Decimal
SEVERITY_RANK = {"high": 0, "medium": 1, "info": 2}
RULE_PRIORITY = {
    r: i
    for i, r in enumerate(
        [
            "sales_drop",
            "margin_leak",
            "discount_creep",
            "week_drop",
            "product_stopped",
            "lapsed_regulars",
            "sales_spike",
            "no_costs",
            "data_stale",
        ]
    )
}

DROP_MEDIUM, DROP_HIGH = D(-30), D(-45)  # percent vs the usual same weekday
SPIKE = D(40)
MIN_Z = D("2.5")
MIN_BASELINE = D(200)  # rupees; below this a percentage swing means nothing
WEEK_MEDIUM, WEEK_HIGH = D(-15), D(-25)
DISCOUNT_MEDIUM, DISCOUNT_HIGH = D(3), D(5)  # points of discount rate
STOPPED_MIN_DAYS = 8  # selling days in the 28 days before the last week
LEAK_HIGH_AMOUNT = D(500)
LEAK_HIGH_POINTS = D(5)
LAPSED_MEDIUM = 10
LAPSED_INFO = 5
STALE_DAYS = 3


# ------------------------------------------------------------------ pure statistics


def median(xs: list[Decimal]) -> Decimal:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def mad(xs: list[Decimal], center: Decimal) -> Decimal:
    return median([abs(x - center) for x in xs])


def robust_change(actual: Decimal, history: list[Decimal]) -> dict[str, Decimal | None]:
    """Change against the median of ``history`` and a robust z-score (None when MAD is zero)."""
    base = median(history)
    sigma = D("1.4826") * mad(history, base)
    change = ((actual - base) / base * 100) if base else None
    z = (actual - base) / sigma if sigma > 0 else None
    return {"expected": base, "change_pct": change, "z": z}


def inr(x: Decimal | float) -> str:
    return f"₹{int(Decimal(str(x)).quantize(D(1), rounding=ROUND_HALF_UP)):,}"


# ------------------------------------------------------------------ rules


def _daily_net(db: Session, ws: uuid.UUID, start: date, end: date) -> dict[date, Decimal]:
    stmt = _lines(
        [Order.business_date, func.sum(LINE_NET)], ws, Filters(date_from=start, date_to=end)
    ).group_by(Order.business_date)
    out = {start + timedelta(days=i): ZERO for i in range((end - start).days + 1)}
    for day, net in db.execute(stmt).all():
        out[day] = dec(net)
    return out


def rule_sales(db: Session, ws: uuid.UUID, first: date, end: date) -> list[dict[str, Any]]:
    series = _daily_net(db, ws, end - timedelta(days=56), end)
    out: list[dict[str, Any]] = []

    hist = [
        series[end - timedelta(days=7 * k)]
        for k in range(1, 9)
        if end - timedelta(days=7 * k) >= first
    ]
    if len(hist) >= 4:
        actual = series[end]
        r = robust_change(actual, hist)
        base, change, z = r["expected"], r["change_pct"], r["z"]
        if base is not None and base >= MIN_BASELINE and change is not None:
            ev = {
                "actual": float(actual),
                "expected": float(base),
                "change_pct": float(change),
                "z": None if z is None else float(z),
                "weeks": len(hist),
            }
            weekday = f"{end:%A}"
            if change <= DROP_MEDIUM and (z is None or z <= -MIN_Z):
                out.append(
                    {
                        "key": f"sales_drop|{end}", "rule": "sales_drop",
                        "severity": "high" if change <= DROP_HIGH else "medium",
                        "title": f"Sales on {end:%a %d %b} were {abs(change):.0f}% below a usual {weekday}",
                        "detail": f"A usual {weekday} is about {inr(base)} (middle of the last {len(hist)}); this one was {inr(actual)}. Check for a closed shop, empty shelves or sales not yet imported.",
                        "evidence": ev, "link": "/app/sales",
                    }
                )  # fmt: skip
            elif change >= SPIKE and (z is None or z >= MIN_Z):
                out.append(
                    {
                        "key": f"sales_spike|{end}", "rule": "sales_spike", "severity": "info",
                        "title": f"Sales on {end:%a %d %b} were {change:.0f}% above a usual {weekday}",
                        "detail": f"A usual {weekday} is about {inr(base)}; this one was {inr(actual)}. Worth knowing why, so you can repeat it and stock for it.",
                        "evidence": ev, "link": "/app/sales",
                    }
                )  # fmt: skip

    if end - timedelta(days=34) >= first:
        cur = sum((series[end - timedelta(days=i)] for i in range(7)), ZERO)
        prior = [
            sum((series[end - timedelta(days=7 * w + i)] for i in range(7)), ZERO)
            for w in range(1, 5)
        ]
        mean = sum(prior, ZERO) / 4
        if mean >= MIN_BASELINE * 7:
            change = (cur - mean) / mean * 100
            if change <= WEEK_MEDIUM:
                out.append(
                    {
                        "key": f"week_drop|{end}", "rule": "week_drop",
                        "severity": "high" if change <= WEEK_HIGH else "medium",
                        "title": f"This week's sales are {abs(change):.0f}% below your recent weeks",
                        "detail": f"The last 7 days brought in {inr(cur)} against about {inr(mean)} in each of the 4 weeks before.",
                        "evidence": {"week": float(cur), "expected": float(mean), "change_pct": float(change)},
                        "link": "/app/sales",
                    }
                )  # fmt: skip
    return out


def rule_margin(
    db: Session, ws: uuid.UUID, end: date
) -> tuple[list[dict[str, Any]], Decimal | None]:
    ov = costs.overview(db, ws, end)
    out = []
    leaks = [i for i in ov["items"] if i["status"] == "margin_leak"]
    for i in leaks[:8]:
        fell = i["margin_prev_pct"] - i["margin_now_pct"]
        high = i["leak_amount"] >= LEAK_HIGH_AMOUNT or fell >= LEAK_HIGH_POINTS
        out.append(
            {
                "key": f"margin_leak|{i['sku']}", "rule": "margin_leak",
                "severity": "high" if high else "medium",
                "title": f"{i['name']}: cost up {i['cost_change_pct']}% but the price did not follow",
                "detail": f"Margin fell from {i['margin_prev_pct']}% to {i['margin_now_pct']}%, about {inr(i['leak_amount'])} lost in {ov['window_days']} days. A price of {inr(i['suggested_price'])} restores the old margin.",
                "evidence": {"cost_change_pct": float(i["cost_change_pct"]), "price_change_pct": float(i["price_change_pct"]), "margin_prev_pct": float(i["margin_prev_pct"]), "margin_now_pct": float(i["margin_now_pct"]), "leak_amount": float(i["leak_amount"]), "suggested_price": float(i["suggested_price"])},
                "link": "/app/costs",
            }
        )  # fmt: skip
    return out, ov["summary"]["unit_coverage_pct"]


def rule_discount(db: Session, ws: uuid.UUID, end: date) -> list[dict[str, Any]]:
    cur = metric_values(
        q.build_totals(db, ws, Filters(date_from=end - timedelta(days=6), date_to=end))[0]
    )
    prev = metric_values(
        q.build_totals(
            db, ws, Filters(date_from=end - timedelta(days=34), date_to=end - timedelta(days=7))
        )[0]
    )
    a, b = cur["discount_rate"], prev["discount_rate"]
    if a is None or b is None:
        return []
    pts = a - b
    if pts < DISCOUNT_MEDIUM:
        return []
    return [
        {
            "key": "discount_creep", "rule": "discount_creep",
            "severity": "high" if pts >= DISCOUNT_HIGH else "medium",
            "title": f"Discounts crept up to {a:.1f}% of sales",
            "detail": f"Over the last 7 days {a:.1f}% of gross sales were given away, against {b:.1f}% in the 4 weeks before. Check who is giving discounts and whether they are needed.",
            "evidence": {"now_pct": float(a), "before_pct": float(b), "points": float(pts)},
            "link": "/app/products",
        }
    ]  # fmt: skip


def rule_stopped(db: Session, ws: uuid.UUID, end: date) -> list[dict[str, Any]]:
    start = end - timedelta(days=34)
    stmt = _lines(
        [Product.sku, Product.name, Order.business_date, func.sum(OrderItem.quantity)],
        ws,
        Filters(date_from=start, date_to=end),
    ).group_by(Product.sku, Product.name, Order.business_date)
    days: dict[str, dict[date, Decimal]] = defaultdict(dict)
    names: dict[str, str] = {}
    for sku, name, day, units in db.execute(stmt).all():
        days[sku][day] = dec(units)
        names[sku] = name
    recent_from = end - timedelta(days=6)
    found = []
    for sku, per_day in days.items():
        prior = {d: u for d, u in per_day.items() if d < recent_from}
        if len(prior) >= STOPPED_MIN_DAYS and not any(d >= recent_from for d in per_day):
            found.append((sku, sum(prior.values(), ZERO), len(prior)))
    found.sort(key=lambda t: -t[1])
    return [
        {
            "key": f"product_stopped|{sku}", "rule": "product_stopped", "severity": "medium",
            "title": f"{names[sku]} has not sold for a week",
            "detail": f"It sold on {n_days} of the 28 days before, about {units / 28:.1f} units a day, and nothing in the last 7. It may be out of stock, delisted or missing from the data.",
            "evidence": {"selling_days_before": n_days, "units_before": float(units)},
            "link": "/app/products",
        }
        for sku, units, n_days in found[:5]
    ]  # fmt: skip


def rule_inventory(db: Session, workspace: Workspace) -> list[dict[str, Any]]:
    ov = inventory.overview(db, workspace)
    items = ov["items"]
    if not items:
        return []
    out: list[dict[str, Any]] = []
    for i in [x for x in items if x["status"] == "urgent"][:8]:
        out.append(
            {
                "key": f"stockout_risk|{i['sku']}", "rule": "stockout_risk", "severity": "high",
                "title": f"{i['name']} will run out in about {float(i['cover_days']):.0f} days",
                "detail": f"{float(i['on_hand']):.0f} left against about {float(i['daily_rate']):.1f} sold a day, and an order takes {i['lead_time_days']} days to arrive. Order about {float(i['order_qty']):.0f} now.",
                "evidence": {"on_hand": float(i["on_hand"]), "cover_days": float(i["cover_days"]), "lead_time_days": i["lead_time_days"], "order_qty": float(i["order_qty"])},
                "link": "/app/inventory",
            }
        )  # fmt: skip
    soon = [x for x in items if x["status"] == "reorder"]
    if soon:
        out.append(
            {
                "key": "reorder_soon", "rule": "reorder_soon", "severity": "medium",
                "title": f"{len(soon)} products need ordering this week",
                "detail": "They will run low before your next delivery window. The inventory page has a ready order list.",
                "evidence": {"products": len(soon)}, "link": "/app/inventory",
            }
        )  # fmt: skip
    dead_cash = ov["summary"]["dead_cash"]
    if ov["summary"]["dead"] and dead_cash > 0:
        out.append(
            {
                "key": "dead_stock", "rule": "dead_stock", "severity": "info",
                "title": f"{inr(dead_cash)} is tied up in {ov['summary']['dead']} products that have stopped selling",
                "detail": "Nothing sold in the last 30 days while stock sits on the shelf. Consider a clearance offer or returning it to the supplier.",
                "evidence": {"cash": float(dead_cash), "products": ov["summary"]["dead"]}, "link": "/app/inventory",
            }
        )  # fmt: skip
    return out


def rule_events(db: Session, workspace: Workspace, today: date) -> list[dict[str, Any]]:
    """Big festivals about to start that touch the shop's products, with stock that may not last."""
    out: list[dict[str, Any]] = []
    rows = events_insight.upcoming(db, workspace, days=21, include_cricket=False, today=today)
    for r in rows:
        e = r["event"]
        if (
            e.category != "festival"
            or e.tier > 2
            or r["matching_products"] == 0
            or r["status"] == "fading"
        ):
            continue
        risky = [p for p in r["products"] if p["at_risk"]]
        when = (
            "is on now"
            if r["status"] == "on"
            else f"starts in {max(r['days_until'], 0)} days"
            if r["days_until"] > 0
            else "starts today"
        )
        names = ", ".join(p["name"] for p in risky[:3])
        out.append(
            {
                "key": f"event_ahead|{e.id}", "rule": "event_ahead",
                "severity": "high" if risky else "medium",
                "title": f"{e.name} {when}" + (f": {len(risky)} of your products may run out" if risky else ""),
                "detail": (f"{names} may not last through it. Order more now." if risky else f"{r['matching_products']} of your products fit this event. Check your stock before demand builds.") + f" {e.notes}",
                "evidence": {"days_until": r["days_until"], "matching_products": r["matching_products"], "at_risk": len(risky)},
                "link": "/app/festivals",
            }
        )  # fmt: skip
        if len(out) >= 3:
            break
    return out


def rule_sources(db: Session, ws: uuid.UUID) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src in db.scalars(select(ImportSource).where(ImportSource.workspace_id == ws)).all():
        if src.last_status == "failed" and (src.failures >= 2 or not src.enabled):
            out.append(
                {
                    "key": f"source_failing|{src.id}", "rule": "source_failing",
                    "severity": "medium" if not src.enabled else "info",
                    "title": f"The link \"{src.name}\" could not be fetched" + (" and is paused" if not src.enabled else ""),
                    "detail": (src.last_message or "The last checks failed.") + " Fix the link or upload the file by hand so your numbers stay current.",
                    "evidence": {"failures": src.failures, "paused": not src.enabled},
                    "link": "/app/data",
                }
            )  # fmt: skip
    return out


def rule_customers(db: Session, workspace: Workspace, end: date) -> list[dict[str, Any]]:
    _, rows = intelligence.scored(db, workspace, end, 365, 30, 30, 45)
    n = sum(1 for r in rows if r.orders >= 2 and r.recency_days >= 45)
    if n < LAPSED_INFO:
        return []
    return [
        {
            "key": "lapsed_regulars", "rule": "lapsed_regulars",
            "severity": "medium" if n >= LAPSED_MEDIUM else "info",
            "title": f"{n} regular customers have gone quiet",
            "detail": "They bought at least twice and nothing in the last 45 days. A friendly message now costs less than losing them.",
            "evidence": {"customers": n}, "link": "/app/campaigns",
        }
    ]  # fmt: skip


def rule_supplier_prices(db: Session, ws: uuid.UUID) -> list[dict[str, Any]]:
    """A supplier charged noticeably more than last time, before it shows up in sales margins."""
    out: list[dict[str, Any]] = []
    for m in bill_service.price_moves(db, ws):
        if m["change_pct"] <= 0:
            continue
        out.append(
            {
                "key": f"supplier_price_up|{m['product_id']}", "rule": "supplier_price_up",
                "severity": "medium" if m["change_pct"] >= 10 else "info",
                "title": f"{m['name']} now costs {m['change_pct']:.0f}% more to buy",
                "detail": f"The last bill{' from ' + m['supplier'] if m['supplier'] else ''} was "
                f"{m['latest']} a unit against {m['previous']} before. Check your selling price covers it.",
                "evidence": {k: m[k] for k in ("previous", "latest", "change_pct", "supplier", "list_price")},
                "link": "/app/bills",
            }
        )  # fmt: skip
    return out


def rule_reviews(db: Session, ws: uuid.UUID, today: date) -> list[dict[str, Any]]:
    """A complaint theme that is both common and getting worse in the last 30 days."""
    s = review_service.summary(db, ws, 30, today)
    out: list[dict[str, Any]] = []
    for t in s["themes"]:
        n, pct, prior = t["mentions"], t["negative_pct"], t["prior_negative_pct"]
        worse = prior is None or pct - prior >= 15
        if n < 5 or pct < 40 or not worse:
            continue
        out.append(
            {
                "key": f"review_theme|{t['theme']}", "rule": "review_theme",
                "severity": "medium" if pct >= 60 and n >= 10 else "info",
                "title": f"Customers are unhappy about {t['label'].lower()}",
                "detail": f"{t['negative']} of {n} reviews that mention it in the last 30 days are negative ({pct:.0f}%)"
                + ("." if prior is None else f", up from {prior:.0f}% before.")
                + " Read what they wrote, then fix the cause.",
                "evidence": {"theme": t["theme"], "mentions": n, "negative_pct": pct, "prior_negative_pct": prior},
                "link": f"/app/reviews?theme={t['theme']}&label=negative",
            }
        )  # fmt: skip
    return out


def compute(
    db: Session, workspace: Workspace, as_of: date | None, today: date
) -> tuple[date | None, list[dict[str, Any]]]:
    first, last = q.workspace_bounds(db, workspace.id)
    if first is None or last is None:
        return None, []
    end = min(as_of or last, last)
    out = rule_sales(db, workspace.id, first, end)
    margin, coverage = rule_margin(db, workspace.id, end)
    out += (
        margin
        + rule_discount(db, workspace.id, end)
        + rule_stopped(db, workspace.id, end)
        + rule_customers(db, workspace, end)
        + rule_inventory(db, workspace)
        + rule_events(db, workspace, today)
        + rule_sources(db, workspace.id)
        + rule_reviews(db, workspace.id, today)
        + rule_supplier_prices(db, workspace.id)
    )
    if coverage is not None and coverage < 60:
        out.append(
            {
                "key": "no_costs", "rule": "no_costs", "severity": "info",
                "title": "Most of your sales have no cost recorded",
                "detail": f"Only {coverage:.0f}% of units sold have a cost, so margins and leaks are understated. Add costs on the Data page.",
                "evidence": {"coverage_pct": float(coverage)}, "link": "/app/data",
            }
        )  # fmt: skip
    if (today - end).days > STALE_DAYS:
        out.append(
            {
                "key": "data_stale", "rule": "data_stale", "severity": "info",
                "title": f"Your latest sales are from {end:%d %b %Y}",
                "detail": "Alerts and summaries are only as current as the last import. Import newer sales to keep them useful.",
                "evidence": {"days_old": (today - end).days}, "link": "/app/data",
            }
        )  # fmt: skip
    return end, out


# ------------------------------------------------------------------ storage


def refresh(
    db: Session, workspace: Workspace, *, as_of: date | None = None, today: date | None = None
) -> dict[str, Any]:
    today = today or date.today()
    end, found = compute(db, workspace, as_of, today)
    if end is None:
        return {"as_of": None, "opened": 0, "resolved": 0}
    now = datetime.now(UTC)
    existing = {
        a.key: a for a in db.scalars(select(Alert).where(Alert.workspace_id == workspace.id))
    }
    keys = {f["key"] for f in found}
    opened = 0
    for f in found:
        a = existing.get(f["key"])
        if a is None:
            db.add(
                Alert(workspace_id=workspace.id, status="open", first_seen=end, last_seen=end, **f)
            )
            opened += 1
            continue
        a.severity, a.title, a.detail, a.evidence, a.link, a.last_seen = (
            f["severity"],
            f["title"],
            f["detail"],
            f["evidence"],
            f["link"],
            end,
        )
        if a.status == "resolved":
            a.status, a.resolved_at = "open", None
            opened += 1
    resolved = 0
    for k, a in existing.items():
        if k not in keys and a.status in ("open", "dismissed"):
            a.status, a.resolved_at = "resolved", now
            resolved += 1
    db.commit()
    return {"as_of": end, "opened": opened, "resolved": resolved}


def counts(db: Session, ws: uuid.UUID) -> dict[str, int]:
    out = {"high": 0, "medium": 0, "info": 0}
    for sev, n in db.execute(
        select(Alert.severity, func.count())
        .where(Alert.workspace_id == ws, Alert.status == "open")
        .group_by(Alert.severity)
    ):
        out[sev] = n
    return out


def listing(db: Session, ws: uuid.UUID, status: str) -> list[Alert]:
    stmt = select(Alert).where(Alert.workspace_id == ws)
    if status != "all":
        stmt = stmt.where(Alert.status == status)
    rows = list(db.scalars(stmt).all())
    rows.sort(
        key=lambda a: (
            SEVERITY_RANK[a.severity],
            RULE_PRIORITY.get(a.rule, 99),
            -a.last_seen.toordinal(),
            a.key,
        )
    )
    return rows


def top_high(db: Session, ws: uuid.UUID) -> list[Alert]:
    return [a for a in listing(db, ws, "open") if a.severity == "high"]
