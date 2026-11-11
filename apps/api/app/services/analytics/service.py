"""Builds the analytics API responses from the query layer, the registry and the driver maths."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.workspace import Workspace
from app.services.analytics import queries as q
from app.services.analytics.compare import (
    bucket_start,
    change,
    compare_label,
    default_range,
    pick_granularity,
    resolve_compare,
)
from app.services.analytics.drivers import DriverResult, price_volume_mix
from app.services.analytics.insights import build_insights
from app.services.analytics.metrics import (
    BY_KEY,
    HEADLINE_KEYS,
    METRICS,
    REGISTRY_VERSION,
    SECONDARY_KEYS,
    versions,
)
from app.services.analytics.text import pct
from app.services.analytics.types import (
    UNSPECIFIED,
    ZERO,
    CompareMode,
    Dimension,
    Filters,
    Granularity,
    ProductAgg,
    Totals,
    metric_values,
    money,
)

MAX_RANGE_DAYS = 1100
ASSUMPTIONS = [
    "Only completed orders count; cancelled, pending and returned orders are excluded "
    "and reported.",
    "Unit prices are assumed to exclude GST; GST and shipping are never part of net sales.",
    "Days are the business day in the workspace timezone.",
    "Gross profit uses only lines that have a cost; see cost coverage.",
]
METHOD = (
    "Volume, mix and price are computed on products sold in both periods (price-volume-mix on "
    "gross revenue). Products sold in only one period are shown as 'new & discontinued', and "
    "discounts as their own effect. The effects add up to the change in net sales."
)
CAVEAT = "Attributions describe how the numbers changed, not why customers behaved as they did."
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class BadRangeError(AppError):
    status_code = 422
    code = "invalid_range"


# ------------------------------------------------------------------ registry & options


def registry() -> dict[str, Any]:
    return {
        "registry_version": REGISTRY_VERSION,
        "eligibility": "Orders with status 'completed'",
        "assumptions": ASSUMPTIONS,
        "metrics": [
            {
                "key": m.key,
                "label": m.label,
                "unit": m.unit,
                "version": m.version,
                "definition": m.definition,
                "includes": m.includes,
                "excludes": m.excludes,
                "good_direction": m.good_direction,
            }
            for m in METRICS
        ],
    }


def resolve_filters(
    db: Session,
    ws: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    *,
    categories: list[str] | None = None,
    channels: list[str] | None = None,
    regions: list[str] | None = None,
    skus: list[str] | None = None,
) -> Filters:
    first, last = q.workspace_bounds(db, ws)
    d_from, d_to = default_range(last, datetime.now(UTC).date())
    if date_from and date_to:
        d_from, d_to = date_from, date_to
    elif date_to:
        d_to, d_from = date_to, date_to - timedelta(days=29)
    elif date_from:
        d_from, d_to = date_from, date_from + timedelta(days=29)
    if d_from > d_to:
        raise BadRangeError("'from' must be on or before 'to'")
    if (d_to - d_from).days + 1 > MAX_RANGE_DAYS:
        raise BadRangeError(f"The range is limited to {MAX_RANGE_DAYS} days")
    _ = first
    return Filters(
        d_from,
        d_to,
        tuple(categories or ()),
        tuple(channels or ()),
        tuple(regions or ()),
        tuple(skus or ()),
    )


def filter_options(db: Session, workspace: Workspace) -> dict[str, Any]:
    first, last = q.workspace_bounds(db, workspace.id)
    d_from, d_to = default_range(last, datetime.now(UTC).date())
    return {
        **q.filter_options(db, workspace.id),
        "first_order_date": first,
        "last_order_date": last,
        "default_from": d_from,
        "default_to": d_to,
        "has_data": last is not None,
    }


# ------------------------------------------------------------------ pieces


def _kpi(
    key: str, cur: dict[str, Decimal | None], prev: dict[str, Decimal | None] | None
) -> dict[str, Any]:
    m = BY_KEY[key]
    c = cur[key]
    p = prev[key] if prev is not None else None
    delta, rel = change(m, c, p)
    return {
        "key": key,
        "label": m.label,
        "unit": m.unit,
        "version": m.version,
        "value": c,
        "previous": p,
        "change": delta,
        "change_pct": rel,
        "good_direction": m.good_direction,
        "compare_in_points": m.compare_in_points,
    }


def _bucket_series(
    db: Session, ws: uuid.UUID, f: Filters, granularity: str
) -> list[dict[str, Any]]:
    days = q.fill_days(q.daily(db, ws, f), f.date_from, f.date_to)
    buckets: dict[date, dict[str, Any]] = {}
    for d, agg in days:
        start = bucket_start(d, granularity)
        b = buckets.setdefault(start, {"start": start, "net": ZERO, "orders": 0, "units": ZERO})
        b["net"] += agg.net
        b["orders"] += agg.orders
        b["units"] += agg.units
    out = []
    for start, b in buckets.items():
        if granularity == "month":
            label = f"{start:%b %Y}"
        elif granularity == "week":
            label = f"Week of {start.day} {start:%b}"
        else:
            label = f"{start.day} {start:%b}"
        b["label"] = label
        b["aov"] = money(b["net"] / b["orders"]) if b["orders"] else None
        out.append(b)
    return out


def _trend(
    db: Session, ws: uuid.UUID, f: Filters, prev_f: Filters | None, granularity: str
) -> list[dict[str, Any]]:
    cur = _bucket_series(db, ws, f, granularity)
    prev = _bucket_series(db, ws, prev_f, granularity) if prev_f else []
    for i, b in enumerate(cur):
        b["previous_net"] = prev[i]["net"] if i < len(prev) else None
        b["previous_label"] = prev[i]["label"] if i < len(prev) else None
    return cur


def _weekday(db: Session, ws: uuid.UUID, f: Filters) -> list[dict[str, Any]]:
    sums = [ZERO] * 7
    counts = [0] * 7
    for d, agg in q.fill_days(q.daily(db, ws, f), f.date_from, f.date_to):
        sums[d.weekday()] += agg.net
        counts[d.weekday()] += 1
    return [
        {
            "weekday": i,
            "label": WEEKDAYS[i],
            "avg_net": money(sums[i] / counts[i]) if counts[i] else ZERO,
            "days": counts[i],
        }
        for i in range(7)
    ]


def _product_rows(
    products: list[ProductAgg], previous: list[ProductAgg] | None, *, reverse: bool, limit: int
) -> list[dict[str, Any]]:
    prev = {p.product_id: p for p in (previous or [])}
    ranked = sorted(products, key=lambda p: p.net, reverse=reverse)[:limit]
    return [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "net": money(p.net),
            "previous_net": money(prev[p.product_id].net)
            if previous is not None and p.product_id in prev
            else (ZERO if previous is not None else None),
            "delta": (
                money(p.net) - (money(prev[p.product_id].net) if p.product_id in prev else ZERO)
            )
            if previous is not None
            else None,
            "units": p.units,
            "previous_units": (prev[p.product_id].units if p.product_id in prev else ZERO)
            if previous is not None
            else None,
        }
        for p in ranked
    ]


def _meta(
    db: Session,
    workspace: Workspace,
    f: Filters,
    mode: CompareMode,
    prev_f: Filters | None,
    granularity: str,
    cur_totals: Totals,
    prev_totals: Totals | None,
    cur_vals: dict[str, Decimal | None],
    keys: list[str],
) -> tuple[dict[str, Any], list[str]]:
    first, last = q.workspace_bounds(db, workspace.id)
    excluded = q.excluded_orders_by_status(db, workspace.id, f)
    warnings: list[str] = []
    if last is None:
        warnings.append("No sales data has been imported yet.")
    else:
        if cur_totals.days_with_data == 0:
            warnings.append("There are no completed orders in the selected period.")
        elif cur_totals.days_with_data < f.days:
            warnings.append(
                f"Only {cur_totals.days_with_data} of {f.days} days in this period have sales."
            )
        if first and f.date_from < first:
            warnings.append(f"Your data starts on {first:%d %b %Y}; earlier days are empty.")
    if prev_f is not None and prev_totals is not None:
        if prev_totals.days_with_data == 0:
            warnings.append("The comparison period has no sales, so changes cannot be calculated.")
        elif prev_totals.days_with_data < prev_f.days:
            warnings.append(
                f"The comparison period has sales on only {prev_totals.days_with_data} of "
                f"{prev_f.days} days."
            )
    cov = cur_vals["cost_coverage"]
    if cov is not None and cov < 95:
        warnings.append(
            f"Only {pct(cov, signed=False)} of net sales has a cost, "
            "so gross profit is understated."
        )
    if excluded:
        total = sum(excluded.values())
        parts = ", ".join(f"{n} {s}" for s, n in sorted(excluded.items()))
        warnings.append(f"{total} orders in this period are not counted ({parts}).")

    meta = {
        "currency": workspace.currency,
        "timezone": workspace.timezone,
        "has_data": last is not None,
        "period": {"date_from": f.date_from, "date_to": f.date_to, "days": f.days},
        "compare": (
            {
                "mode": mode,
                "label": compare_label(mode),
                "date_from": prev_f.date_from,
                "date_to": prev_f.date_to,
                "days": prev_f.days,
            }
            if prev_f is not None and mode != "none"
            else None
        ),
        "granularity": granularity,
        "filters": f.as_dict(),
        "metric_versions": versions(keys),
        "freshness": {
            "last_order_date": last,
            "first_order_date": first,
            "last_import_at": q.last_import_at(db, workspace.id),
        },
        "coverage": {
            "days_in_period": f.days,
            "days_with_data": cur_totals.days_with_data,
            "compare_days_with_data": prev_totals.days_with_data if prev_totals else None,
            "cost_coverage_pct": cov,
            "excluded_orders_by_status": excluded,
            "anonymous_order_share": cur_vals["anonymous_order_share"],
        },
    }
    return meta, warnings


# ------------------------------------------------------------------ public API


def overview(
    db: Session,
    workspace: Workspace,
    f: Filters,
    mode: CompareMode = "previous_period",
    granularity: Granularity | None = None,
) -> dict[str, Any]:
    ws = workspace.id
    gran = granularity or pick_granularity(f.days)
    rng = resolve_compare(f.date_from, f.date_to, mode)
    prev_f = f.with_range(*rng) if rng else None

    cur_totals, cur_products = q.build_totals(db, ws, f)
    prev_totals, prev_products = q.build_totals(db, ws, prev_f) if prev_f else (None, None)
    cur_vals = metric_values(cur_totals)
    prev_vals = metric_values(prev_totals) if prev_totals else None

    cat_cur = q.breakdown(db, ws, f, "category")
    cat_prev = q.breakdown(db, ws, prev_f, "category") if prev_f else None
    category_mix = q.merge_breakdowns(cat_cur, cat_prev)
    channel_mix = q.merge_breakdowns(
        q.breakdown(db, ws, f, "channel"),
        q.breakdown(db, ws, prev_f, "channel") if prev_f else None,
    )
    region_mix = q.merge_breakdowns(
        q.breakdown(db, ws, f, "region"), q.breakdown(db, ws, prev_f, "region") if prev_f else None
    )

    drivers: DriverResult | None = (
        price_volume_mix(cur_products, prev_products or [])
        if prev_f and prev_totals and prev_totals.days_with_data
        else None
    )
    insights = build_insights(
        current=cur_vals,
        previous=prev_vals if prev_totals and prev_totals.days_with_data else None,
        compare_label=compare_label(mode) if prev_f else None,
        drivers=drivers,
        category_mix=category_mix,
        days_in_period=f.days,
    )

    keys = [*HEADLINE_KEYS, *SECONDARY_KEYS]
    meta, warnings = _meta(
        db, workspace, f, mode, prev_f, gran, cur_totals, prev_totals, cur_vals, keys
    )
    have_prev = prev_vals if prev_totals and prev_totals.days_with_data else None
    return {
        "meta": meta,
        "headline": [_kpi(k, cur_vals, have_prev) for k in HEADLINE_KEYS],
        "secondary": [_kpi(k, cur_vals, have_prev) for k in SECONDARY_KEYS],
        "trend": _trend(db, ws, f, prev_f, gran),
        "category_mix": category_mix,
        "channel_mix": channel_mix,
        "region_mix": region_mix,
        "weekday": _weekday(db, ws, f),
        "top_products": _product_rows(cur_products, prev_products, reverse=True, limit=8),
        "bottom_products": _product_rows(cur_products, prev_products, reverse=False, limit=5),
        "insights": insights,
        "warnings": warnings,
    }


def drivers(
    db: Session,
    workspace: Workspace,
    f: Filters,
    mode: CompareMode = "previous_period",
    by: Dimension = "category",
) -> dict[str, Any]:
    ws = workspace.id
    rng = resolve_compare(f.date_from, f.date_to, mode)
    prev_f = f.with_range(*rng) if rng else None
    cur_totals, cur_products = q.build_totals(db, ws, f)
    prev_totals, prev_products = q.build_totals(db, ws, prev_f) if prev_f else (None, None)
    cur_vals = metric_values(cur_totals)
    usable = bool(prev_f and prev_totals and prev_totals.days_with_data)

    result = price_volume_mix(cur_products, prev_products or []) if usable else None
    contributions = q.merge_breakdowns(
        q.breakdown(db, ws, f, by), q.breakdown(db, ws, prev_f, by) if prev_f else None
    )
    cat_mix = (
        contributions
        if by == "category"
        else q.merge_breakdowns(
            q.breakdown(db, ws, f, "category"),
            q.breakdown(db, ws, prev_f, "category") if prev_f else None,
        )
    )
    insights = build_insights(
        current=cur_vals,
        previous=metric_values(prev_totals) if usable and prev_totals else None,
        compare_label=compare_label(mode) if prev_f else None,
        drivers=result,
        category_mix=cat_mix,
        days_in_period=f.days,
    )
    meta, warnings = _meta(
        db,
        workspace,
        f,
        mode,
        prev_f,
        pick_granularity(f.days),
        cur_totals,
        prev_totals,
        cur_vals,
        ["net_sales"],
    )

    def move(m: Any) -> dict[str, Any]:
        return {
            "sku": m.sku,
            "name": m.name,
            "category": m.category,
            "units_prev": m.units_prev,
            "units_cur": m.units_cur,
            "net_prev": m.net_prev,
            "net_cur": m.net_cur,
            "delta": m.delta,
        }

    moves = result.moves if result else []
    return {
        "meta": meta,
        "net_sales_current": money(cur_totals.net),
        "net_sales_previous": money(prev_totals.net) if usable and prev_totals else None,
        "net_change": result.net_change if result else None,
        "effects": [
            {"key": e.key, "label": e.label, "amount": e.amount, "explanation": e.explanation}
            for e in (result.effects if result else [])
        ],
        "method": METHOD,
        "caveat": CAVEAT,
        "contributions": contributions,
        "contribution_dimension": by,
        "biggest_decliners": [move(m) for m in moves[:5] if m.delta < 0],
        "biggest_gainers": [move(m) for m in reversed(moves[-5:]) if m.delta > 0],
        "continuing_products": result.continuing_products if result else 0,
        "new_products": result.new_products if result else 0,
        "discontinued_products": result.discontinued_products if result else 0,
        "insights": insights,
        "warnings": warnings,
    }


def transactions(
    db: Session,
    workspace: Workspace,
    f: Filters,
    *,
    limit: int,
    offset: int,
    search: str | None,
) -> dict[str, Any]:
    totals, _ = q.build_totals(db, workspace.id, f)
    rows, total, net = q.transactions(
        db, workspace.id, f, limit=limit, offset=offset, search=search
    )
    meta, _ = _meta(
        db,
        workspace,
        f,
        "none",
        None,
        pick_granularity(f.days),
        totals,
        None,
        metric_values(totals),
        ["net_sales"],
    )
    return {
        "meta": meta,
        "total_lines": total,
        "total_net": net,
        "limit": limit,
        "offset": offset,
        "items": rows,
    }


def staff(db: Session, ws: Workspace, f: Filters, only: str | None = None) -> dict[str, Any]:
    """Sales by cashier or salesperson. `only` keeps one person (counter staff: their own)."""
    rows = q.per_staff(db, ws.id, f)
    named = [r for r in rows if r["staff"] != UNSPECIFIED]
    if only is not None:
        rows = [r for r in rows if r["staff"].casefold() == only.casefold()]
    return {
        "meta": {"date_from": f.date_from, "date_to": f.date_to},
        "has_staff": bool(named),
        "rows": rows,
        "note": None
        if named
        else "No bills carry a cashier or salesperson name. Map that column when you import.",
    }
