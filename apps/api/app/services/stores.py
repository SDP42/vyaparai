"""Compare the stores (workspaces) a person belongs to, side by side.

Each store keeps its own data and permissions; nothing is merged. A person sees only the stores they are a
member of. Rates (growth, margin, order value, discount) are compared, not raw sales, because a bigger shop
is not a better-run one. Each store is judged on its own latest 30 days unless a period is given, and the
period used is shown so a store with stale data is visible as such.
"""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import alerts as alert_service
from app.services import credit, inventory
from app.services import workspaces as workspace_service
from app.services.analytics import queries as q
from app.services.analytics import service as analytics

MAX_STORES = 12
SALES_DROP_PCT = -10.0
MARGIN_GAP_POINTS = 3.0


def _num(x: Any) -> float | None:
    return None if x is None else float(x)


def _store(
    db: Session, ws: Any, role: Any, start: date | None, end: date | None, today: date
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(ws.id),
        "name": ws.name,
        "city": ws.city,
        "role": role.value,
        "has_data": False,
        "flags": [],
    }
    first, last = q.workspace_bounds(db, ws.id)
    if first is None or last is None:
        out["flags"].append("No sales imported yet")
        return out
    a, b = (max(start, first), min(end, last)) if start and end else (None, None)
    f = analytics.resolve_filters(
        db, ws.id, a if a and b and a <= b else None, b if a and b and a <= b else None
    )
    ov = analytics.overview(db, ws, f, "previous_period")
    k = {x["key"]: x for x in ov["headline"] + ov["secondary"]}
    inv = inventory.overview(db, ws)["summary"]
    ud = credit.summary(db, ws.id, today)
    alerts = alert_service.counts(db, ws.id)
    out |= {
        "has_data": True, "from": f.date_from.isoformat(), "to": f.date_to.isoformat(), "latest_sale": last.isoformat(),
        "net_sales": _num(k["net_sales"]["value"]), "growth_pct": _num(k["net_sales"]["change_pct"]), "orders": _num(k["orders"]["value"]), "aov": _num(k["aov"]["value"]),
        "margin_pct": _num(k["gross_margin"]["value"]), "discount_rate": _num(k["discount_rate"]["value"]), "active_customers": _num(k["active_customers"]["value"]),
        "urgent_stock": int(inv["urgent"]) if inv["tracked"] else None, "udhaar_overdue": float(ud["overdue"]) if ud["has_data"] else None,
        "high_alerts": alerts.get("high", 0),
    }  # fmt: skip
    return out


def overview(
    db: Session, user: User, start: date | None, end: date | None, today: date
) -> dict[str, Any]:
    mine = list(workspace_service.list_for_user(db, user))[:MAX_STORES]
    stores = [_store(db, ws, role, start, end, today) for ws, role in mine]
    withdata = [s for s in stores if s["has_data"]]
    avg_margin = (
        sum(s["margin_pct"] for s in withdata if s["margin_pct"] is not None)
        / max(1, sum(1 for s in withdata if s["margin_pct"] is not None))
        if withdata
        else None
    )
    for s in withdata:
        if s["growth_pct"] is not None and s["growth_pct"] <= SALES_DROP_PCT:
            s["flags"].append(f"Sales down {abs(s['growth_pct']):.0f}% on the period before")
        if (
            avg_margin is not None
            and s["margin_pct"] is not None
            and s["margin_pct"] < avg_margin - MARGIN_GAP_POINTS
            and len(withdata) > 1
        ):
            s["flags"].append(
                f"Margin {s['margin_pct']:.1f}% is {avg_margin - s['margin_pct']:.1f} points under your stores' average"
            )
        if s["urgent_stock"]:
            s["flags"].append(
                f"{s['urgent_stock']} products will run out before a new order can arrive"
            )
        if s["udhaar_overdue"] and s["udhaar_overdue"] >= 20000:
            s["flags"].append(f"₹{int(s['udhaar_overdue']):,} of udhaar is over 30 days old")
        if s["high_alerts"]:
            s["flags"].append(f"{s['high_alerts']} alerts need attention")
    dates = {s["to"] for s in withdata}
    notes = []
    if len(dates) > 1:
        notes.append(
            "Stores have different latest sale dates, so their periods differ. Choose the same dates to compare like with like."
        )
    if len(stores) == 1:
        notes.append("You have one store. Add another to compare them.")
    total = sum(s["net_sales"] or 0 for s in withdata)
    return {
        "stores": sorted(stores, key=lambda s: (-len(s["flags"]), -(s.get("net_sales") or 0))),
        "totals": {
            "stores": len(stores),
            "net_sales": total,
            "needs_attention": sum(1 for s in stores if s["flags"]),
            "average_margin_pct": avg_margin,
        },
        "notes": notes,
        "method": "Each store is read with its own permissions. Growth is against the period of the same length before. Margins use only sales with a recorded cost.",
    }
