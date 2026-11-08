"""Product intelligence: margin, discount impact, ABC class and portfolio quadrants.

Definitions (docs/research/PHASE-3-RESEARCH.md):
- Margin uses only lines that have a cost; cost coverage says how much of the sales that is.
- ABC by cumulative share of net sales: A up to 80 %, B up to 95 %, C the rest. A product that
  crosses a boundary stays in the better class.
- Portfolio quadrant (menu-engineering adapted to retail): popular = units at or above the median
  product; profitable = margin % at or above the overall margin %.
"""

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.commerce import OrderItem, Product
from app.services.analytics.queries import HAS_COST, LINE_GROSS, LINE_NET, _lines
from app.services.analytics.types import ZERO, Filters, dec, money

A_LIMIT = Decimal(80)
B_LIMIT = Decimal(95)
DISCOUNT_HEAVY_MIN = Decimal(3)  # % of gross
CHANGE_FLAG = Decimal(20)  # % change that earns a "declining" / "rising" flag

QUADRANT_HELP = {
    "Star": "Sells a lot and earns a good margin: protect it",
    "Workhorse": "Sells a lot at a low margin: look at its cost or price",
    "Puzzle": "Earns a good margin but sells little: promote it",
    "Dog": "Sells little at a low margin: consider dropping it",
    "Unknown": "No cost recorded, so the margin cannot be judged",
}


@dataclass(slots=True)
class ProductPerf:
    key: str
    name: str
    category: str | None
    units: Decimal
    gross: Decimal
    discount: Decimal
    cogs: Decimal
    covered_net: Decimal
    lines: int
    discounted_lines: int
    previous_net: Decimal | None = None

    @property
    def net(self) -> Decimal:
        return self.gross - self.discount


def pct(a: Decimal, b: Decimal) -> Decimal | None:
    return None if b == 0 else (a / b * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def overall_margin(rows: list[ProductPerf]) -> Decimal | None:
    covered = sum((r.covered_net for r in rows), ZERO)
    cogs = sum((r.cogs for r in rows), ZERO)
    return pct(covered - cogs, covered)


def classify(rows: list[ProductPerf]) -> list[dict[str, Any]]:
    """Add shares, ABC class, margin, discount flags and the portfolio quadrant to each product."""
    total_net = sum((r.net for r in rows), ZERO)
    total_gross = sum((r.gross for r in rows), ZERO)
    total_discount = sum((r.discount for r in rows), ZERO)
    overall_discount = pct(total_discount, total_gross) or ZERO
    margin_ref = overall_margin(rows)
    sellers = [r.units for r in rows if r.units > 0]
    unit_median = Decimal(str(median(sellers))) if sellers else ZERO
    discount_cut = max(DISCOUNT_HEAVY_MIN, overall_discount * 2)

    out: list[dict[str, Any]] = []
    cum_net = ZERO  # accumulate exact amounts: summing rounded shares drifts below 100 %
    for r in sorted(rows, key=lambda x: x.net, reverse=True):
        share = pct(r.net, total_net)
        cum_before = cum_net / total_net * 100 if total_net else ZERO
        abc = "A" if cum_before < A_LIMIT else "B" if cum_before < B_LIMIT else "C"
        cum_net += r.net
        cum_after = cum_net / total_net * 100 if total_net else ZERO
        gp = r.covered_net - r.cogs
        margin = pct(gp, r.covered_net)
        popular = r.units >= unit_median
        if margin is None or margin_ref is None:
            quadrant = "Unknown"
        else:
            profitable = margin >= margin_ref
            quadrant = (
                ("Star" if profitable else "Workhorse")
                if popular
                else ("Puzzle" if profitable else "Dog")
            )
        discount_rate = pct(r.discount, r.gross)
        flags = []
        if discount_rate is not None and discount_rate >= discount_cut:
            flags.append("discount_heavy")
        if r.covered_net == 0:
            flags.append("no_cost")
        change = None
        if r.previous_net is not None and r.previous_net > 0:
            change = ((r.net - r.previous_net) / r.previous_net * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if change <= -CHANGE_FLAG:
                flags.append("declining")
            elif change >= CHANGE_FLAG:
                flags.append("rising")
        out.append(
            {
                "key": r.key,
                "name": r.name,
                "category": r.category,
                "units": r.units,
                "net": money(r.net),
                "gross": money(r.gross),
                "discount": money(r.discount),
                "discount_rate": discount_rate,
                "discounted_line_share": pct(Decimal(r.discounted_lines), Decimal(r.lines)),
                "margin_amount": money(gp) if r.covered_net else None,
                "margin_pct": margin,
                "cost_coverage_pct": pct(r.covered_net, r.net),
                "share": share,
                "cumulative_share": min(Decimal(100), cum_after).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "abc": abc,
                "quadrant": quadrant,
                "previous_net": money(r.previous_net) if r.previous_net is not None else None,
                "change_pct": change,
                "flags": flags,
            }
        )
    return out


def by_category(rows: list[ProductPerf]) -> list[dict[str, Any]]:
    groups: dict[str, list[ProductPerf]] = {}
    for r in rows:
        groups.setdefault(r.category or "Unspecified", []).append(r)
    total_net = sum((r.net for r in rows), ZERO)
    out = []
    for name, members in groups.items():
        gross = sum((m.gross for m in members), ZERO)
        discount = sum((m.discount for m in members), ZERO)
        net = gross - discount
        covered = sum((m.covered_net for m in members), ZERO)
        cogs = sum((m.cogs for m in members), ZERO)
        prev = (
            sum((m.previous_net or ZERO for m in members), ZERO)
            if any(m.previous_net is not None for m in members)
            else None
        )
        out.append(
            {
                "category": name,
                "products": len(members),
                "units": sum((m.units for m in members), ZERO),
                "net": money(net),
                "share": pct(net, total_net),
                "discount_rate": pct(discount, gross),
                "margin_amount": money(covered - cogs) if covered else None,
                "margin_pct": pct(covered - cogs, covered),
                "cost_coverage_pct": pct(covered, net),
                "previous_net": money(prev) if prev is not None else None,
                "change_pct": (
                    ((net - prev) / prev * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if prev
                    else None
                ),
            }
        )
    return sorted(out, key=lambda r: r["net"], reverse=True)


def portfolio_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {q: sum(1 for i in items if i["quadrant"] == q) for q in QUADRANT_HELP}
    nets = {q: sum((i["net"] for i in items if i["quadrant"] == q), ZERO) for q in QUADRANT_HELP}
    abc = {c: sum(1 for i in items if i["abc"] == c) for c in "ABC"}
    return {
        "quadrants": [
            {"quadrant": q, "help": h, "products": counts[q], "net": nets[q]}
            for q, h in QUADRANT_HELP.items()
        ],
        "abc": abc,
        "discount_heavy": sum(1 for i in items if "discount_heavy" in i["flags"]),
        "declining": sum(1 for i in items if "declining" in i["flags"]),
        "rising": sum(1 for i in items if "rising" in i["flags"]),
    }


def product_perf(db: Session, ws: uuid.UUID, f: Filters) -> list[ProductPerf]:
    stmt = _lines(
        [
            Product.sku,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity),
            func.sum(LINE_GROSS),
            func.sum(OrderItem.discount_amount),
            func.sum(case((HAS_COST, OrderItem.quantity * OrderItem.unit_cost_snapshot), else_=0)),
            func.sum(case((HAS_COST, LINE_NET), else_=0)),
            func.count(OrderItem.id),
            func.sum(case((OrderItem.discount_amount > 0, 1), else_=0)),
        ],
        ws,
        f,
    ).group_by(Product.sku, Product.name, Product.category)
    return [
        ProductPerf(
            key=r[0],
            name=r[1],
            category=r[2],
            units=dec(r[3]),
            gross=money(r[4]),
            discount=money(r[5]),
            cogs=money(r[6]),
            covered_net=money(r[7]),
            lines=int(r[8]),
            discounted_lines=int(r[9] or 0),
        )
        for r in db.execute(stmt).all()
    ]


def attach_previous(rows: list[ProductPerf], previous: list[ProductPerf] | None) -> None:
    if previous is None:
        return
    prev = {p.key: p.net for p in previous}
    for r in rows:
        r.previous_net = prev.get(r.key, ZERO)
