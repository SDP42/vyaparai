"""The numbers behind an answer, listed with where each one comes from.

Shown beside every reply so an owner can check the claim: each line names the metric or service
that produced it. Built from the tool result only.
"""

from typing import Any

from app.services.assistant import tools
from app.services.assistant.tools import inr, pct


def _span(f: dict[str, Any]) -> str:
    a, b = f["start"], f["end"]
    return f"{a:%d %b %Y}" if a == b else f"{a:%d %b} – {b:%d %b %Y}"


def build(intent: str, r: tools.Result) -> list[dict[str, str]]:
    f = r.facts
    e: list[tuple[str, str, str]] = []
    if intent == "sales":
        e = [("Period", _span(f), "date range used"), ("Net sales", inr(f["net_sales"]), "metric:net_sales@v1"),
             ("Orders", str(int(f["orders"])), "metric:orders@v1"), ("Average order", inr(f["aov"]), "metric:aov@v1"),
             ("Change vs previous period", pct(f["net_sales"] and f["net_change_pct"]), "metric comparison")]  # fmt: skip
    elif intent == "why":
        e = [("Period", _span(f), "date range used"), ("Net sales now", inr(f["now"]), "metric:net_sales@v1"),
             ("Net sales before", inr(f["before"]), "metric:net_sales@v1")]  # fmt: skip
        e += [(x["label"], inr(x["amount"]), "drivers:price_volume_mix") for x in f["effects"]]
    elif intent in {"top_products", "slow_products"}:
        e = [("Period", _span(f), "date range used")] + [
            (x["name"], f"{x['net']} · {x['units']} units", "products:net_sales") for x in r.rows
        ]
    elif intent == "customers":
        e = [("Customers", str(f["customers"]), "customers:summary"), ("Repeat rate", f"{float(f['repeat_rate']):.0f}%", "customers:summary"),
             ("Regulars gone quiet", str(f["lapsed_regulars"]), "customers:lapse 45 days"), ("Data up to", str(f["as_of"]), "latest sale")]  # fmt: skip
    elif intent == "stock":
        e = [("Run out before a new order", str(f["urgent"]), "inventory:cover vs lead time"), ("Order soon", str(f["reorder"]), "inventory:cover"),
             ("Suggested order value", inr(f["order_cost"]), "inventory:order list")]  # fmt: skip
    elif intent == "dead_stock":
        e = [
            ("Dead stock", str(f["dead"]), "inventory:30 days no sales"),
            ("Cash in dead stock", inr(f["dead_cash"]), "stock x unit cost"),
        ]
    elif intent == "forecast":
        e = [("Next units", f"{f['units_next']:.0f} ({f['low']:.0f}-{f['high']:.0f})", f"forecast run as of {f['as_of']}"),
             ("Next net sales", inr(f["net_next"]), "forecast x net price"), ("Past error (WAPE)", f"{float(f['wape']) * 100:.0f}%", "backtest")]  # fmt: skip
    elif intent == "alerts":
        e = [
            ("Open alerts", str(f["count"]), "alerts"),
            ("Need attention", str(f["high"]), "alerts"),
            ("Worth a look", str(f["medium"]), "alerts"),
        ]
    elif intent == "margin":
        e = [("Period", _span(f), "date range used"), ("Gross margin", f"{float(f['margin_pct']):.1f}%", "metric:gross_margin@v1"), ("Margin leaks", str(f["leaks"]), "costs:leaks")]  # fmt: skip
    elif intent == "udhaar":
        e = [("Total owed", inr(f["outstanding"]), "udhaar:ledger"), ("Older than 30 days", inr(f["overdue"]), "udhaar:FIFO ageing"), ("People owing", str(f["parties"]), "udhaar:ledger")]  # fmt: skip
    elif intent == "recommend":
        e = [("Suggestions waiting", str(f["count"]), "recommendations")] + [
            (x["title"][:70], x["impact"], "recommendations:impact estimate") for x in r.rows
        ]
    elif intent == "product_sales":
        e = [("Product", f["name"], "product match"), ("Period", _span(f), "date range used"), ("Net sales", inr(f["net_sales"]), "metric:net_sales@v1 (filtered to product)"),
             ("Units", f"{float(f['units']):.0f}", "metric:units@v1"), ("Gross margin", f"{float(f['margin']):.1f}%" if f["margin"] is not None else "–", "metric:gross_margin@v1")]  # fmt: skip
    elif intent == "product_stock":
        e = [("Product", f["name"], "product match"), ("Days of cover", "–" if f["cover_days"] is None else str(f["cover_days"]), "inventory:cover"),
             ("Status", str(f["status"]), "inventory:plan"), ("Suggested order", str(f["order_qty"]), "inventory:order qty")]  # fmt: skip
    elif intent == "product_forecast":
        e = [("Product", f["name"], "product match"), ("Next units", f"{f['units_next']:.0f} ({f['low']:.0f}-{f['high']:.0f})", "forecast"),
             ("Model confidence", str(f["confidence"]), "backtest")]  # fmt: skip
    return [{"label": a, "value": b, "source": c} for a, b, c in e]
