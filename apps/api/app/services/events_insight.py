"""Events for one shop: what is coming, which of its products it touches, and what past events did."""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commerce import Order, OrderItem, OrderStatus, Product
from app.models.workspace import Workspace
from app.services import events, inventory, weather
from app.services.analytics import queries as q
from app.services.analytics.queries import LINE_NET

D = Decimal
MIN_BASELINE_DAYS = 21  # days with sales needed in the 28 days before an event to judge its effect
MIN_WINDOW_DAYS = 3


def region_of(workspace: Workspace) -> tuple[frozenset[str], str | None]:
    """(zones, state) from the shop's city, when it was chosen from the list."""
    city = weather.find_city(workspace.city or "")
    state = workspace.state or (city[1] if city else None)
    return events.zones_for(state), state


def _status(e: events.Event, today: date) -> str:
    if today < e.start - timedelta(days=e.lead):
        return "ahead"
    if today < e.start:
        return "ramping"
    if today <= e.end:
        return "on"
    return "fading"


def calendar(
    workspace: Workspace, start: date, end: date, *, include_cricket: bool, tier_max: int
) -> list[events.Event]:
    zones, state = region_of(workspace)
    out = []
    for e in events.relevant(zones, state):
        lo, hi = events.window(e)
        if hi < start or lo > end or e.tier > tier_max:
            continue
        if e.category == "cricket" and not include_cricket:
            continue
        out.append(e)
    return out


def _sales_by_product(
    db: Session, ws: uuid.UUID, start: date, end: date
) -> dict[str, dict[date, Decimal]]:
    stmt = (
        select(Product.sku, Order.business_date, func.sum(LINE_NET))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.workspace_id == ws, Order.workspace_id == ws, Order.status == OrderStatus.COMPLETED,
               Order.business_date >= start, Order.business_date <= end)
        .group_by(Product.sku, Order.business_date)
    )  # fmt: skip
    out: dict[str, dict[date, Decimal]] = defaultdict(dict)
    for sku, day, net in db.execute(stmt):
        out[sku][day] = D(str(net))
    return out


def _lift(
    sales: dict[str, dict[date, Decimal]],
    skus: set[str],
    lo: date,
    hi: date,
    first: date,
    last: date,
) -> dict[str, Any] | None:
    """Average daily sales in the window against the 28 days before it, for the given products."""
    base_lo, base_hi = lo - timedelta(days=28), lo - timedelta(days=1)
    if hi > last or base_lo < first:
        return None
    base_days = {d for s in skus for d in sales.get(s, {}) if base_lo <= d <= base_hi}
    win_days = {d for s in skus for d in sales.get(s, {}) if lo <= d <= hi}
    if len(base_days) < MIN_BASELINE_DAYS or len(win_days) < MIN_WINDOW_DAYS:
        return None
    base = (
        sum((v for s in skus for d, v in sales.get(s, {}).items() if base_lo <= d <= base_hi), D(0))
        / 28
    )
    cur = sum((v for s in skus for d, v in sales.get(s, {}).items() if lo <= d <= hi), D(0)) / (
        (hi - lo).days + 1
    )
    if base <= 0:
        return None
    return {
        "ratio": float(cur / base),
        "baseline_per_day": float(base),
        "window_per_day": float(cur),
    }


def observed_effects(
    db: Session, workspace: Workspace, *, tier_max: int = 2
) -> list[dict[str, Any]]:
    """What each past event did to this shop's sales (all products, and the products it touches)."""
    first, last = q.workspace_bounds(db, workspace.id)
    if first is None or last is None:
        return []
    sales = _sales_by_product(db, workspace.id, first, last)
    products = {
        p.sku: p for p in db.scalars(select(Product).where(Product.workspace_id == workspace.id))
    }
    all_skus = set(sales)
    zones, state = region_of(workspace)
    out: list[dict[str, Any]] = []
    for e in events.relevant(zones, state):
        if e.tier > tier_max or e.category == "cricket" or e.end >= last:
            continue
        lo, hi = events.window(e)
        if hi < first:
            continue
        matched = {
            s
            for s in all_skus
            if s in products
            and events.demand_categories(products[s].name, products[s].category) & set(e.demand)
        }
        out.append(
            {
                "id": e.id, "name": e.name, "start": e.start, "end": e.end, "tier": e.tier,
                "all_products": _lift(sales, all_skus, lo, hi, first, last),
                "matching_products": _lift(sales, matched, lo, hi, first, last) if matched else None,
                "matching_count": len(matched),
            }
        )  # fmt: skip
    return sorted(out, key=lambda r: r["start"], reverse=True)


def upcoming(
    db: Session,
    workspace: Workspace,
    *,
    days: int,
    include_cricket: bool,
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    evs = calendar(
        workspace, today, today + timedelta(days=days), include_cricket=include_cricket, tier_max=3
    )
    if not evs:
        return []
    _, last = q.workspace_bounds(db, workspace.id)
    products = {
        p.sku: p for p in db.scalars(select(Product).where(Product.workspace_id == workspace.id))
    }
    sales = _sales_by_product(db, workspace.id, last - timedelta(days=27), last) if last else {}
    daily = {sku: float(sum(v.values(), D(0)) / 28) for sku, v in sales.items()}
    stock = {i["sku"]: i for i in inventory.overview(db, workspace)["items"]}
    effects = {r["name"]: r for r in observed_effects(db, workspace)}
    out: list[dict[str, Any]] = []
    for e in evs:
        matched = [
            s for s in products
            if s in daily and events.demand_categories(products[s].name, products[s].category) & set(e.demand)
        ]  # fmt: skip
        top = sorted(matched, key=lambda s: -daily[s])[:6]
        need_until = (e.end - today).days + 1
        plist = []
        for s in top:
            st = stock.get(s)
            cover = float(st["cover_days"]) if st and st["cover_days"] is not None else None
            plist.append(
                {
                    "sku": s,
                    "name": products[s].name,
                    "daily_sales": round(daily[s], 2),
                    "cover_days": cover,
                    "tracked": st is not None,
                    "at_risk": bool(
                        cover is not None and e.tier <= 2 and cover < max(need_until, 1)
                    ),
                }
            )
        eff = effects.get(e.name)
        out.append(
            {
                "event": e, "days_until": (e.start - today).days, "status": _status(e, today),
                "matching_products": len(matched), "products": plist,
                "last_time": None if eff is None else {"year": eff["start"].year, "all": eff["all_products"], "matching": eff["matching_products"]},
            }
        )  # fmt: skip
    out.sort(key=lambda r: (r["event"].start, r["event"].id))
    return out
