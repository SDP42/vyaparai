"""The workflows. Each builds a LangGraph StateGraph whose nodes are read-only service calls.

investigate_sales: "why did sales change?" Compare a period with the one before, break the change
into effects, find the products behind it, then check the usual suspects (stock, cost, discounts,
the festival calendar, reviews, customers) and rank what was found.
"""

import operator
from datetime import date
from decimal import Decimal
from itertools import pairwise
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.services import alerts as alert_service
from app.services import events_insight, inventory
from app.services.agents.engine import Recorder, traced
from app.services.analytics import queries as q
from app.services.analytics import service as analytics
from app.services.analytics.types import Filters
from app.services.assistant.tools import inr
from app.services.bills import service as bills
from app.services.recommend import service as recommend
from app.services.reviews import service as reviews

D = Decimal
FLAT_PCT = 3.0  # below this change, there is nothing to explain


class State(TypedDict, total=False):
    params: dict[str, Any]
    facts: dict[str, Any]
    findings: Annotated[list[dict[str, Any]], operator.add]
    notes: Annotated[list[str], operator.add]
    result: dict[str, Any]


def _f(ctx: dict[str, Any]) -> Filters:
    f: Filters = ctx["f"]
    return f


def _find(
    kind: str, title: str, detail: str, weight: float, evidence: list[tuple[str, str, str]]
) -> dict[str, Any]:
    return {"kind": kind, "title": title, "detail": detail, "weight": round(max(0.0, min(1.0, weight)), 2),
            "evidence": [{"label": a, "value": b, "source": c} for a, b, c in evidence]}  # fmt: skip


def investigate_sales(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    ws = workspace.id
    ctx: dict[str, Any] = {}

    def scope(s: State) -> dict[str, Any]:
        first, last = q.workspace_bounds(db, ws)
        if first is None or last is None:
            raise ValueError("No sales have been imported yet")
        a = date.fromisoformat(params["from"]) if params.get("from") else None
        b = date.fromisoformat(params["to"]) if params.get("to") else None
        note = None
        if (
            a and b
        ):  # days after the last sale (or before the first) are not "no sales", they are no data
            ca, cb = max(a, first), min(b, last)
            if ca > cb:
                note = f"There are no sales between {a} and {b}; the latest 30 days of data are used instead."
                a = b = None
            elif (ca, cb) != (a, b):
                note = f"Your sales run from {first:%d %b %Y} to {last:%d %b %Y}, so the period was trimmed to {ca:%d %b} - {cb:%d %b}."
                a, b = ca, cb
        if note:
            ctx["scope_note"] = note
        f = analytics.resolve_filters(db, ws, a, b)
        ctx["f"] = f
        from app.services.analytics.compare import resolve_compare

        rng = resolve_compare(f.date_from, f.date_to, "previous_period")
        ctx["compare"] = rng
        out: dict[str, Any] = {
            "facts": {
                "from": f.date_from,
                "to": f.date_to,
                "compare_from": rng[0] if rng else None,
                "compare_to": rng[1] if rng else None,
                "latest_sale": last,
            }
        }
        if ctx.get("scope_note"):
            out["notes"] = [ctx["scope_note"]]
        return out

    def headline(s: State) -> dict[str, Any]:
        ov = analytics.overview(db, workspace, _f(ctx), "previous_period")
        k = {x["key"]: x for x in ov["headline"] + ov["secondary"]}
        ctx["kpi"] = k
        ns = k["net_sales"]
        ch = None if ns["change_pct"] is None else float(ns["change_pct"])
        facts = {**s["facts"], "net_sales": ns["value"], "previous": ns["previous"], "change": ns["change"], "change_pct": ch,
                 "orders_pct": None if k["orders"]["change_pct"] is None else float(k["orders"]["change_pct"]),
                 "aov_pct": None if k["aov"]["change_pct"] is None else float(k["aov"]["change_pct"])}  # fmt: skip
        out: dict[str, Any] = {"facts": facts}
        if ch is not None:
            word = "rose" if ch > 0 else "fell"
            out["findings"] = [_find("measured", f"Net sales {word} {abs(ch):.1f}%", f"{inr(ns['previous'])} before, {inr(ns['value'])} now.", 1.0,
                                     [("Net sales now", inr(ns["value"]), "metric:net_sales@v1"), ("Net sales before", inr(ns["previous"]), "metric:net_sales@v1")])]  # fmt: skip
        return out

    def route(s: State) -> str:
        ch = s.get("facts", {}).get("change_pct")
        return "conclude" if ch is None or abs(ch) < FLAT_PCT else "drivers"

    def drivers(s: State) -> dict[str, Any]:
        d = analytics.drivers(db, workspace, _f(ctx), "previous_period")
        ctx["drivers"] = d
        total = float(d["net_change"]) or 1.0
        fs = []
        for e in sorted(d["effects"], key=lambda e: -abs(float(e["amount"])))[:3]:
            amt = float(e["amount"])
            if amt == 0:
                continue
            share = abs(amt) / abs(total)
            fs.append(_find("measured", f"{e['label']} effect {inr(amt)}", f"{e['explanation']}. This is {share * 100:.0f}% of the change.", share,
                            [(e["label"], inr(amt), "drivers:price_volume_mix")]))  # fmt: skip
        return {"findings": fs, "facts": {**s["facts"], "net_change": d["net_change"]}}

    def movers(s: State) -> dict[str, Any]:
        d = ctx["drivers"]
        total = float(d["net_change"]) or 1.0
        down = d["biggest_decliners"][:3]
        up = d["biggest_gainers"][:3]
        ctx["down_skus"] = [x["sku"] for x in down]
        fs = []
        for label, rows in (("fell", down), ("rose", up)):
            if not rows:
                continue
            amt = sum(float(r["delta"]) for r in rows)
            share = abs(amt) / abs(total)
            fs.append(_find("measured", f"{len(rows)} products {label} by {inr(abs(amt))}", ", ".join(f"{r['name']} ({inr(r['delta'])})" for r in rows) + f". About {share * 100:.0f}% of the net change.",
                            min(share, 1.0) * 0.8, [(r["name"], inr(r["delta"]), "drivers:biggest movers") for r in rows]))  # fmt: skip
        return {"findings": fs}

    def stock_check(s: State) -> dict[str, Any]:
        skus = set(ctx.get("down_skus", []))
        ov = inventory.overview(db, workspace)
        hit = [i for i in ov["items"] if i["sku"] in skus and i["status"] in {"urgent", "reorder"}]
        if not skus or not ov["items"]:
            return {"notes": ["Stock was not checked: no stock counts or no falling products"]}
        if not hit:
            return {"facts": {**s["facts"], "stock_flags": 0}}
        return {"findings": [_find("context", f"{len(hit)} falling products are low on stock now", "Empty shelves can cut sales. Stock counts show today's position, not the position during the period, so this is a possibility, not a finding.", 0.5,
                                   [(i["name"], f"{i['cover_days']} days of cover" if i["cover_days"] is not None else i["status"], "inventory:cover") for i in hit[:4]])]}  # fmt: skip

    def cost_check(s: State) -> dict[str, Any]:
        leaks, _ = alert_service.rule_margin(db, ws, _f(ctx).date_to)
        moves = [m for m in bills.price_moves(db, ws) if m["change_pct"] > 0]
        fs = []
        if leaks:
            fs.append(
                _find(
                    "context",
                    f"{len(leaks)} products have a margin leak",
                    "Costs rose without prices following. This affects profit more than sales.",
                    0.3,
                    [(x["title"][:60], "margin leak", "costs:leaks") for x in leaks[:3]],
                )
            )
        if moves:
            fs.append(
                _find(
                    "context",
                    f"{len(moves)} suppliers raised prices",
                    "Rising purchase prices can lead to price rises that slow sales.",
                    0.25,
                    [
                        (m["name"], f"{m['change_pct']:+.1f}%", "bills:price moves")
                        for m in moves[:3]
                    ],
                )
            )
        return {"findings": fs}

    def discount_check(s: State) -> dict[str, Any]:
        r = ctx["kpi"].get("discount_rate")
        if not r or r["change"] is None:
            return {}
        pts = float(r["change"])
        ch = s["facts"]["change_pct"]
        if pts >= 1 and ch < 0:
            return {
                "findings": [
                    _find(
                        "context",
                        f"Discounts rose {pts:.1f} points but sales still fell",
                        "More discount did not lift sales in this period.",
                        0.35,
                        [("Discount rate change", f"{pts:+.1f} pts", "metric:discount_rate@v1")],
                    )
                ]
            }
        if pts <= -1 and ch < 0:
            return {
                "findings": [
                    _find(
                        "context",
                        f"Discounts were cut by {abs(pts):.1f} points",
                        "Giving less discount can lower volume. Check whether margin improved.",
                        0.3,
                        [("Discount rate change", f"{pts:+.1f} pts", "metric:discount_rate@v1")],
                    )
                ]
            }
        return {}

    def calendar_check(s: State) -> dict[str, Any]:
        f = _f(ctx)
        cmp = ctx.get("compare")
        if not cmp:
            return {}
        now = {
            e.id: e
            for e in events_insight.calendar(
                workspace, f.date_from, f.date_to, include_cricket=False, tier_max=2
            )
        }
        before = {
            e.id: e
            for e in events_insight.calendar(
                workspace, cmp[0], cmp[1], include_cricket=False, tier_max=2
            )
        }
        only_before = [e for k, e in before.items() if k not in now]
        only_now = [e for k, e in now.items() if k not in before]
        ch = s["facts"]["change_pct"]
        fs = []
        if only_before and ch < 0:
            fs.append(
                _find(
                    "context",
                    "The earlier period had a festival this one did not",
                    "Comparing with a festive period makes a normal period look weak.",
                    0.6,
                    [
                        (e.name, f"{e.start:%d %b}–{e.end:%d %b}", "festival calendar")
                        for e in only_before[:3]
                    ],
                )
            )
        if only_now and ch > 0:
            fs.append(
                _find(
                    "context",
                    "This period included a festival the earlier one did not",
                    "Part of the rise is the calendar, not a lasting change.",
                    0.6,
                    [
                        (e.name, f"{e.start:%d %b}–{e.end:%d %b}", "festival calendar")
                        for e in only_now[:3]
                    ],
                )
            )
        return {"findings": fs}

    def review_check(s: State) -> dict[str, Any]:
        sm = reviews.summary(db, ws, 30, _f(ctx).date_to)
        bad = [t for t in sm["themes"] if t["mentions"] >= 5 and t["negative_pct"] >= 40]
        if not bad or s["facts"]["change_pct"] >= 0:
            return {}
        return {"findings": [_find("context", "Customers are complaining about " + ", ".join(t["label"].lower() for t in bad[:2]), "Complaints can come before lost sales.", 0.3,
                                   [(t["label"], f"{t['negative_pct']:.0f}% negative of {t['mentions']}", "reviews:themes") for t in bad[:3]])]}  # fmt: skip

    def customers_check(s: State) -> dict[str, Any]:
        o, a = s["facts"].get("orders_pct"), s["facts"].get("aov_pct")
        if o is None or a is None:
            return {}
        if abs(o) >= abs(a):
            t, w = (
                f"Orders {o:+.1f}% matter more than basket size {a:+.1f}%",
                abs(o) / max(abs(o) + abs(a), 1),
            )
            d = "The change is mostly about how many orders came in, not how much each was worth."
        else:
            t, w = (
                f"Basket size {a:+.1f}% matters more than orders {o:+.1f}%",
                abs(a) / max(abs(o) + abs(a), 1),
            )
            d = "The change is mostly about how much each order was worth, not how many came in."
        return {
            "findings": [
                _find(
                    "measured",
                    t,
                    d,
                    w * 0.7,
                    [
                        ("Orders change", f"{o:+.1f}%", "metric:orders@v1"),
                        ("Average order change", f"{a:+.1f}%", "metric:aov@v1"),
                    ],
                )
            ]
        }

    def conclude(s: State) -> dict[str, Any]:
        facts = s.get("facts", {})
        findings = sorted(
            s.get("findings", []), key=lambda x: (x["kind"] != "measured", -x["weight"])
        )
        ch = facts.get("change_pct")
        if ch is None:
            summary = (
                "There is no earlier period to compare with, so there is nothing to explain yet."
            )
        elif abs(ch) < FLAT_PCT:
            summary = f"Net sales moved only {ch:+.1f}% against the period before: no material change to explain."
        else:
            measured = [f for f in findings if f["kind"] == "measured"][1:4]
            context = [f for f in findings if f["kind"] == "context"][:3]
            summary = (
                f"Net sales {'rose' if ch > 0 else 'fell'} {abs(ch):.1f}% ({inr(abs(float(facts['net_change'])))}). "
                + " ".join(f"{f['title']}." for f in measured)
            )
            if context:
                summary += (
                    " Worth checking: " + "; ".join(f["title"].lower() for f in context) + "."
                )
        return {"result": {"summary": summary, "findings": findings, "facts": facts, "notes": s.get("notes", []),
                           "caveat": "This shows how the numbers changed and what else was going on. It does not prove why customers behaved this way."}}  # fmt: skip

    g = StateGraph(State)
    nodes: list[tuple[str, Any]] = [("scope", scope), ("headline", headline), ("drivers", drivers), ("movers", movers), ("stock_check", stock_check),
                                    ("cost_check", cost_check), ("discount_check", discount_check), ("calendar_check", calendar_check),
                                    ("review_check", review_check), ("customers_check", customers_check), ("conclude", conclude)]  # fmt: skip
    for name, fn in nodes:
        wrapped: Any = traced(
            rec,
            name,
            fn,
            lambda o: f"{len(o.get('findings', []))} findings" if "findings" in o else "",
        )  # LangGraph infers node types from the function; ours takes the state as Any
        g.add_node(name, wrapped)
    g.set_entry_point("scope")
    g.add_edge("scope", "headline")
    g.add_conditional_edges("headline", route, {"drivers": "drivers", "conclude": "conclude"})
    chain = [
        "drivers",
        "movers",
        "stock_check",
        "cost_check",
        "discount_check",
        "calendar_check",
        "review_check",
        "customers_check",
        "conclude",
    ]
    for a, b in pairwise(chain):
        g.add_edge(a, b)
    g.add_edge("conclude", END)
    out = g.compile().invoke(
        {"params": params, "facts": {}, "findings": [], "notes": []}, config={"recursion_limit": 30}
    )
    res: dict[str, Any] = out.get("result") or {
        "summary": "The workflow stopped before it could conclude.",
        "findings": [],
        "notes": out.get("notes", []),
    }
    return res


def weekly_review(
    db: Session, workspace: Workspace, rec: Recorder, params: dict[str, Any]
) -> dict[str, Any]:
    """What to do this week: refresh every signal, then list the top suggestions with their reasons."""

    def refresh(s: State) -> dict[str, Any]:
        r = recommend.refresh(db, workspace)
        return {
            "facts": {**s.get("facts", {}), "refresh": r},
            "notes": [f"A signal could not be read: {e}" for e in r["errors"]],
        }

    def alerts(s: State) -> dict[str, Any]:
        c = alert_service.counts(db, workspace.id)
        return {"facts": {**s["facts"], "alerts": c}}

    def rank(s: State) -> dict[str, Any]:
        top = recommend.listing(db, workspace.id, "proposed")[:5]
        fs = [_find("measured" if r.impact.get("measured") else "context", r.title, r.why, min(1.0, r.score / 10000) if r.score else 0.1,
                    [(e["label"], e["value"], e["source"]) for e in r.evidence[:4]]) for r in top]  # fmt: skip
        return {"findings": fs, "facts": {**s["facts"], "top": [r.title for r in top]}}

    def conclude(s: State) -> dict[str, Any]:
        facts, f = s["facts"], s.get("findings", [])
        al = facts.get("alerts", {})
        if not f:
            summary = "Nothing needs your action this week."
        else:
            summary = (
                f"{len(f)} things to do this week, most valuable first: "
                + "; ".join(x["title"] for x in f[:3])
                + "."
            )
        if al.get("high"):
            summary += f" {al['high']} alerts need attention."
        return {"result": {"summary": summary, "findings": f, "facts": facts, "notes": s.get("notes", []),
                           "caveat": "Impact figures are estimates with stated assumptions, not promises. Approve what you will actually do on the Recommendations page."}}  # fmt: skip

    g = StateGraph(State)
    for name, fn in [
        ("refresh", refresh),
        ("alerts", alerts),
        ("rank", rank),
        ("conclude", conclude),
    ]:
        wrapped: Any = traced(
            rec,
            name,
            fn,
            lambda o: f"{len(o.get('findings', []))} findings" if "findings" in o else "",
        )
        g.add_node(name, wrapped)
    g.set_entry_point("refresh")
    for a, b in pairwise(["refresh", "alerts", "rank", "conclude"]):
        g.add_edge(a, b)
    g.add_edge("conclude", END)
    out = g.compile().invoke(
        {"params": params, "facts": {}, "findings": [], "notes": []}, config={"recursion_limit": 20}
    )
    res: dict[str, Any] = out.get("result") or {
        "summary": "The workflow stopped before it could conclude.",
        "findings": [],
        "notes": out.get("notes", []),
    }
    return res


WORKFLOWS: dict[str, dict[str, Any]] = {
    "weekly_review": {
        "title": "What should I do this week?",
        "about": "Reads every signal (stock, margins, udhaar, festivals, customers, supplier prices), refreshes the recommendations and lists the top five with reasons.",
        "params": [],
        "run": weekly_review,
    },
    "investigate_sales": {
        "title": "Why did sales change?",
        "about": "Compares a period with the one before, splits the change into effects, finds the products behind it, then checks stock, costs, discounts, festivals, reviews and customers.",
        "params": ["from", "to"],
        "run": investigate_sales,
    },
}
