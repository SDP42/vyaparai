"""Customer intelligence: RFM scores, named segments, activity status and cohort retention.

Rules are explicit and documented in docs/research/PHASE-3-RESEARCH.md and docs/METRICS.md.
Only customers with an ID are analysed; walk-in orders cannot be tracked over time.
"""

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models.commerce import Customer, Order, OrderItem, OrderStatus
from app.services.analytics.queries import LINE_NET
from app.services.analytics.types import ZERO, money

SEGMENTS = [
    "Champions",
    "Loyal",
    "New",
    "Promising",
    "Needs attention",
    "Can't lose",
    "At risk",
    "Hibernating",
]
SEGMENT_HELP = {
    "Champions": "Bought recently and often (R ≥ 4, F ≥ 4)",
    "Loyal": "Regulars who still come back (R ≥ 3, F ≥ 3)",
    "New": "First order in the last 30 days and only one order so far",
    "Promising": "Bought recently but not often yet (R ≥ 4, F ≤ 2)",
    "Needs attention": "Average recency, low frequency (R = 3, F ≤ 2)",
    "Can't lose": "Big spenders who have gone quiet (R ≤ 2, F ≥ 4, M ≥ 4)",
    "At risk": "Used to buy often, not recently (R ≤ 2, F ≥ 3)",
    "Hibernating": "Rarely bought and not recently (R ≤ 2, F ≤ 2)",
}
STATUSES = ["Active", "Cooling", "Lapsed"]


# ------------------------------------------------------------------ pure logic


def percentile_scores(values: list[float], higher_is_better: bool = True) -> list[int]:
    """Score 1-5 by tie-fair percentile rank.

    percentile = (customers strictly worse + half of those equal) / n;  score = floor(p*5) + 1.
    Identical values always share a score, so ties are never split arbitrarily.
    """
    n = len(values)
    if n == 0:
        return []
    out = []
    for v in values:
        worse = sum(1 for x in values if (x < v if higher_is_better else x > v))
        equal = sum(1 for x in values if x == v)
        pct = (worse + 0.5 * equal) / n
        out.append(min(5, int(pct * 5) + 1))
    return out


def segment_for(
    r: int, f: int, m: int, *, orders: int, first_order: date, as_of: date, new_days: int = 30
) -> str:
    """First matching rule wins. Every (r, f) pair maps to exactly one segment."""
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal"
    if orders == 1 and (as_of - first_order).days <= new_days:
        return "New"
    if r >= 4:  # f <= 2
        return "Promising"
    if r == 3:  # f <= 2
        return "Needs attention"
    if f >= 4 and m >= 4:  # r <= 2
        return "Can't lose"
    if f >= 3:
        return "At risk"
    return "Hibernating"


def status_for(days_since_last: int, active_days: int = 30, lapse_days: int = 45) -> str:
    if days_since_last <= active_days:
        return "Active"
    if days_since_last < lapse_days:
        return "Cooling"
    return "Lapsed"


@dataclass(slots=True)
class CustomerStat:
    key: str
    region: str | None
    city: str | None
    first_order: date  # all-time, up to the as-of date
    last_order: date
    orders: int  # within the lookback window
    net: Decimal  # within the lookback window


@dataclass(slots=True)
class CustomerRow:
    key: str
    region: str | None
    city: str | None
    first_order: date
    last_order: date
    orders: int
    net: Decimal
    recency_days: int
    r: int
    f: int
    m: int
    segment: str
    status: str

    @property
    def aov(self) -> Decimal:
        return money(self.net / self.orders) if self.orders else ZERO


def score_customers(
    stats: list[CustomerStat],
    as_of: date,
    *,
    new_days: int = 30,
    active_days: int = 30,
    lapse_days: int = 45,
) -> list[CustomerRow]:
    recency = [(as_of - s.last_order).days for s in stats]
    r_scores = percentile_scores([float(x) for x in recency], higher_is_better=False)
    f_scores = percentile_scores([float(s.orders) for s in stats])
    m_scores = percentile_scores([float(s.net) for s in stats])
    rows = []
    for s, days, r, f, m in zip(stats, recency, r_scores, f_scores, m_scores, strict=True):
        rows.append(
            CustomerRow(
                key=s.key,
                region=s.region,
                city=s.city,
                first_order=s.first_order,
                last_order=s.last_order,
                orders=s.orders,
                net=money(s.net),
                recency_days=days,
                r=r,
                f=f,
                m=m,
                segment=segment_for(
                    r,
                    f,
                    m,
                    orders=s.orders,
                    first_order=s.first_order,
                    as_of=as_of,
                    new_days=new_days,
                ),
                status=status_for(days, active_days, lapse_days),
            )
        )
    return rows


def top_share(values: list[Decimal], fraction: float = 0.10) -> Decimal | None:
    """Share of the total held by the top ``fraction`` of customers (at least one customer)."""
    total = sum(values, ZERO)
    if not values or total == 0:
        return None
    k = max(1, math.ceil(len(values) * fraction))
    top = sum(sorted(values, reverse=True)[:k], ZERO)
    return (top / total * 100).quantize(Decimal("0.01"))


def summarise(rows: list[CustomerRow]) -> dict[str, Any]:
    n = len(rows)
    total_net = sum((r.net for r in rows), ZERO)
    seg_rows = []
    for name in SEGMENTS:
        members = [r for r in rows if r.segment == name]
        net = sum((r.net for r in members), ZERO)
        seg_rows.append(
            {
                "segment": name,
                "help": SEGMENT_HELP[name],
                "customers": len(members),
                "share": _pct(len(members), n),
                "net": net,
                "net_share": _pct(net, total_net),
                "avg_orders": _avg([r.orders for r in members]),
                "avg_recency_days": _avg([r.recency_days for r in members]),
            }
        )
    status_counts = {s: sum(1 for r in rows if r.status == s) for s in STATUSES}
    grid = [[0] * 5 for _ in range(5)]  # rows = recency score 5..1, cols = frequency score 1..5
    for r in rows:
        grid[5 - r.r][r.f - 1] += 1
    repeat = sum(1 for r in rows if r.orders >= 2)
    lapsed_regulars = sum(1 for r in rows if r.status == "Lapsed" and r.orders >= 2)
    return {
        "customers": n,
        "net": total_net,
        "repeat_customers": repeat,
        "repeat_rate": _pct(repeat, n),
        "revenue_per_customer": money(total_net / n) if n else None,
        "avg_orders_per_customer": _avg([r.orders for r in rows]),
        "top_decile_share": top_share([r.net for r in rows]),
        "lapsed_regulars": lapsed_regulars,
        "status_counts": status_counts,
        "segments": seg_rows,
        "rfm_grid": grid,
    }


def _pct(a: Any, b: Any) -> Decimal | None:
    return None if not b else (Decimal(str(a)) / Decimal(str(b)) * 100).quantize(Decimal("0.01"))


def _avg(xs: list[int]) -> Decimal | None:
    return None if not xs else (Decimal(sum(xs)) / len(xs)).quantize(Decimal("0.1"))


# ------------------------------------------------------------------ SQL


def customer_stats(
    db: Session, ws: uuid.UUID, as_of: date, lookback_days: int
) -> list[CustomerStat]:
    """Per-customer orders and net sales in the lookback window, with all-time first order."""
    window_from = as_of - timedelta(days=lookback_days - 1)
    window = (
        select(
            Order.customer_id.label("cid"),
            func.count(distinct(Order.id)).label("orders"),
            func.sum(LINE_NET).label("net"),
            func.max(Order.business_date).label("last_order"),
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.workspace_id == ws,
            Order.workspace_id == ws,
            Order.status == OrderStatus.COMPLETED,
            Order.customer_id.is_not(None),
            Order.business_date >= window_from,
            Order.business_date <= as_of,
        )
        .group_by(Order.customer_id)
        .subquery()
    )
    firsts = (
        select(Order.customer_id.label("cid"), func.min(Order.business_date).label("first_order"))
        .where(
            Order.workspace_id == ws,
            Order.status == OrderStatus.COMPLETED,
            Order.customer_id.is_not(None),
            Order.business_date <= as_of,
        )
        .group_by(Order.customer_id)
        .subquery()
    )
    stmt = (
        select(
            Customer.external_key,
            Customer.region,
            Customer.city,
            firsts.c.first_order,
            window.c.last_order,
            window.c.orders,
            window.c.net,
        )
        .join(window, window.c.cid == Customer.id)
        .join(firsts, firsts.c.cid == Customer.id)
        .where(Customer.workspace_id == ws)
    )
    return [
        CustomerStat(
            key=r[0],
            region=r[1],
            city=r[2],
            first_order=r[3],
            last_order=r[4],
            orders=int(r[5]),
            net=money(r[6]),
        )
        for r in db.execute(stmt).all()
    ]


def walk_in_share(db: Session, ws: uuid.UUID, as_of: date, lookback_days: int) -> Decimal | None:
    window_from = as_of - timedelta(days=lookback_days - 1)
    base = [
        Order.workspace_id == ws,
        Order.status == OrderStatus.COMPLETED,
        Order.business_date >= window_from,
        Order.business_date <= as_of,
    ]
    total = int(db.scalar(select(func.count(Order.id)).where(*base)) or 0)
    anon = int(
        db.scalar(select(func.count(Order.id)).where(*base, Order.customer_id.is_(None))) or 0
    )
    return _pct(anon, total)


def cohort_matrix(db: Session, ws: uuid.UUID, as_of: date, months: int = 12) -> dict[str, Any]:
    """Customers grouped by first-order month; retention = share buying again k months later."""
    rows = db.execute(
        select(Order.customer_id, Order.business_date)
        .where(
            Order.workspace_id == ws,
            Order.status == OrderStatus.COMPLETED,
            Order.customer_id.is_not(None),
            Order.business_date <= as_of,
        )
        .distinct()
    ).all()

    def month_index(d: date) -> int:
        return d.year * 12 + d.month - 1

    active: dict[Any, set[int]] = defaultdict(set)
    for cid, d in rows:
        active[cid].add(month_index(d))
    cohorts: dict[int, list[Any]] = defaultdict(list)
    for cid, ms in active.items():
        cohorts[min(ms)].append(cid)

    last = month_index(as_of)
    keep = sorted(cohorts)[-months:]
    out_rows: list[dict[str, Any]] = []
    for c in keep:
        members = cohorts[c]
        size = len(members)
        max_offset = last - c
        counts = [
            sum(1 for cid in members if (c + k) in active[cid]) for k in range(max_offset + 1)
        ]
        year, month = divmod(c, 12)
        out_rows.append(
            {
                "cohort": f"{year}-{month + 1:02d}",
                "size": size,
                "counts": counts,
                "retention": [_pct(n, size) for n in counts],
            }
        )
    width = max((len(r["counts"]) for r in out_rows), default=0)
    return {"months": width, "cohorts": out_rows}
