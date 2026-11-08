"""SQL for analytics. Every query is workspace-scoped and counts only completed orders.

All sums are computed in the database; Python only rounds with Decimal.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, case, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.dataset import Job, JobStatus
from app.services.analytics.types import (
    UNSPECIFIED,
    ZERO,
    Dimension,
    Filters,
    ProductAgg,
    Totals,
    dec,
    money,
)

LINE_GROSS = OrderItem.quantity * OrderItem.unit_price
LINE_NET = LINE_GROSS - OrderItem.discount_amount
HAS_COST = OrderItem.unit_cost_snapshot.is_not(None)


def _in_or_null(column: Any, values: tuple[str, ...]) -> Any:
    """``column IN values``, treating the label 'Unspecified' as NULL."""
    real = [v for v in values if v != UNSPECIFIED]
    clauses = []
    if real:
        clauses.append(column.in_(real))
    if UNSPECIFIED in values:
        clauses.append(column.is_(None))
    return or_(*clauses)


def _lines(columns: list[Any], ws: uuid.UUID, f: Filters, *, customer: bool = False) -> Select[Any]:
    """Order lines of completed orders in the period, joined for filtering and grouping."""
    stmt = (
        select(*columns)
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
    )
    if customer or f.regions:
        stmt = stmt.outerjoin(Customer, Customer.id == Order.customer_id)
    stmt = stmt.where(
        OrderItem.workspace_id == ws,
        Order.workspace_id == ws,
        Order.status == OrderStatus.COMPLETED,
        Order.business_date >= f.date_from,
        Order.business_date <= f.date_to,
    )
    if f.categories:
        stmt = stmt.where(_in_or_null(Product.category, f.categories))
    if f.channels:
        stmt = stmt.where(_in_or_null(Order.channel, f.channels))
    if f.regions:
        stmt = stmt.where(_in_or_null(Customer.region, f.regions))
    if f.skus:
        stmt = stmt.where(Product.sku.in_(f.skus))
    return stmt


# ---------------------------------------------------------------- per-product


def per_product(db: Session, ws: uuid.UUID, f: Filters) -> list[ProductAgg]:
    stmt = _lines(
        [
            Product.id,
            Product.sku,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity),
            func.sum(LINE_GROSS),
            func.sum(OrderItem.discount_amount),
            func.sum(case((HAS_COST, OrderItem.quantity * OrderItem.unit_cost_snapshot), else_=0)),
            func.sum(case((HAS_COST, LINE_NET), else_=0)),
        ],
        ws,
        f,
    ).group_by(Product.id, Product.sku, Product.name, Product.category)
    return [
        ProductAgg(
            product_id=str(r[0]),
            sku=r[1],
            name=r[2],
            category=r[3],
            units=dec(r[4]),
            gross=money(r[5]),
            discount=money(r[6]),
            cogs=money(r[7]),
            covered_net=money(r[8]),
        )
        for r in db.execute(stmt).all()
    ]


def totals_from_products(products: list[ProductAgg]) -> Totals:
    t = Totals()
    for p in products:
        t.gross += p.gross
        t.discount += p.discount
        t.units += p.units
        t.cogs += p.cogs
        t.covered_net += p.covered_net
    return t


# ---------------------------------------------------------------- orders & customers


def order_count(db: Session, ws: uuid.UUID, f: Filters) -> int:
    stmt = _lines([func.count(distinct(Order.id))], ws, f)
    return int(db.scalar(stmt) or 0)


def anonymous_orders(db: Session, ws: uuid.UUID, f: Filters) -> int:
    stmt = _lines([func.count(distinct(Order.id))], ws, f).where(Order.customer_id.is_(None))
    return int(db.scalar(stmt) or 0)


def customer_counts(db: Session, ws: uuid.UUID, f: Filters) -> tuple[int, int, int]:
    """(active, new, repeat). New/repeat use each customer's whole completed history."""
    active_sub = (
        _lines([Order.customer_id.label("cid")], ws, f)
        .where(Order.customer_id.is_not(None))
        .distinct()
        .subquery()
    )
    active = int(db.scalar(select(func.count()).select_from(active_sub)) or 0)
    if active == 0:
        return 0, 0, 0
    history = (
        select(
            Order.customer_id.label("cid"),
            func.min(Order.business_date).label("first_day"),
            func.count(distinct(Order.id)).label("n"),
        )
        .where(
            Order.workspace_id == ws,
            Order.status == OrderStatus.COMPLETED,
            Order.customer_id.is_not(None),
            Order.customer_id.in_(select(active_sub.c.cid)),
        )
        .group_by(Order.customer_id)
        .subquery()
    )
    new = int(
        db.scalar(
            select(func.count())
            .select_from(history)
            .where(history.c.first_day >= f.date_from, history.c.first_day <= f.date_to)
        )
        or 0
    )
    repeat = int(db.scalar(select(func.count()).select_from(history).where(history.c.n >= 2)) or 0)
    return active, new, repeat


def days_with_data(db: Session, ws: uuid.UUID, f: Filters) -> int:
    return int(db.scalar(_lines([func.count(distinct(Order.business_date))], ws, f)) or 0)


def build_totals(db: Session, ws: uuid.UUID, f: Filters) -> tuple[Totals, list[ProductAgg]]:
    products = per_product(db, ws, f)
    t = totals_from_products(products)
    t.orders = order_count(db, ws, f)
    t.anonymous_orders = anonymous_orders(db, ws, f)
    t.active_customers, t.new_customers, t.repeat_customers = customer_counts(db, ws, f)
    t.days_with_data = days_with_data(db, ws, f)
    return t, products


# ---------------------------------------------------------------- time series


@dataclass(slots=True)
class DayAgg:
    gross: Any = ZERO
    discount: Any = ZERO
    units: Any = ZERO
    orders: int = 0

    @property
    def net(self) -> Any:
        return self.gross - self.discount


def daily(db: Session, ws: uuid.UUID, f: Filters) -> dict[date, DayAgg]:
    stmt = _lines(
        [
            Order.business_date,
            func.sum(LINE_GROSS),
            func.sum(OrderItem.discount_amount),
            func.sum(OrderItem.quantity),
            func.count(distinct(Order.id)),
        ],
        ws,
        f,
    ).group_by(Order.business_date)
    out: dict[date, DayAgg] = {}
    for d, gross, disc, units, orders in db.execute(stmt).all():
        out[d] = DayAgg(money(gross), money(disc), dec(units), int(orders))
    return out


def fill_days(
    data: dict[date, DayAgg], date_from: date, date_to: date
) -> list[tuple[date, DayAgg]]:
    out = []
    d = date_from
    while d <= date_to:
        out.append((d, data.get(d, DayAgg())))
        d += timedelta(days=1)
    return out


# ---------------------------------------------------------------- breakdowns


def breakdown(db: Session, ws: uuid.UUID, f: Filters, dim: Dimension) -> list[dict[str, Any]]:
    """Net sales, units and orders grouped by one dimension; missing values become 'Unspecified'."""
    if dim == "category":
        key_cols = [Product.category]
        needs_customer = False
    elif dim == "channel":
        key_cols = [Order.channel]
        needs_customer = False
    elif dim == "region":
        key_cols = [Customer.region]
        needs_customer = True
    else:
        key_cols = [Product.sku, Product.name]
        needs_customer = False
    stmt = _lines(
        [
            *key_cols,
            func.sum(LINE_GROSS),
            func.sum(OrderItem.discount_amount),
            func.sum(OrderItem.quantity),
            func.count(distinct(Order.id)),
        ],
        ws,
        f,
        customer=needs_customer,
    ).group_by(*key_cols)
    rows = []
    for r in db.execute(stmt).all():
        *keys, gross, disc, units, orders = r
        key = keys[0] if keys[0] is not None else UNSPECIFIED
        label = keys[1] if dim == "product" else key
        rows.append(
            {
                "key": key,
                "label": label,
                "gross": money(gross),
                "discount": money(disc),
                "net": money(gross) - money(disc),
                "units": dec(units),
                "orders": int(orders),
            }
        )
    return rows


def merge_breakdowns(
    current: list[dict[str, Any]], previous: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Join two breakdowns on key, adding previous net and the change."""
    prev = {r["key"]: r for r in (previous or [])}
    keys = {r["key"] for r in current} | set(prev)
    cur = {r["key"]: r for r in current}
    total_cur = sum((r["net"] for r in current), ZERO)
    total_delta = total_cur - sum((r["net"] for r in (previous or [])), ZERO)
    out = []
    for k in keys:
        c, p = cur.get(k), prev.get(k)
        net = c["net"] if c else ZERO
        pnet = p["net"] if p else ZERO
        out.append(
            {
                "key": k,
                "label": (c or p)["label"],  # type: ignore[index]
                "net": net,
                "previous_net": pnet if previous is not None else None,
                "delta": (net - pnet) if previous is not None else None,
                "share": (net / total_cur * 100) if total_cur else None,
                "share_of_change": (
                    (net - pnet) / total_delta * 100
                    if previous is not None and total_delta != 0
                    else None
                ),
                "units": c["units"] if c else ZERO,
                "orders": c["orders"] if c else 0,
            }
        )
    out.sort(key=lambda r: r["net"], reverse=True)
    return out


# ---------------------------------------------------------------- coverage & options


def excluded_orders_by_status(db: Session, ws: uuid.UUID, f: Filters) -> dict[str, int]:
    stmt = (
        select(Order.status, func.count(Order.id))
        .where(
            Order.workspace_id == ws,
            Order.status != OrderStatus.COMPLETED,
            Order.business_date >= f.date_from,
            Order.business_date <= f.date_to,
        )
        .group_by(Order.status)
    )
    return {s.value: int(n) for s, n in db.execute(stmt).all()}


def workspace_bounds(db: Session, ws: uuid.UUID) -> tuple[date | None, date | None]:
    row = db.execute(
        select(func.min(Order.business_date), func.max(Order.business_date)).where(
            Order.workspace_id == ws, Order.status == OrderStatus.COMPLETED
        )
    ).one()
    return row[0], row[1]


def last_import_at(db: Session, ws: uuid.UUID) -> Any:
    return db.scalar(
        select(func.max(Job.finished_at)).where(
            Job.workspace_id == ws, Job.status == JobStatus.SUCCEEDED
        )
    )


def filter_options(db: Session, ws: uuid.UUID) -> dict[str, list[str]]:
    categories = sorted(
        v
        for (v,) in db.execute(
            select(Product.category).where(Product.workspace_id == ws).distinct()
        ).all()
        if v
    )
    channels = sorted(
        v
        for (v,) in db.execute(
            select(Order.channel).where(Order.workspace_id == ws).distinct()
        ).all()
        if v
    )
    regions = sorted(
        v
        for (v,) in db.execute(
            select(Customer.region).where(Customer.workspace_id == ws).distinct()
        ).all()
        if v
    )
    return {"categories": categories, "channels": channels, "regions": regions}


# ---------------------------------------------------------------- drill-through


def _search_clause(search: str) -> Any:
    like = f"%{search.strip()}%"
    return or_(Order.external_key.ilike(like), Product.sku.ilike(like), Product.name.ilike(like))


def transactions(
    db: Session, ws: uuid.UUID, f: Filters, *, limit: int, offset: int, search: str | None
) -> tuple[list[dict[str, Any]], int, Any]:
    """Order lines behind the numbers, newest first, plus the line count and net total."""
    cols = [
        Order.external_key,
        Order.business_date,
        Product.sku,
        Product.name,
        Product.category,
        OrderItem.quantity,
        OrderItem.unit_price,
        OrderItem.discount_amount,
        LINE_NET,
        Customer.external_key,
        Order.channel,
    ]
    rows_stmt = _lines(cols, ws, f, customer=True)
    agg_stmt = _lines([func.count(OrderItem.id), func.sum(LINE_NET)], ws, f, customer=True)
    if search and search.strip():
        rows_stmt = rows_stmt.where(_search_clause(search))
        agg_stmt = agg_stmt.where(_search_clause(search))
    total, net = db.execute(agg_stmt).one()
    rows = db.execute(
        rows_stmt.order_by(Order.business_date.desc(), Order.external_key, Product.sku)
        .limit(limit)
        .offset(offset)
    ).all()
    out = [
        {
            "order_id": r[0],
            "date": r[1],
            "sku": r[2],
            "product": r[3],
            "category": r[4],
            "quantity": dec(r[5]),
            "unit_price": money(r[6]),
            "discount": money(r[7]),
            "net": money(r[8]),
            "customer": r[9],
            "channel": r[10],
        }
        for r in rows
    ]
    return out, int(total or 0), money(net)
