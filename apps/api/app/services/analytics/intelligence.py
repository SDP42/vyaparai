"""Assembles the customer and product intelligence responses."""

import csv
import io
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.workspace import Workspace
from app.services.analytics import basket, customers, products
from app.services.analytics import queries as q
from app.services.analytics.compare import pick_granularity, resolve_compare
from app.services.analytics.service import _meta
from app.services.analytics.types import ZERO, CompareMode, Filters, metric_values

SORTS = {
    "net": lambda r: r.net,
    "orders": lambda r: r.orders,
    "recency": lambda r: r.recency_days,  # days since last order; descending = quietest first
    "last_order": lambda r: r.last_order,
    "name": lambda r: r.key,
}


class BadParamsError(AppError):
    status_code = 422
    code = "invalid_params"


def check_params(active_days: int, lapse_days: int) -> None:
    if lapse_days <= active_days:
        raise BadParamsError("lapse_days must be greater than active_days")


def _as_of(db: Session, workspace: Workspace, as_of: date | None) -> date:
    if as_of:
        return as_of
    _, last = q.workspace_bounds(db, workspace.id)
    return last or datetime.now(UTC).date()


def _params(as_of: date, lookback: int, new_days: int, active: int, lapse: int) -> dict[str, Any]:
    return {
        "as_of": as_of,
        "lookback_days": lookback,
        "new_days": new_days,
        "active_days": active,
        "lapse_days": lapse,
    }


def scored(
    db: Session,
    workspace: Workspace,
    as_of: date | None,
    lookback_days: int,
    new_days: int,
    active_days: int,
    lapse_days: int,
) -> tuple[date, list[customers.CustomerRow]]:
    check_params(active_days, lapse_days)
    day = _as_of(db, workspace, as_of)
    stats = customers.customer_stats(db, workspace.id, day, lookback_days)
    rows = customers.score_customers(
        stats, day, new_days=new_days, active_days=active_days, lapse_days=lapse_days
    )
    return day, rows


def customers_summary(
    db: Session,
    workspace: Workspace,
    as_of: date | None,
    lookback_days: int,
    new_days: int,
    active_days: int,
    lapse_days: int,
) -> dict[str, Any]:
    day, rows = scored(db, workspace, as_of, lookback_days, new_days, active_days, lapse_days)
    summary = customers.summarise(rows)
    walk_in = customers.walk_in_share(db, workspace.id, day, lookback_days)
    warnings: list[str] = []
    if not rows:
        warnings.append(
            "No customers with an ID have bought in this window, so there is nothing to segment."
        )
    elif len(rows) < 10:
        warnings.append(
            f"Only {len(rows)} customers: segments are unreliable below about 10 customers."
        )
    if walk_in is not None and walk_in >= 20:
        warnings.append(
            f"{walk_in}% of orders have no customer (walk-ins), so these figures cover only "
            "identified customers."
        )
    return {
        "params": _params(day, lookback_days, new_days, active_days, lapse_days),
        "currency": workspace.currency,
        "walk_in_share": walk_in,
        "warnings": warnings,
        **summary,
    }


def customers_list(
    db: Session,
    workspace: Workspace,
    as_of: date | None,
    lookback_days: int,
    new_days: int,
    active_days: int,
    lapse_days: int,
    *,
    segment: str | None,
    status: str | None,
    search: str | None,
    sort: str,
    descending: bool,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    day, rows = scored(db, workspace, as_of, lookback_days, new_days, active_days, lapse_days)
    rows = filter_rows(rows, segment, status, search)
    key = SORTS.get(sort, SORTS["net"])
    rows.sort(key=key, reverse=descending)
    page = rows[offset : offset + limit]
    return {
        "params": _params(day, lookback_days, new_days, active_days, lapse_days),
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "items": [{**vars_of(r), "aov": r.aov} for r in page],
    }


def filter_rows(
    rows: list[customers.CustomerRow], segment: str | None, status: str | None, search: str | None
) -> list[customers.CustomerRow]:
    if segment:
        rows = [r for r in rows if r.segment == segment]
    if status:
        rows = [r for r in rows if r.status == status]
    if search and search.strip():
        needle = search.strip().lower()
        rows = [r for r in rows if needle in r.key.lower() or needle in (r.city or "").lower()]
    return rows


def vars_of(r: customers.CustomerRow) -> dict[str, Any]:
    return {
        "key": r.key,
        "region": r.region,
        "city": r.city,
        "first_order": r.first_order,
        "last_order": r.last_order,
        "orders": r.orders,
        "net": r.net,
        "recency_days": r.recency_days,
        "r": r.r,
        "f": r.f,
        "m": r.m,
        "segment": r.segment,
        "status": r.status,
    }


def customers_csv(rows: list[customers.CustomerRow]) -> Iterator[str]:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["customer", "segment", "status", "region", "city", "first_order", "last_order",
         "days_since_last_order", "orders", "net_sales", "avg_order_value", "R", "F", "M"]
    )  # fmt: skip
    yield buf.getvalue()
    for r in rows:
        buf.seek(0)
        buf.truncate()
        w.writerow(
            [r.key, r.segment, r.status, r.region or "", r.city or "", r.first_order,
             r.last_order, r.recency_days, r.orders, r.net, r.aov, r.r, r.f, r.m]
        )  # fmt: skip
        yield buf.getvalue()


def cohorts(db: Session, workspace: Workspace, as_of: date | None, months: int) -> dict[str, Any]:
    day = _as_of(db, workspace, as_of)
    data = customers.cohort_matrix(db, workspace.id, day, months)
    warnings = []
    if len(data["cohorts"]) < 2:
        warnings.append("Cohorts need at least two months of customer history to compare.")
    return {"as_of": day, **data, "warnings": warnings}


# ------------------------------------------------------------------ products


def products_overview(
    db: Session, workspace: Workspace, f: Filters, mode: CompareMode
) -> dict[str, Any]:
    ws = workspace.id
    rng = resolve_compare(f.date_from, f.date_to, mode)
    prev_f = f.with_range(*rng) if rng else None
    perf = products.product_perf(db, ws, f)
    prev_perf = products.product_perf(db, ws, prev_f) if prev_f else None
    usable_prev = prev_perf if prev_perf and sum(p.net for p in prev_perf) > 0 else None
    products.attach_previous(perf, usable_prev)
    items = products.classify(perf)

    totals, _ = q.build_totals(db, ws, f)
    prev_totals, _ = q.build_totals(db, ws, prev_f) if prev_f else (None, None)
    vals = metric_values(totals)
    meta, warnings = _meta(
        db, workspace, f, mode, prev_f, pick_granularity(f.days), totals, prev_totals, vals,
        ["net_sales", "gross_profit", "gross_margin", "discount_rate"],
    )  # fmt: skip
    if not items:
        warnings.append("No products sold in this period.")
    elif all(i["margin_pct"] is None for i in items):
        warnings.append("No product has a cost recorded, so margins and quadrants are unavailable.")
    gross = sum((p.gross for p in perf), ZERO)
    discount = sum((p.discount for p in perf), ZERO)
    overall_discount = products.pct(discount, gross)
    return {
        "meta": meta,
        "overall_margin_pct": products.overall_margin(perf),
        "overall_discount_rate": overall_discount,
        "items": items,
        "categories": products.by_category(perf),
        "portfolio": products.portfolio_summary(items),
        "warnings": warnings,
    }


def products_csv(items: list[dict[str, Any]]) -> Iterator[str]:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["sku", "product", "category", "units", "net_sales", "share_pct", "abc", "quadrant",
         "margin_pct", "margin_amount", "discount_rate_pct", "cost_coverage_pct",
         "previous_net_sales", "change_pct", "flags"]
    )  # fmt: skip
    yield buf.getvalue()
    for i in items:
        buf.seek(0)
        buf.truncate()
        w.writerow(
            [i["key"], i["name"], i["category"] or "", i["units"], i["net"], i["share"], i["abc"],
             i["quadrant"], i["margin_pct"] or "", i["margin_amount"] or "",
             i["discount_rate"] or "", i["cost_coverage_pct"] or "",
             i["previous_net"] if i["previous_net"] is not None else "",
             i["change_pct"] if i["change_pct"] is not None else "", " ".join(i["flags"])]
        )  # fmt: skip
        yield buf.getvalue()


def basket_overview(
    db: Session, workspace: Workspace, f: Filters, min_orders: int, limit: int
) -> dict[str, Any]:
    totals, _ = q.build_totals(db, workspace.id, f)
    meta, _ = _meta(
        db, workspace, f, "none", None, pick_granularity(f.days), totals, None,
        metric_values(totals), ["orders"],
    )  # fmt: skip
    data = basket.basket_pairs(db, workspace.id, f, min_orders=min_orders, limit=limit)
    return {
        "meta": meta,
        **data,
        "note": (
            "Products appear together more often than chance when lift is above 1. "
            "This shows association, not that one product causes the purchase of the other."
        ),
    }
