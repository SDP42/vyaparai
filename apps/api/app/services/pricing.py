"""Pricing and promotion advice from the shop's own sales: did discounts pay off, and are price moves safe?

Discounts. A product-day is a *promo day* when at least PROMO_RATE of that day's gross sales were discounted;
a *normal day* has under NORMAL_RATE (days with no sales count, so the baseline is the true average demand).
The baseline is the product's normal-day average for each weekday, so a promo on a Saturday is compared with
a normal Saturday, not an average day. For the promo days:
  lift   = units sold / units a normal day of that weekday would have sold - 1
  profit = profit made on those days minus the profit the baseline units would have made at normal margin
Both come with a bootstrap 95% range over the promo days. A discount "paid off" only if the whole profit
range is above zero, "lost money" only if it is entirely below, otherwise it is "unclear".

Price moves. A price move is a lasting change of at least MOVE_PCT in a product's average net price per unit
(weekly). Volume in the two weeks after is compared with the two weeks before, giving a rough elasticity
(% change in units per % change in price). One shop has few moves and a lot of noise; every row says how
reliable it is, and suggestions without a measured response use a stated range of assumed elasticities.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commerce import Order, OrderItem, OrderStatus, Product

PROMO_RATE = 0.03
NORMAL_RATE = 0.01
MIN_PROMO_DAYS = 3
MIN_NORMAL_DAYS = 28
LOOKBACK_DAYS = 180
MOVE_PCT = 3.0
ELASTICITY_RANGE = (
    -1.5,
    -1.0,
    -0.5,
)  # assumed when none was measured: (price-sensitive, typical, price-insensitive)


@dataclass(slots=True)
class Day:
    day: date
    units: float
    gross: float
    discount: float
    cost: float  # cost of the units that have a recorded cost
    costed_net: float  # net sales of those units

    @property
    def rate(self) -> float:
        return self.discount / self.gross if self.gross > 0 else 0.0

    @property
    def profit(self) -> float:
        return self.costed_net - self.cost


def daily(db: Session, ws: uuid.UUID, start: date, end: date) -> dict[str, tuple[str, list[Day]]]:
    net = OrderItem.quantity * OrderItem.unit_price - OrderItem.discount_amount
    stmt = (
        select(
            Product.sku, Product.name, Order.business_date, func.sum(OrderItem.quantity), func.sum(OrderItem.quantity * OrderItem.unit_price),
            func.sum(OrderItem.discount_amount), func.sum(func.coalesce(OrderItem.quantity * OrderItem.unit_cost_snapshot, 0)),
            func.sum(net * (OrderItem.unit_cost_snapshot.is_not(None))),
        )
        .join(Order, Order.id == OrderItem.order_id).join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.workspace_id == ws, Order.status == OrderStatus.COMPLETED, Order.business_date >= start, Order.business_date <= end)
        .group_by(Product.sku, Product.name, Order.business_date)
    )  # fmt: skip
    out: dict[str, tuple[str, list[Day]]] = {}
    for sku, name, d, u, g, disc, c, cn in db.execute(stmt).all():
        out.setdefault(sku, (name, []))[1].append(
            Day(d, float(u or 0), float(g or 0), float(disc or 0), float(c or 0), float(cn or 0))
        )
    return out


def _bounds(db: Session, ws: uuid.UUID) -> tuple[date, date] | None:
    first, last = db.execute(
        select(func.min(Order.business_date), func.max(Order.business_date)).where(
            Order.workspace_id == ws, Order.status == OrderStatus.COMPLETED
        )
    ).one()
    return None if first is None else (first, last)


def _boot(x: np.ndarray, reps: int = 1500, seed: int = 5) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    m = rng.choice(x, size=(reps, len(x))).mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def judge_discounts(days: list[Day], start: date, end: date) -> dict[str, Any] | None:
    """Did this product's discount days pay off? None when there is too little data to say anything."""
    by_date = {d.day: d for d in days}
    span = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    promo = [by_date[d] for d in span if d in by_date and by_date[d].rate >= PROMO_RATE]
    normal_dates = [d for d in span if d not in by_date or by_date[d].rate < NORMAL_RATE]
    if len(promo) < MIN_PROMO_DAYS or len(normal_dates) < MIN_NORMAL_DAYS:
        return None
    units_wd: dict[int, list[float]] = defaultdict(list)
    profit_per_unit_num = profit_per_unit_den = 0.0
    for d in normal_dates:
        row = by_date.get(d)
        units_wd[d.weekday()].append(row.units if row else 0.0)
        if row and row.units > 0 and row.costed_net > 0:
            profit_per_unit_num += row.profit
            profit_per_unit_den += row.units
    overall = float(np.mean([u for v in units_wd.values() for u in v]))
    base = {wd: (float(np.mean(v)) if len(v) >= 3 else overall) for wd, v in units_wd.items()}
    ppu = profit_per_unit_num / profit_per_unit_den if profit_per_unit_den else None
    exp_units = np.array([base.get(p.day.weekday(), overall) for p in promo])
    act_units = np.array([p.units for p in promo])
    lift = float(act_units.sum() / exp_units.sum() - 1) if exp_units.sum() > 0 else 0.0
    lift_days = act_units - exp_units
    lo_u, hi_u = _boot(lift_days)
    out: dict[str, Any] = {
        "promo_days": len(promo), "normal_days": len(normal_dates), "avg_discount_pct": round(100 * float(np.mean([p.rate for p in promo])), 1),
        "lift_pct": round(100 * lift, 1), "extra_units": round(float(lift_days.sum()), 1), "extra_units_low": round(lo_u * len(promo), 1), "extra_units_high": round(hi_u * len(promo), 1),
        "discount_given": round(sum(p.discount for p in promo), 2),
    }  # fmt: skip
    if ppu is None:
        return {
            **out,
            "profit_known": False,
            "verdict": "unclear",
            "note": "No cost is recorded for this product, so profit cannot be judged.",
        }
    inc = np.array([p.profit - e * ppu for p, e in zip(promo, exp_units, strict=True)])
    lo, hi = _boot(inc)
    verdict = "paid_off" if lo > 0 else "lost_money" if hi < 0 else "unclear"
    return {
        **out,
        "profit_known": True,
        "profit_effect": round(float(inc.sum()), 2),
        "profit_effect_low": round(lo * len(promo), 2),
        "profit_effect_high": round(hi * len(promo), 2),
        "verdict": verdict,
    }


def discounts(db: Session, ws: uuid.UUID, today: date | None = None) -> dict[str, Any]:
    b = _bounds(db, ws)
    if b is None:
        return {"has_data": False, "items": [], "summary": {}}
    end = min(today or b[1], b[1])
    start = max(b[0], end - timedelta(days=LOOKBACK_DAYS - 1))
    items = []
    for sku, (name, days) in daily(db, ws, start, end).items():
        r = judge_discounts(days, start, end)
        if r is not None:
            items.append({"sku": sku, "name": name, **r})
    order = {"lost_money": 0, "unclear": 1, "paid_off": 2}
    items.sort(key=lambda i: (order[i["verdict"]], -i["discount_given"]))
    lost = [i for i in items if i["verdict"] == "lost_money"]
    return {
        "has_data": True, "from": start.isoformat(), "to": end.isoformat(), "items": items,
        "summary": {"judged": len(items), "paid_off": sum(i["verdict"] == "paid_off" for i in items), "lost_money": len(lost), "unclear": sum(i["verdict"] == "unclear" for i in items),
                    "discount_in_losing_promos": round(sum(i["discount_given"] for i in lost), 2)},
        "method": f"Promo day: at least {PROMO_RATE * 100:.0f}% of the day's gross sales discounted. Normal day: under {NORMAL_RATE * 100:.0f}%. Compared with the product's normal average for the same weekday, over {LOOKBACK_DAYS} days.",
        "limits": ["Other things changed on promo days too (festivals, weather, stock). This compares like weekdays but cannot isolate the discount.", "A product with fewer than 3 promo days or 28 normal days is not judged."],
    }  # fmt: skip


# ------------------------------------------------------------------ price moves


def _weekly(days: list[Day]) -> dict[date, tuple[float, float]]:
    """week start -> (average net price per unit, units)."""
    acc: dict[date, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for d in days:
        wk = d.day - timedelta(days=d.day.weekday())
        acc[wk][0] += d.gross - d.discount
        acc[wk][1] += d.units
    return {k: (v[0] / v[1], v[1]) for k, v in acc.items() if v[1] > 0}


def detect_moves(days: list[Day]) -> list[dict[str, Any]]:
    wk = _weekly(days)
    weeks = sorted(wk)
    out = []
    i = 2
    while i < len(weeks) - 2:
        before_p = np.mean([wk[weeks[i - 2]][0], wk[weeks[i - 1]][0]])
        after = [wk[weeks[i]][0], wk[weeks[i + 1]][0]]
        after_p = float(np.mean(after))
        pct = (after_p / float(before_p) - 1) * 100
        stable = abs(after[0] / after[1] - 1) < 0.015 if after[1] else False
        if (
            abs(pct) >= MOVE_PCT
            and stable
            and all(weeks[j + 1] - weeks[j] == timedelta(days=7) for j in range(i - 2, i + 1))
        ):
            u_before = float(np.mean([wk[weeks[i - 2]][1], wk[weeks[i - 1]][1]]))
            u_after = float(np.mean([wk[weeks[i]][1], wk[weeks[i + 1]][1]]))
            upct = (u_after / u_before - 1) * 100 if u_before > 0 else 0.0
            el = upct / pct if pct else None
            out.append({"week": weeks[i].isoformat(), "old_price": round(float(before_p), 2), "new_price": round(after_p, 2), "price_pct": round(pct, 1), "units_pct": round(upct, 1),
                        "elasticity": None if el is None else round(el, 2), "reliable": u_before >= 20 and u_after >= 20})  # fmt: skip
            i += 3
        else:
            i += 1
    return out


def suggest(
    name: str,
    price: float,
    cost: float | None,
    monthly_units: float,
    measured: float | None,
    step_pct: float = 3.0,
) -> dict[str, Any] | None:
    """What a small price rise is likely to do to monthly profit, as a range."""
    if cost is None or monthly_units <= 0 or price <= 0 or cost >= price:
        return None
    new = price * (1 + step_pct / 100)
    els = (
        (measured, measured, measured)
        if measured is not None and measured > -3
        else ELASTICITY_RANGE
    )
    results = []
    for e in els:
        q = monthly_units * (1 + e * step_pct / 100)
        results.append((new - cost) * q - (price - cost) * monthly_units)
    lo, mid, hi = sorted(results)[0], results[1], sorted(results)[-1]
    return {"name": name, "price": round(price, 2), "suggested_price": round(new, 2), "step_pct": step_pct, "margin_pct": round((price - cost) / price * 100, 1),
            "profit_change_month": {"low": round(lo), "expected": round(mid), "high": round(hi)}, "measured": measured is not None,
            "assumption": None if measured is not None else f"No lasting price change was seen, so a typical shopper response is assumed: {int(-ELASTICITY_RANGE[2] * 100)}-{int(-ELASTICITY_RANGE[0] * 100)}% fewer units per 100% price rise."}  # fmt: skip


def price_moves(db: Session, ws: uuid.UUID, today: date | None = None) -> dict[str, Any]:
    b = _bounds(db, ws)
    if b is None:
        return {"has_data": False, "moves": [], "suggestions": []}
    end = min(today or b[1], b[1])
    start = max(b[0], end - timedelta(days=LOOKBACK_DAYS - 1))
    moves, suggestions = [], []
    for sku, (name, days) in daily(db, ws, start, end).items():
        for m in detect_moves(days):
            moves.append({"sku": sku, "name": name, **m})
        last28 = [d for d in days if d.day > end - timedelta(days=28)]
        units, gross, disc = (
            sum(d.units for d in last28),
            sum(d.gross for d in last28),
            sum(d.discount for d in last28),
        )
        costed_u = sum(d.units for d in last28 if d.cost > 0)
        cost_u = sum(d.cost for d in last28) / costed_u if costed_u else None
        if units < 20 or gross <= 0:
            continue
        price = (gross - disc) / units
        own = [
            m["elasticity"]
            for m in moves
            if m["sku"] == sku and m["reliable"] and m["elasticity"] is not None
        ]
        measured = float(np.mean(own)) if own else None
        s = suggest(name, price, cost_u, units, measured)
        if s is None:
            continue
        margin_low = s["margin_pct"] < 20
        if margin_low and s["profit_change_month"]["low"] > 0:
            suggestions.append(
                {
                    "sku": sku,
                    **s,
                    "why": "Margin is thin and even the price-sensitive case gains profit.",
                }
            )
        elif margin_low and s["profit_change_month"]["expected"] > 0:
            suggestions.append(
                {
                    "sku": sku,
                    **s,
                    "why": "Margin is thin; a small rise gains profit unless shoppers are very price-sensitive. Try it on a trial week.",
                }
            )
    moves.sort(key=lambda m: m["week"], reverse=True)
    suggestions.sort(key=lambda s: -s["profit_change_month"]["expected"])
    return {"has_data": True, "from": start.isoformat(), "to": end.isoformat(), "moves": moves[:40], "suggestions": suggestions[:15],
            "limits": ["A price move needs 2 stable weeks before and after and at least 20 units a week to count as reliable.", "Volume also moves with festivals, weather and stock; treat elasticity as a rough guide.", "Suggestions are small trials (+3%), never a large jump."]}  # fmt: skip
