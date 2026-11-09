"""Cost history and margin-leak tracking, from the cost recorded on each sale line.

Every line keeps the unit cost the shop had at the time (docs/research/COST-TRACKING.md), so a
product's cost history is already in the sales data. We compare the last ``window`` days with the
``window`` days before:

- cost per unit and net price per unit, both on lines that have a cost (so they are comparable);
- margin leak: cost rose by at least ``MIN_CHANGE`` percent and the margin fell by more than one
  point, i.e. the price was not raised enough to pass the cost on;
- the price that would restore the earlier margin, and how much margin was lost in the window.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.commerce import Order, OrderItem, Product
from app.services.analytics import queries as q
from app.services.analytics.queries import HAS_COST, LINE_NET, _lines
from app.services.analytics.types import ZERO, Filters, dec, money

D = Decimal
MIN_CHANGE = D(3)  # percent change in cost that counts as a real move
LEAK_POINTS = D(1)  # margin must fall by more than this many points to be a leak
MIN_UNITS = D(5)  # ignore products with too few units in a window to compare


@dataclass(slots=True)
class Win:
    units: Decimal
    covered_units: Decimal
    covered_net: Decimal
    cogs: Decimal

    @property
    def cost(self) -> Decimal | None:
        return None if self.covered_units <= 0 else self.cogs / self.covered_units

    @property
    def price(self) -> Decimal | None:
        return None if self.covered_units <= 0 else self.covered_net / self.covered_units


def _stats(db: Session, ws: uuid.UUID, f: Filters) -> dict[str, tuple[str, str | None, Win]]:
    stmt = _lines(
        [
            Product.sku,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity),
            func.sum(case((HAS_COST, OrderItem.quantity), else_=0)),
            func.sum(case((HAS_COST, LINE_NET), else_=0)),
            func.sum(case((HAS_COST, OrderItem.quantity * OrderItem.unit_cost_snapshot), else_=0)),
        ],
        ws,
        f,
    ).group_by(Product.sku, Product.name, Product.category)
    return {
        r[0]: (r[1], r[2], Win(dec(r[3]), dec(r[4]), dec(r[5]), dec(r[6])))
        for r in db.execute(stmt).all()
    }


def _pct(a: Decimal, b: Decimal) -> Decimal:
    return ((a - b) / b * 100).quantize(D("0.1"), rounding=ROUND_HALF_UP)


def _margin(price: Decimal, cost: Decimal) -> Decimal:
    return ((price - cost) / price * 100).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def classify(prev: Win | None, cur: Win) -> dict[str, Any]:
    """Pure comparison of one product across two windows."""
    out: dict[str, Any] = {"status": "stable"}
    if cur.units > 0 and cur.covered_units <= 0:
        return {"status": "no_cost"}
    if (
        prev is None
        or prev.cost is None
        or prev.price is None
        or cur.cost is None
        or cur.price is None
    ):
        return {"status": "new"}
    if prev.covered_units < MIN_UNITS or cur.covered_units < MIN_UNITS:
        return {"status": "too_few"}
    cost_c, price_c = _pct(cur.cost, prev.cost), _pct(cur.price, prev.price)
    m_prev, m_now = _margin(prev.price, prev.cost), _margin(cur.price, cur.cost)
    # extra cost per unit that the price did not recover, over this window's units
    leak = money(cur.covered_units * ((cur.cost - prev.cost) - (cur.price - prev.price)))
    out |= {
        "cost_prev": money(prev.cost), "cost_now": money(cur.cost), "cost_change_pct": cost_c,
        "price_prev": money(prev.price), "price_now": money(cur.price), "price_change_pct": price_c,
        "margin_prev_pct": m_prev, "margin_now_pct": m_now, "units": cur.units, "leak_amount": leak,
    }  # fmt: skip
    if abs(cost_c) < MIN_CHANGE:
        return out
    if cost_c > 0:
        if m_now < m_prev - LEAK_POINTS and m_prev < 100:
            target = (cur.cost / (1 - m_prev / 100)).quantize(D(1), rounding=ROUND_CEILING)
            out |= {
                "status": "margin_leak",
                "suggested_price": target,
                "suggested_increase_pct": _pct(target, cur.price),
            }
        else:
            out["status"] = "passed_on"
    else:
        out["status"] = "cost_down"
    return out


def overview(
    db: Session, ws: uuid.UUID, as_of: date | None = None, window: int = 28
) -> dict[str, Any]:
    _, last = q.workspace_bounds(db, ws)
    if last is None:
        return {"as_of": None, "window_days": window, "items": [], "summary": _summary([], None)}
    end = min(as_of or last, last)
    cur_f = Filters(date_from=end - timedelta(days=window - 1), date_to=end)
    prev_f = Filters(
        date_from=cur_f.date_from - timedelta(days=window),
        date_to=cur_f.date_from - timedelta(days=1),
    )
    cur, prev = _stats(db, ws, cur_f), _stats(db, ws, prev_f)
    items = []
    for sku, (name, cat, win) in cur.items():
        res = classify(prev[sku][2] if sku in prev else None, win)
        items.append({"sku": sku, "name": name, "category": cat, **res})
    order = {
        "margin_leak": 0,
        "no_cost": 1,
        "cost_down": 2,
        "passed_on": 3,
        "stable": 4,
        "new": 5,
        "too_few": 6,
    }
    items.sort(key=lambda i: (order[i["status"]], -(i.get("leak_amount") or ZERO)))
    coverage = None
    tot_units = sum((w.units for _, _, w in cur.values()), ZERO)
    if tot_units > 0:
        coverage = (
            sum((w.covered_units for _, _, w in cur.values()), ZERO) / tot_units * 100
        ).quantize(D("0.1"), rounding=ROUND_HALF_UP)
    return {
        "as_of": end,
        "window_days": window,
        "current": {"from": cur_f.date_from, "to": cur_f.date_to},
        "previous": {"from": prev_f.date_from, "to": prev_f.date_to},
        "items": items,
        "summary": _summary(items, coverage),
    }


def _summary(items: list[dict[str, Any]], coverage: Decimal | None) -> dict[str, Any]:
    leaks = [i for i in items if i["status"] == "margin_leak"]
    return {
        "margin_leaks": len(leaks),
        "leak_amount": money(sum((i["leak_amount"] for i in leaks), ZERO)),
        "cost_up": sum(1 for i in items if i.get("cost_change_pct", ZERO) >= MIN_CHANGE),
        "cost_down": sum(1 for i in items if i["status"] == "cost_down"),
        "no_cost": sum(1 for i in items if i["status"] == "no_cost"),
        "unit_coverage_pct": coverage,
    }


def history(
    db: Session, ws: uuid.UUID, sku: str, weeks: int = 12, as_of: date | None = None
) -> dict[str, Any]:
    """Weekly average cost and net price per unit (lines with a cost) for one product."""
    _, last = q.workspace_bounds(db, ws)
    if last is None:
        return {"sku": sku, "weeks": []}
    end = min(as_of or last, last)
    start = end - timedelta(days=weeks * 7 - 1)
    stmt = _lines(
        [Order.business_date, func.sum(OrderItem.quantity), func.sum(LINE_NET), func.sum(OrderItem.quantity * OrderItem.unit_cost_snapshot)],
        ws,
        Filters(date_from=start, date_to=end, skus=(sku,)),
    ).where(HAS_COST).group_by(Order.business_date)  # fmt: skip
    buckets: dict[int, list[Decimal]] = {}
    for day, units, net, cogs in db.execute(stmt).all():
        w = (day - start).days // 7
        acc = buckets.setdefault(w, [ZERO, ZERO, ZERO])
        acc[0] += dec(units)
        acc[1] += dec(net)
        acc[2] += dec(cogs)
    rows = []
    for w in range(weeks):
        got = buckets.get(w)
        wk = start + timedelta(days=w * 7)
        rows.append(
            {
                "week_start": wk,
                "units": got[0] if got else ZERO,
                "cost": money(got[2] / got[0]) if got and got[0] > 0 else None,
                "price": money(got[1] / got[0]) if got and got[0] > 0 else None,
            }
        )
    return {"sku": sku, "weeks": rows}
