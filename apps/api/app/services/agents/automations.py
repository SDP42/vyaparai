"""Automation agents for the shop's daily routine. Each is a small LangGraph graph of read-only checks over
existing services, like the analyst workflows, and ends with a short list of findings and ready drafts.

They prepare; they never act. Reminders and order lists come back as text for a person to send, and nothing is
written to the shop's data. They can run on demand or on a daily schedule (see services/agents/schedule.py).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.daily import DayClose, Expense
from app.models.workspace import Workspace
from app.services import costs, credit, daily, inventory
from app.services.agents.engine import Recorder
from app.services.agents.workflows import WORKFLOWS, State, _find, _simple
from app.services.assistant.tools import inr

D = Decimal


def _today(params: dict[str, Any]) -> date:
    raw = params.get("today")
    return date.fromisoformat(raw) if isinstance(raw, str) else datetime.now(UTC).date()


# ------------------------------------------------------------------ morning brief


def morning_brief(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    day = _today(params)
    allc = {"credit", "stock", "cash", "supplier"}

    def sales(s: State) -> dict[str, Any]:
        t = daily.today(db, workspace, day, can=set())
        sv = t.get("sales")
        if not sv or sv["net"] is None:
            return {"notes": ["No sales file yet, so there is no sales number."]}
        ch = sv["vs_same_day_last_week_pct"]
        f = [_find("measured", f"Last day's sales {inr(sv['net'])}" + (f", {ch:+}% on the same day last week" if ch is not None else ""),
                   f"{sv['bills']} bills on {sv['day']}.", 0.6 if ch is not None and abs(ch) >= 10 else 0.3, [("Net sales", inr(sv["net"]), "sales file")])]  # fmt: skip
        return {"findings": f, "facts": {"sales": sv}}

    def money_owed(s: State) -> dict[str, Any]:
        rows = credit.parties(db, workspace.id, day)[:3]
        if not rows:
            return {}
        return {"findings": [_find("measured", f"Call {rows[0]['name']} first: {inr(rows[0]['owed'])} for {rows[0]['oldest_days']} days",
                                   "Ordered by amount and age together.", 0.7, [(r["name"], inr(r["owed"]), "udhaar") for r in rows])]}  # fmt: skip

    def shelves(s: State) -> dict[str, Any]:
        t = daily.today(db, workspace, day, can=allc)
        fs = []
        o = t.get("order") or {}
        if o.get("count"):
            fs.append(_find("measured", f"{o['count']} products to order today", "Order lists by supplier are ready to share.", 0.65,
                            [(x["name"], f"× {x['qty']}", "inventory") for x in o["top"]]))  # fmt: skip
        e = t.get("expiry") or {}
        if e.get("expired") or e.get("this_week"):
            fs.append(_find("measured", f"{e.get('expired', 0)} expired and {e.get('this_week', 0)} expiring this week",
                            "Move them to the front or take them off the shelf.", 0.6, [(x["name"], f"{x['days_left']} days", "expiry list") for x in e.get("soonest", [])]))  # fmt: skip
        c = t.get("cash") or {}
        if c and not c.get("yesterday_closed"):
            fs.append(
                _find(
                    "context",
                    "Yesterday's galla was not closed",
                    "Counting the drawer each night catches mistakes early.",
                    0.3,
                    [],
                )
            )
        if t.get("alerts"):
            fs.append(
                _find("measured", f"{t['alerts']} urgent alerts are open", "See Alerts.", 0.55, [])
            )
        return {"findings": fs}

    return _simple(
        db,
        workspace,
        rec,
        params,
        [("sales", sales), ("money_owed", money_owed), ("shelves", shelves)],
        "A quiet morning: nothing stands out.",
    )


# ------------------------------------------------------------------ reorder planner


def reorder_planner(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    def need(s: State) -> dict[str, Any]:
        ov = inventory.overview(db, workspace)
        items = [i for i in ov["items"] if D(str(i.get("order_qty") or 0)) > 0]
        if not items:
            return {
                "notes": ["Nothing needs ordering (or there are no stock counts yet)."],
                "facts": {"order_cost": 0},
            }
        cost = sum(
            (D(str(i["order_cost"])) for i in items if i.get("order_cost") is not None), D(0)
        )
        missing = sum(1 for i in items if i.get("order_cost") is None)
        urgent = [i for i in items if i["status"] == "urgent"]
        fs = [_find("measured", f"{len(items)} products to order, about {inr(cost)}" + (f" (+{missing} without a cost)" if missing else ""),
                    f"{len(urgent)} of them will run out before a new order arrives.", 0.7 if urgent else 0.45,
                    [(i["name"], f"× {i['order_qty']}", "inventory:order advice") for i in (urgent or items)[:5]])]  # fmt: skip
        return {"findings": fs, "facts": {"order_cost": cost}}

    def cash(s: State) -> dict[str, Any]:
        last = db.scalars(
            select(DayClose)
            .where(DayClose.workspace_id == workspace.id)
            .order_by(DayClose.day.desc())
        ).first()
        cost = D(str(s.get("facts", {}).get("order_cost") or 0))
        if last is None or cost == 0:
            return {}
        if cost > last.counted_cash:
            return {"findings": [_find("context", f"The order ({inr(cost)}) is more than the last cash count ({inr(last.counted_cash)})",
                                       "Order the urgent items first, or ask the supplier for credit days.", 0.6, [("Last close", last.day.isoformat(), "galla")])]}  # fmt: skip
        return {}

    def lists(s: State) -> dict[str, Any]:
        out = daily.order_lists(db, workspace, params.get("lang") or "hinglish")
        return {
            "facts": {
                "order_lists": [
                    {"supplier": g["supplier"], "text": g["text"], "share_url": g["share_url"]}
                    for g in out["groups"]
                ]
            }
        }

    return _simple(
        db,
        workspace,
        rec,
        params,
        [("need", need), ("cash", cash), ("lists", lists)],
        "Stock is fine: nothing to order today.",
    )


# ------------------------------------------------------------------ udhaar collector


def udhaar_collector(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    day = _today(params)
    lang = params.get("lang") or "hinglish"

    def rank(s: State) -> dict[str, Any]:
        rows = credit.parties(db, workspace.id, day)
        if not rows:
            return {"notes": ["Nobody owes the shop money."]}
        total = sum((r["owed"] for r in rows), D(0))
        stalled = [r for r in rows if r["behaviour"] == "stalled"]
        fs = [_find("measured", f"{inr(total)} is owed by {len(rows)} people", "Call in this order: amount and age together.", 0.55,
                    [(r["name"], f"{inr(r['owed'])} · {r['oldest_days']} days", "udhaar") for r in rows[:5]])]  # fmt: skip
        if stalled:
            fs.append(_find("measured", f"{len(stalled)} have not paid anything in over 60 days", "A visit may work better than a message.", 0.75,
                            [(r["name"], inr(r["owed"]), "udhaar") for r in stalled[:4]]))  # fmt: skip
        return {"findings": fs, "facts": {"top": [r["key"] for r in rows[:5]]}}

    def drafts(s: State) -> dict[str, Any]:
        rows = credit.parties(db, workspace.id, day)[:5]
        return {
            "facts": {
                "drafts": [
                    {
                        "name": r["name"],
                        "phone": r["phone"],
                        "text": credit.draft(r, workspace.name, lang),
                    }
                    for r in rows
                ]
            }
        }

    return _simple(
        db,
        workspace,
        rec,
        params,
        [("rank", rank), ("drafts", drafts)],
        "Nobody owes the shop money.",
    )


# ------------------------------------------------------------------ day-end check


def day_end_check(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    day = _today(params) - timedelta(days=1)

    def galla(s: State) -> dict[str, Any]:
        v = daily.close_view(db, workspace, day)
        saved = v["saved"]
        if saved is None:
            return {
                "findings": [
                    _find(
                        "context",
                        f"The galla for {day.isoformat()} was not closed",
                        "Count the drawer and close the day on the Galla page.",
                        0.5,
                        [],
                    )
                ]
            }
        fs = []
        if saved["status"] != "matches":
            fs.append(_find("measured", f"Drawer was {'short' if saved['status'] == 'short' else 'over'} by {inr(abs(saved['difference']))}",
                            "Check cash expenses and udhaar payments that were not written down.", min(1.0, float(abs(saved["difference"])) / 2000 + 0.3),
                            [("Expected", inr(saved["expected_cash"]), "galla"), ("Counted", inr(saved["counted_cash"]), "galla")]))  # fmt: skip
        gap = saved.get("file_gap")
        if gap is not None and abs(gap) >= 100:
            fs.append(
                _find(
                    "measured",
                    f"Typed sales and the sales file differ by {inr(abs(gap))}",
                    "A bill may be missing from the file, or cancelled.",
                    0.45,
                    [],
                )
            )
        return {"findings": fs}

    def spend(s: State) -> dict[str, Any]:
        yday = (
            db.scalar(
                select(func.sum(Expense.amount)).where(
                    Expense.workspace_id == workspace.id, Expense.spent_on == day
                )
            )
            or 0
        )
        month = (
            db.scalar(
                select(func.sum(Expense.amount)).where(
                    Expense.workspace_id == workspace.id,
                    Expense.spent_on >= day - timedelta(days=30),
                    Expense.spent_on < day,
                )
            )
            or 0
        )
        avg = D(str(month)) / 30
        if avg > 0 and D(str(yday)) > avg * 3 and D(str(yday)) > 500:
            return {
                "findings": [
                    _find(
                        "context",
                        f"Spending was {inr(yday)}, about {float(D(str(yday)) / avg):.0f}× a usual day",
                        "Fine if it was rent or a planned repair.",
                        0.35,
                        [],
                    )
                ]
            }
        return {}

    return _simple(
        db,
        workspace,
        rec,
        params,
        [("galla", galla), ("spend", spend)],
        "Yesterday closed cleanly.",
    )


# ------------------------------------------------------------------ expiry clearance


def expiry_clearance(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    day = _today(params)

    def sort(s: State) -> dict[str, Any]:
        ex = daily.expiry_list(db, workspace.id, day)
        items = ex["items"]
        if not items:
            return {
                "notes": ["The expiry list is empty. Add items you worry about on the Expiry page."]
            }
        fs = []
        gone = [i for i in items if i["bucket"] == "expired"]
        week = [i for i in items if i["bucket"] == "this_week"]
        if gone:
            fs.append(_find("measured", f"Take {len(gone)} expired items off the shelf", "Ask the supplier about returns before throwing away.", 0.9,
                            [(i["name"], f"{-i['days_left']} days ago", "expiry list") for i in gone[:5]]))  # fmt: skip
        if week:
            fs.append(_find("measured", f"Sell {len(week)} items first this week", "Move them to the front; a small discount above cost is better than a loss.", 0.6,
                            [(i["name"], f"{i['days_left']} days left", "expiry list") for i in week[:5]]))  # fmt: skip
        return {"findings": fs}

    return _simple(db, workspace, rec, params, [("sort", sort)], "Nothing is about to expire.")


# ------------------------------------------------------------------ supplier price watch


def price_watch(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    def leaks(s: State) -> dict[str, Any]:
        ov = costs.overview(db, workspace.id)
        bad = [i for i in ov["items"] if i["status"] == "margin_leak"]
        if not bad:
            return {}
        return {"findings": [_find("measured", f"{len(bad)} products cost more now but sell at the old price", "Each has a suggested price that restores the old margin.", 0.7,
                                   [(i.get("name") or i["sku"], f"cost +{i.get('cost_change_pct')}% · try {inr(i.get('suggested_price'))}", "costs") for i in bad[:5]])]}  # fmt: skip

    return _simple(
        db,
        workspace,
        rec,
        params,
        [("leaks", leaks)],
        "Supplier prices and your prices are in step.",
    )


NEW = {
    "morning_brief": (
        "Start the day",
        "Last day's sales, who to call for udhaar, what to order, what is expiring and whether the galla was closed.",
        morning_brief,
    ),
    "reorder_planner": (
        "Plan today's orders",
        "What to order, what it costs against the cash you counted, and a ready order list per supplier.",
        reorder_planner,
    ),
    "udhaar_collector": (
        "Collect udhaar",
        "Who to call first, who has stopped paying, and a polite reminder drafted for each.",
        udhaar_collector,
    ),
    "day_end_check": (
        "Check yesterday's close",
        "Was the galla closed, did the drawer match, do typed sales match the file, was spending unusual.",
        day_end_check,
    ),
    "expiry_clearance": (
        "Clear expiring stock",
        "What to take off the shelf and what to sell first this week.",
        expiry_clearance,
    ),
    "price_watch": (
        "Watch supplier prices",
        "Products whose cost went up while your price stayed the same, with a suggested price.",
        price_watch,
    ),
}
for key, (title, about, fn) in NEW.items():
    WORKFLOWS[key] = {"title": title, "about": about, "params": ["today", "lang"], "run": fn, "automation": True}
