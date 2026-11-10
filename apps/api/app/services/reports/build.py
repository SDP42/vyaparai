"""Collect a business summary from the existing services. Every number comes from them; none is computed here."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.services import alerts as alert_service
from app.services import credit, inventory
from app.services.agents.engine import jsonable
from app.services.analytics import intelligence
from app.services.analytics import queries as q
from app.services.analytics import service as analytics
from app.services.forecasting import service as forecasting
from app.services.recommend import service as recommend


def build(
    db: Session, workspace: Workspace, start: date | None, end: date | None
) -> dict[str, Any]:
    ws = workspace.id
    first, last = q.workspace_bounds(db, ws)
    if first is None or last is None:
        raise ValueError("No sales have been imported yet")
    if start and end:  # trim to the days that have data so empty days do not look like a collapse
        ca, cb = max(start, first), min(end, last)
        start, end = (ca, cb) if ca <= cb else (None, None)
    f = analytics.resolve_filters(db, ws, start, end)
    ov = analytics.overview(db, workspace, f, "previous_period")
    dr = analytics.drivers(db, workspace, f, "previous_period")
    prod = intelligence.products_overview(db, workspace, f, "previous_period")
    cust = intelligence.customers_summary(db, workspace, f.date_to, 365, 30, 30, 45)
    inv = inventory.overview(db, workspace)
    ud = credit.summary(db, ws, datetime.now(UTC).date())
    run = forecasting.latest_run(db, ws)
    fc = None
    if run is not None:
        o = forecasting.overview(db, workspace, run)
        fc = {"as_of": run.as_of, "horizon": run.horizon, "kpis": o["kpis"], "wape": o["accuracy"]["wape"], "stale": o["stale"],
              "risers": o["risers"][:3], "fallers": o["fallers"][:3], "warnings": o["warnings"][:3]}  # fmt: skip
    recs = recommend.listing(db, ws, "proposed")[:5] + recommend.listing(db, ws, "approved")[:5]
    kpis = [
        {"key": k["key"], "label": k["label"], "unit": k["unit"], "value": k["value"], "previous": k["previous"], "change_pct": k["change_pct"]}
        for k in ov["headline"] + ov["secondary"]
    ]  # fmt: skip
    out: dict[str, Any] = jsonable({
        "shop": workspace.name, "currency": workspace.currency,
        "period": {"from": f.date_from, "to": f.date_to, "compare": ov["meta"].get("compare")},
        "generated_at": datetime.now(UTC), "data_through": last,
        "kpis": kpis,
        "trend": [t["net"] for t in ov["trend"]],
        "drivers": {"net_change": dr["net_change"], "effects": [{"label": e["label"], "amount": e["amount"]} for e in dr["effects"]],
                    "decliners": dr["biggest_decliners"][:5], "gainers": dr["biggest_gainers"][:5]},
        "products": {"top": [{"name": i["name"], "units": i["units"], "net": i["net"], "margin_pct": i.get("margin_pct")} for i in prod["items"][:8]],
                     "bottom": [{"name": i["name"], "units": i["units"], "net": i["net"]} for i in sorted(prod["items"], key=lambda x: float(x["net"]))[:5]]},
        "customers": {"customers": cust["customers"], "repeat_rate": cust["repeat_rate"], "lapsed_regulars": cust["lapsed_regulars"],
                      "segments": [{"segment": s["segment"], "customers": s.get("customers"), "net": s.get("net")} for s in cust["segments"]]},
        "stock": inv["summary"] if inv["summary"]["tracked"] else None,
        "udhaar": ud if ud["has_data"] else None,
        "forecast": fc,
        "alerts": alert_service.counts(db, ws),
        "recommendations": [{"title": r.title, "status": r.status, "impact": r.impact, "effort": r.effort, "confidence": r.confidence, "why": r.why} for r in recs],
        "warnings": ov["warnings"] + prod["warnings"],
        "limits": [
            "Numbers come from the data imported into this workspace; anything not imported is not here.",
            "Impact figures for recommendations are estimates with stated assumptions, not promises.",
            "Forecasts carry an error shown beside them; past accuracy does not guarantee future accuracy.",
        ],
    })  # fmt: skip
    return out
