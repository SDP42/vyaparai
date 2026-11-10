"""Turn the product's existing signals into candidate actions.

Every candidate states how its impact was estimated and what was assumed. Where the data cannot
support a number, the impact is left empty and the item is ranked lower, never invented.
Assumptions that are not measured from the shop's own data are flagged as such.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commerce import Product
from app.models.workspace import Workspace
from app.services import alerts as alert_service
from app.services import credit, events_insight, inventory, pricing
from app.services.analytics import intelligence
from app.services.assistant.tools import inr
from app.services.bills import service as bills

D = Decimal

# Recovery rates below are ASSUMPTIONS from general practice, not measured on this shop; the
# range is shown so the owner can discount it. They are flagged "unmeasured" in the output.
UDHAAR_RECOVERY = (0.3, 0.5, 0.7)
DEAD_STOCK_RECOVERY = (0.2, 0.35, 0.5)
LAPSED_REACTIVATION = (0.1, 0.2, 0.35)
FESTIVAL_UPLIFT = (0.1, 0.25, 0.4)


def _impact(
    low: float | None,
    exp: float | None,
    high: float | None,
    basis: str,
    assumptions: list[str],
    measured: bool,
) -> dict[str, Any]:
    return {"low": None if low is None else round(low), "expected": None if exp is None else round(exp),
            "high": None if high is None else round(high), "basis": basis, "assumptions": assumptions, "measured": measured}  # fmt: skip


def _cand(
    key: str,
    kind: str,
    title: str,
    why: str,
    evidence: list[tuple[str, str, str]],
    impact: dict[str, Any],
    effort: str,
    confidence: str,
    link: str,
) -> dict[str, Any]:
    return {"key": key, "kind": kind, "title": title, "why": why, "effort": effort, "confidence": confidence, "link": link, "impact": impact,
            "evidence": [{"label": a, "value": b, "source": c} for a, b, c in evidence]}  # fmt: skip


def reorder(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    ov = inventory.overview(db, ws)
    prices = {
        p.sku: p.list_price
        for p in db.scalars(select(Product).where(Product.workspace_id == ws.id))
    }
    urgent = [i for i in ov["items"] if i["status"] == "urgent"]
    soon = [i for i in ov["items"] if i["status"] == "reorder"]
    out: list[dict[str, Any]] = []
    if urgent:
        lost, known = 0.0, 0
        for i in urgent:
            price = prices.get(i["sku"])
            cover = float(i["cover_days"] or 0)
            short = max(0.0, float(i["lead_time_days"]) - cover)
            if price is not None:
                lost += short * float(i["daily_rate"]) * float(price)
                known += 1
        exp = lost if known == len(urgent) and lost > 0 else None
        out.append(_cand(
            "reorder|urgent", "reorder", f"Order {len(urgent)} products today: they run out before a new order can arrive",
            "Delivery takes longer than the stock will last. Every day of delay is a day of empty shelf.",
            [(i["name"], f"{i['cover_days']} days left, delivery {i['lead_time_days']} days, order {i['order_qty']}", "inventory:cover") for i in urgent[:5]],
            _impact(0.6 * exp if exp else None, exp, 1.2 * exp if exp else None, "Days short of the delivery time x daily sales x selling price", ["Demand continues at the forecast rate", "Customers do not buy elsewhere meanwhile (so this is sales at risk)"], exp is not None),
            "S", "high", "/app/inventory"))  # fmt: skip
    if soon:
        out.append(_cand("reorder|soon", "reorder", f"Plan orders for {len(soon)} more products this week",
                         "They will run out before the order after this one could arrive.",
                         [(i["name"], f"{i['cover_days']} days of cover", "inventory:cover") for i in soon[:5]], _impact(None, None, None, "Not estimated: avoiding a stock-out saves sales only if it would have happened", [], False), "S", "medium", "/app/inventory"))  # fmt: skip
    return out


def margin_leaks(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    leaks, _ = alert_service.rule_margin(db, ws.id, today)
    out = []
    for x in leaks[:5]:
        e = x["evidence"]
        monthly = float(e["leak_amount"])  # lost over the compared window; windows are 28 days
        out.append(_cand(
            x["key"], "price_fix", x["title"].split(":")[0] + f": raise the price to {inr(e['suggested_price'])}", x["detail"],
            [("Cost change", f"{e['cost_change_pct']:+.1f}%", "costs:history"), ("Price change", f"{e['price_change_pct']:+.1f}%", "costs:history"), ("Margin", f"{e['margin_prev_pct']:.1f}% → {e['margin_now_pct']:.1f}%", "costs:margin")],
            _impact(0.5 * monthly, 0.8 * monthly, monthly, "Margin lost in the last 28 days, if the old margin is restored", ["Raising the price may cost some volume (low case), customers accept it (high case)"], True),
            "S", "high", "/app/costs"))  # fmt: skip
    return out


def udhaar(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    rows = [r for r in credit.parties(db, ws.id, today) if r["oldest_days"] > 30]
    if not rows:
        return []
    total = float(sum(r["owed"] for r in rows))
    lo, ex, hi = (total * f for f in UDHAAR_RECOVERY)
    return [_cand(
        "udhaar|chase", "collect_udhaar", f"Remind {len(rows)} people who owe {inr(total)} for more than 30 days",
        "Old dues are the hardest to recover and the easiest to start on: a short, polite message.",
        [(r["name"], f"{inr(r['owed'])}, {r['oldest_days']} days", "udhaar:FIFO ageing") for r in rows[:5]],
        _impact(lo, ex, hi, "Dues older than 30 days x an assumed recovery share", [f"{int(UDHAAR_RECOVERY[0] * 100)}-{int(UDHAAR_RECOVERY[2] * 100)}% of old dues come back when asked (unmeasured, general practice)"], False),
        "S", "medium", "/app/udhaar")]  # fmt: skip


def dead_stock(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    ov = inventory.overview(db, ws)
    dead = [i for i in ov["items"] if i["status"] == "dead"]
    cash = float(ov["summary"]["dead_cash"] or 0)
    if not dead or cash <= 0:
        return []
    lo, ex, hi = (cash * f for f in DEAD_STOCK_RECOVERY)
    return [_cand(
        "dead_stock|clear", "clear_stock", f"Free {inr(cash)} stuck in {len(dead)} products that have not sold",
        "Stock that does not sell holds cash. A bundle or a small offer above cost turns it back into money.",
        [(i["name"], f"{inr(i['cash_tied'])} in stock", "inventory:dead stock") for i in dead[:5]],
        _impact(lo, ex, hi, "Cash in dead stock x an assumed share recovered at or above cost", [f"{int(DEAD_STOCK_RECOVERY[0] * 100)}-{int(DEAD_STOCK_RECOVERY[2] * 100)}% of it sells within two months (unmeasured)"], False),
        "M", "medium", "/app/inventory")]  # fmt: skip


def winback(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    s = intelligence.customers_summary(db, ws, None, 365, 30, 30, 45)
    n = int(s["lapsed_regulars"])
    if n < 3:
        return []
    per = float(s["revenue_per_customer"]) / max(
        1.0, 12.0
    )  # a typical month of that customer's spend
    lo, ex, hi = (n * per * f for f in LAPSED_REACTIVATION)
    return [_cand(
        "winback|lapsed", "winback", f"Win back {n} regular customers who have gone quiet",
        "They bought at least twice and nothing in 45 days. Bringing a few back costs less than finding new ones.",
        [("Regulars gone quiet", str(n), "customers:lapse 45 days"), ("Typical monthly spend", inr(per), "customers:revenue per customer / 12")],
        _impact(lo, ex, hi, "Quiet regulars x a typical month's spend x an assumed share who return", [f"{int(LAPSED_REACTIVATION[0] * 100)}-{int(LAPSED_REACTIVATION[2] * 100)}% return after a message (unmeasured)"], False),
        "S", "medium", "/app/campaigns")]  # fmt: skip


def festival(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    ev = events_insight.upcoming(db, ws, days=21, include_cricket=False, today=today)
    out = []
    for e in ev[:2]:
        at_risk = [p for p in e.get("products", []) if p.get("at_risk")]
        if not at_risk:
            continue
        days = max(1, (e["event"].end - e["event"].start).days + 1)
        daily = sum(float(p["daily_sales"]) for p in at_risk)
        lo, ex, hi = (daily * days * f for f in FESTIVAL_UPLIFT)
        out.append(_cand(
            f"festival|{e['event'].id}", "festival_stock", f"Stock up before {e['event'].name}: {len(at_risk)} products may run short",
            f"{e['event'].name} starts in {e['days_until']} days and these products usually sell more.",
            [(p["name"], f"{inr(p['daily_sales'])} a day now", "events:matching products") for p in at_risk[:5]],
            _impact(lo, ex, hi, "Daily sales of the products at risk x days of the event x an assumed uplift", [f"Demand rises {int(FESTIVAL_UPLIFT[0] * 100)}-{int(FESTIVAL_UPLIFT[2] * 100)}% (unmeasured unless the festival Page shows your own past lift)"], False),
            "M", "medium", "/app/festivals"))  # fmt: skip
    return out


def supplier_pass_through(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    out = []
    for m in [x for x in bills.price_moves(db, ws.id) if x["change_pct"] >= 5][:4]:
        lp = m["list_price"]
        if lp is None:
            continue
        rise = float(m["latest"]) - float(m["previous"])
        out.append(_cand(
            f"pass_through|{m['product_id']}", "price_fix", f"{m['name']}: supplier raised the price {m['change_pct']:.0f}%, check your selling price",
            f"You now pay {inr(m['latest'])} (was {inr(m['previous'])}) and sell at {inr(lp)}. Each unit earns {inr(rise)} less unless the price moves.",
            [("Purchase price", f"{inr(m['previous'])} → {inr(m['latest'])}", "bills:confirmed bills"), ("Selling price", inr(lp), "product list price")],
            _impact(None, None, None, "Not estimated: needs this product's monthly units", [f"Margin per unit down by {inr(rise)}"], False), "S", "high", "/app/bills"))  # fmt: skip
    return out


def stop_losing_discounts(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    d = pricing.discounts(db, ws.id)
    bad = [i for i in d.get("items", []) if i["verdict"] == "lost_money"][:3]
    out = []
    for i in bad:
        lo, hi = abs(i["profit_effect_high"]), abs(i["profit_effect_low"])
        out.append(_cand(
            f"discount|{i['sku']}", "stop_discount", f"Stop discounting {i['name']}: it lost money",
            f"On {i['promo_days']} discount days sales rose only {i['lift_pct']:.0f}% and profit was {inr(abs(i['profit_effect']))} lower than normal days would have given.",
            [("Discount days", str(i["promo_days"]), "pricing:promo days"), ("Sales lift", f"{i['lift_pct']:+.0f}%", "pricing:vs same weekday"), ("Profit effect", inr(i["profit_effect"]), "pricing:bootstrap 95% range")],
            _impact(lo, abs(i["profit_effect"]), hi, "Profit lost on discount days over the last 180 days, range from the bootstrap", ["Other things changed on those days too (festivals, weather, stock)"], True),
            "S", "medium", "/app/pricing"))  # fmt: skip
    return out


def price_tests(db: Session, ws: Workspace, today: date) -> list[dict[str, Any]]:
    m = pricing.price_moves(db, ws.id)
    out = []
    for s in m.get("suggestions", [])[:2]:
        pc = s["profit_change_month"]
        out.append(_cand(
            f"price_test|{s['sku']}", "price_test", f"Try {inr(s['suggested_price'])} for {s['name']} (+{s['step_pct']:.0f}%) for a week",
            s["why"], [("Margin now", f"{s['margin_pct']}%", "costs:margin"), ("Price now", inr(s["price"]), "sales:net price per unit")],
            _impact(max(0, pc["low"]), pc["expected"], pc["high"], "Monthly profit change from a small rise, using " + ("this product's own measured response" if s["measured"] else "an assumed range of shopper response"), [s["assumption"]] if s["assumption"] else [], bool(s["measured"])),
            "S", "medium" if s["measured"] else "low", "/app/pricing"))  # fmt: skip
    return out


GENERATORS = [
    reorder,
    margin_leaks,
    udhaar,
    dead_stock,
    winback,
    festival,
    supplier_pass_through,
    stop_losing_discounts,
    price_tests,
]


# ------------------------------------------------------------------ outcome metrics


def metric_now(db: Session, ws: Workspace, kind: str, today: date) -> dict[str, Any] | None:
    """The one number an action is meant to move, as it stands today. None when there is no honest metric."""
    if kind == "collect_udhaar":
        return {
            "name": "Udhaar older than 30 days",
            "value": float(credit.summary(db, ws.id, today)["overdue"]),
            "good": "down",
            "money": True,
        }
    if kind == "clear_stock":
        return {
            "name": "Cash in dead stock",
            "value": float(inventory.overview(db, ws)["summary"]["dead_cash"] or 0),
            "good": "down",
            "money": True,
        }
    if kind == "winback":
        return {
            "name": "Regulars gone quiet",
            "value": float(
                intelligence.customers_summary(db, ws, None, 365, 30, 30, 45)["lapsed_regulars"]
            ),
            "good": "down",
            "money": False,
        }
    if kind == "reorder":
        return {
            "name": "Products that will run out first",
            "value": float(inventory.overview(db, ws)["summary"]["urgent"]),
            "good": "down",
            "money": False,
        }
    if kind == "price_fix":
        leaks, _ = alert_service.rule_margin(db, ws.id, today)
        return {
            "name": "Products with a margin leak",
            "value": float(len(leaks)),
            "good": "down",
            "money": False,
        }
    return None
