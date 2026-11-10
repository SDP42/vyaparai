"""Goals: pace, projection and status; and benchmarks against the shop's own history.

Cumulative measures (net sales, orders, gross profit) are tracked against the share of the period gone:
- pace    = progress / expected progress at this point (1.0 means exactly on pace);
- projection = so far + a simulated rest of the period drawn from the last 28 days of actual daily values
  (1,000 resamples, 10th to 90th percentile), so the range shows how uncertain the finish is.
Rate measures (gross margin, order value, discount rate) and udhaar owed are compared with the target as they stand.

Status: achieved, on_track (the low end of the projection still reaches it), at_risk (it might), behind (even the
high end falls short), missed or met (the period is over). At-most goals mirror this.

Benchmarks: no peer data exists in the product, so benchmarks are the shop's own: the same measure over past
periods of the same length (median, best, a stretch). Peer ranges would need an opt-in sharing network with
anonymity rules; that is not built (docs/GOALS.md).
"""

import uuid
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.commerce import Order, OrderItem, OrderStatus
from app.models.goal import Goal
from app.models.workspace import Workspace
from app.services import audit, credit
from app.services.analytics import queries as q
from app.services.analytics import service as analytics

METRICS: dict[str, dict[str, Any]] = {
    "net_sales": {
        "label": "Net sales",
        "unit": "inr",
        "kind": "cumulative",
        "direction": "at_least",
    },
    "orders": {"label": "Orders", "unit": "count", "kind": "cumulative", "direction": "at_least"},
    "gross_profit": {
        "label": "Gross profit",
        "unit": "inr",
        "kind": "cumulative",
        "direction": "at_least",
    },
    "gross_margin": {
        "label": "Gross margin",
        "unit": "percent",
        "kind": "rate",
        "direction": "at_least",
    },
    "aov": {"label": "Average order value", "unit": "inr", "kind": "rate", "direction": "at_least"},
    "discount_rate": {
        "label": "Discount rate",
        "unit": "percent",
        "kind": "rate",
        "direction": "at_most",
    },
    "udhaar_overdue": {
        "label": "Udhaar older than 30 days",
        "unit": "inr",
        "kind": "point",
        "direction": "at_most",
    },
}
HISTORY_DAYS = 28


# ------------------------------------------------------------------ periods


def month_bounds(d: date) -> tuple[date, date]:
    return d.replace(day=1), d.replace(day=monthrange(d.year, d.month)[1])


def week_bounds(d: date) -> tuple[date, date]:
    s = d - timedelta(days=d.weekday())
    return s, s + timedelta(days=6)


def period_for(kind: str, today: date) -> tuple[date, date]:
    return month_bounds(today) if kind == "month" else week_bounds(today)


# ------------------------------------------------------------------ data


def daily_series(
    db: Session, ws: uuid.UUID, metric: str, start: date, end: date
) -> dict[date, float]:
    net = OrderItem.quantity * OrderItem.unit_price - OrderItem.discount_amount
    base = (
        OrderItem.workspace_id == ws,
        Order.status == OrderStatus.COMPLETED,
        Order.business_date >= start,
        Order.business_date <= end,
    )
    stmt: Any
    if metric == "orders":
        stmt = (
            select(Order.business_date, func.count(func.distinct(Order.id)))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(*base)
            .group_by(Order.business_date)
        )
    elif metric == "gross_profit":
        stmt = (
            select(
                Order.business_date,
                func.sum(
                    (net - OrderItem.quantity * OrderItem.unit_cost_snapshot)
                    * (OrderItem.unit_cost_snapshot.is_not(None))
                ),
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(*base)
            .group_by(Order.business_date)
        )
    else:
        stmt = (
            select(Order.business_date, func.sum(net))
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(*base)
            .group_by(Order.business_date)
        )
    return {d: float(v or 0) for d, v in db.execute(stmt).all()}


def value_for(
    db: Session, workspace: Workspace, metric: str, start: date, end: date, today: date
) -> float | None:
    if metric == "udhaar_overdue":
        return float(credit.summary(db, workspace.id, today)["overdue"])
    f = analytics.resolve_filters(db, workspace.id, start, end)
    ov = analytics.overview(db, workspace, f, "previous_period")
    k = {x["key"]: x for x in ov["headline"] + ov["secondary"]}
    v = k.get(metric, {}).get("value")
    return None if v is None else float(v)


# ------------------------------------------------------------------ progress


def _project(
    series: dict[date, float], last: date, remaining: int, so_far: float, seed: int = 3
) -> dict[str, float]:
    days = [last - timedelta(days=i) for i in range(HISTORY_DAYS)]
    vals = np.array([series.get(d, 0.0) for d in days])
    if remaining <= 0 or len(vals) == 0:
        return {
            "low": so_far,
            "expected": so_far,
            "high": so_far,
            "recent_daily": float(vals.mean()) if len(vals) else 0.0,
        }
    rng = np.random.default_rng(seed)
    totals = rng.choice(vals, size=(1000, remaining)).sum(axis=1)
    return {
        "low": so_far + float(np.percentile(totals, 10)),
        "expected": so_far + float(vals.mean() * remaining),
        "high": so_far + float(np.percentile(totals, 90)),
        "recent_daily": float(vals.mean()),
    }


def progress(db: Session, workspace: Workspace, g: Goal, today: date) -> dict[str, Any]:
    m = METRICS[g.metric]
    first, last = q.workspace_bounds(db, workspace.id)
    out: dict[str, Any] = {"id": str(g.id), "name": g.name, "metric": g.metric, "label": m["label"], "unit": m["unit"], "kind": m["kind"], "target": g.target, "direction": g.direction,
                           "from": g.period_start.isoformat(), "to": g.period_end.isoformat(), "active": g.active}  # fmt: skip
    if last is None and g.metric != "udhaar_overdue":
        return {**out, "status": "no_data", "message": "No sales have been imported yet."}
    data_end = min(today, g.period_end, last) if last else today
    total_days = (g.period_end - g.period_start).days + 1
    elapsed = max(0, (min(data_end, g.period_end) - g.period_start).days + 1)
    over = today > g.period_end
    at_least = g.direction == "at_least"
    if g.period_start > today:
        return {**out, "status": "not_started", "message": f"Starts {g.period_start:%d %b}."}
    if g.metric != "udhaar_overdue" and (first is None or data_end < g.period_start):
        return {**out, "status": "no_data", "message": "There are no sales in this period yet."}
    value = value_for(db, workspace, g.metric, g.period_start, data_end, today)
    out |= {
        "value": value,
        "elapsed_days": elapsed,
        "total_days": total_days,
        "data_through": data_end.isoformat(),
    }
    if value is None:
        return {
            **out,
            "status": "no_data",
            "message": "This measure cannot be worked out from the data yet.",
        }
    if m["kind"] == "cumulative":
        out["progress_pct"] = round(100 * value / g.target, 1) if g.target else None
        expected_share = elapsed / total_days
        out["pace"] = (
            round((value / g.target) / expected_share, 2)
            if g.target and expected_share > 0
            else None
        )
        out["needed_per_day"] = (
            None
            if over or total_days - elapsed <= 0
            else round(max(0.0, g.target - value) / (total_days - elapsed), 2)
        )
        series = daily_series(
            db, workspace.id, g.metric, data_end - timedelta(days=HISTORY_DAYS - 1), data_end
        )
        proj = _project(series, data_end, max(0, (g.period_end - data_end).days), value)
        out["projection"] = {k: round(v, 2) for k, v in proj.items()}
        if at_least:
            if value >= g.target:
                status = "achieved" if not over else "met"
            elif over:
                status = "missed"
            elif proj["low"] >= g.target:
                status = "on_track"
            elif proj["high"] < g.target:
                status = "behind"
            else:
                status = "at_risk"
        else:  # a ceiling on a cumulative measure (rare): breached or not
            status = "behind" if value > g.target else ("met" if over else "on_track")
    else:
        out["progress_pct"] = round(100 * value / g.target, 1) if g.target else None
        ok = value >= g.target if at_least else value <= g.target
        status = ("met" if over else "on_track") if ok else ("missed" if over else "behind")
    out["status"] = status
    return out


# ------------------------------------------------------------------ CRUD


def create(
    db: Session,
    workspace: Workspace,
    user_id: uuid.UUID,
    *,
    name: str,
    metric: str,
    target: float,
    period: str,
    start: date | None,
    end: date | None,
    today: date,
) -> Goal:
    if metric not in METRICS:
        raise AppError("Unknown measure")
    if target <= 0:
        raise AppError("The target must be more than zero")
    if period == "custom":
        if not start or not end or end < start or (end - start).days > 366:
            raise AppError("Give a start and an end date, at most a year apart")
        s, e = start, end
    else:
        s, e = period_for(period, today)
    g = Goal(
        workspace_id=workspace.id,
        name=name.strip()[:120] or METRICS[metric]["label"],
        metric=metric,
        target=target,
        direction=METRICS[metric]["direction"],
        period_start=s,
        period_end=e,
        created_by_id=user_id,
    )
    db.add(g)
    audit.record(
        db,
        action="goal.created",
        actor_user_id=user_id,
        workspace_id=workspace.id,
        entity_type="goal",
        entity_id=None,
        details={"metric": metric, "target": target},
    )
    db.commit()
    return g


def get(db: Session, ws: uuid.UUID, gid: uuid.UUID) -> Goal:
    g = db.get(Goal, gid)
    if g is None or g.workspace_id != ws:
        raise NotFoundError("Goal not found")
    return g


def listing(
    db: Session, workspace: Workspace, today: date, include_closed: bool = False
) -> list[dict[str, Any]]:
    gs = db.scalars(
        select(Goal)
        .where(Goal.workspace_id == workspace.id)
        .order_by(Goal.period_end.desc(), Goal.created_at.desc())
    )
    out = [progress(db, workspace, g, today) for g in gs if g.active or include_closed]
    order = {
        "behind": 0,
        "at_risk": 1,
        "missed": 2,
        "on_track": 3,
        "achieved": 4,
        "met": 5,
        "not_started": 6,
        "no_data": 7,
    }
    return sorted(out, key=lambda x: order.get(x["status"], 9))


def close(db: Session, g: Goal, user_id: uuid.UUID) -> None:
    g.active = False
    audit.record(
        db,
        action="goal.closed",
        actor_user_id=user_id,
        workspace_id=g.workspace_id,
        entity_type="goal",
        entity_id=g.id,
    )
    db.commit()


# ------------------------------------------------------------------ benchmarks from the shop's own history


def history(
    db: Session, workspace: Workspace, metric: str, period: str, today: date, n: int = 12
) -> dict[str, Any]:
    """The same measure over the last ``n`` completed periods of the same length."""
    if metric not in METRICS or METRICS[metric]["kind"] == "point":
        raise AppError("History is not available for this measure")
    first, last = q.workspace_bounds(db, workspace.id)
    if first is None or last is None:
        return {"periods": [], "enough": False}
    cur_s, _ = period_for(period, today)
    periods = []
    s = cur_s
    for _ in range(n):
        prev_end = s - timedelta(days=1)
        s = period_for(period, prev_end)[0]
        e = prev_end
        if s < first or e > last:
            if s < first:
                break
            continue
        v = value_for(db, workspace, metric, s, e, today)
        if v is not None:
            periods.append({"from": s.isoformat(), "to": e.isoformat(), "value": v})
    vals = [p["value"] for p in periods]
    out: dict[str, Any] = {
        "metric": metric,
        "label": METRICS[metric]["label"],
        "unit": METRICS[metric]["unit"],
        "period": period,
        "periods": periods,
        "enough": len(vals) >= 3,
    }
    if len(vals) >= 3:
        arr = np.array(vals)
        at_least = METRICS[metric]["direction"] == "at_least"
        out |= {"median": float(np.median(arr)), "best": float(arr.max() if at_least else arr.min()), "worst": float(arr.min() if at_least else arr.max()),
                "steady": float(np.median(arr)), "stretch": float(np.percentile(arr, 75 if at_least else 25))}  # fmt: skip
        out["note"] = (
            f"Based on your last {len(vals)} {period}s. A steady target is your usual {period}; a stretch is your better-than-usual {period} (top quarter)."
        )
    else:
        out["note"] = "Not enough history yet: at least three past periods are needed."
    return out
