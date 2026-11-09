"""The owner digest: three numbers, one action, in text a shop owner reads in half a minute.

Content follows docs/research/DIGEST.md: the owner should not need to open a dashboard. Numbers come
from the same metric layer as the app, actions from rules over customers and forecasts, and every
figure is aggregate (no customer names or IDs leave the app in a digest).
"""

import html
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.workspace import Workspace
from app.services import alerts as alert_service
from app.services.analytics import intelligence
from app.services.analytics import queries as q
from app.services.analytics.types import Filters, metric_values
from app.services.forecasting import service as forecast_service

Kind = Literal["daily", "weekly"]
D = Decimal
STALE_AFTER_DAYS = 2
MIN_LAPSED_FOR_ACTION = 3


def inr(x: Decimal | float | int) -> str:
    """Rupees with Indian digit grouping: 1234567 -> ₹12,34,567."""
    n = int(Decimal(str(x)).quantize(D(1), rounding=ROUND_HALF_UP))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    head, tail = s[:-3], s[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return f"{sign}₹{','.join([*parts, tail])}" if parts else f"{sign}₹{tail}"


@dataclass(slots=True)
class ActionContext:
    lapsed_regulars: int
    risers: list[dict[str, Any]]
    fallers: list[dict[str, Any]]
    cost_coverage: Decimal | None
    sales_change_pct: Decimal | None
    kind: Kind
    alerts: list[dict[str, str]] = field(
        default_factory=list
    )  # open high-severity alerts, first = most important


def choose_actions(c: ActionContext) -> list[dict[str, str]]:
    """Ordered actions, most useful first. The digest shows the first and mentions up to two more."""
    out: list[dict[str, str]] = [
        {"kind": "alert", "title": a["title"], "detail": a["detail"], "link": a["link"]}
        for a in c.alerts[:1]
    ]
    if c.lapsed_regulars >= MIN_LAPSED_FOR_ACTION:
        out.append(
            {
                "kind": "winback",
                "title": f"Message {c.lapsed_regulars} regular customers who have gone quiet",
                "detail": "They used to buy often. A friendly note now costs less than losing them.",
                "link": "/app/campaigns",
            }
        )
    for r in c.risers:
        if r["units_last"] >= 10 and r["change_pct"] >= 15:
            out.append(
                {
                    "kind": "stock_up",
                    "title": f"Stock up on {r['name']}",
                    "detail": f"Expected to sell about {r['change_pct']:.0f}% more over the next two weeks "
                    f"({r['units_last']:.0f} to {r['units_next']:.0f} units).",
                    "link": "/app/forecasts",
                }
            )
            break
    for r in c.fallers:
        if r["units_last"] >= 10 and r["change_pct"] <= -20:
            out.append(
                {
                    "kind": "ease_off",
                    "title": f"Go easy on reordering {r['name']}",
                    "detail": f"Expected to sell about {abs(r['change_pct']):.0f}% less over the next "
                    f"two weeks ({r['units_last']:.0f} to {r['units_next']:.0f} units).",
                    "link": "/app/forecasts",
                }
            )
            break
    if c.sales_change_pct is not None and c.sales_change_pct <= D(-10):
        label = "last week" if c.kind == "weekly" else "the same day last week"
        out.append(
            {
                "kind": "sales_drop",
                "title": f"Sales are down {abs(c.sales_change_pct):.0f}% on {label}",
                "detail": "Open the sales explorer to see which products and days fell.",
                "link": "/app/sales",
            }
        )
    if c.cost_coverage is not None and c.cost_coverage < 60:
        out.append(
            {
                "kind": "add_costs",
                "title": "Add costs for your products",
                "detail": f"Only {c.cost_coverage:.0f}% of sales have a cost, so margins are understated.",
                "link": "/app/data",
            }
        )
    if not out:
        out.append(
            {
                "kind": "steady",
                "title": "Nothing urgent",
                "detail": "Sales are steady. Keep your best sellers stocked.",
                "link": "/app",
            }
        )
    return out


def _pct(cur: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if cur is None or prev is None or prev == 0:
        return None
    return ((cur - prev) / prev * 100).quantize(D("0.1"), rounding=ROUND_HALF_UP)


def _arrow(x: Decimal | None) -> str:
    return "" if x is None else "▲" if x > 0 else "▼" if x < 0 else "■"


def _line(label: str, value: str, change: str | None) -> str:
    return f"{label}: {value}" + (f" ({change})" if change else "")


def build(
    db: Session,
    workspace: Workspace,
    kind: Kind,
    *,
    as_of: date | None = None,
    today: date | None = None,
) -> dict[str, Any] | None:
    """Build one digest; None when the workspace has no completed sales."""
    first, last = q.workspace_bounds(db, workspace.id)
    if last is None or first is None:
        return None
    end = min(as_of or last, last)
    today = today or date.today()
    if kind == "daily":
        cur = Filters(date_from=end, date_to=end)
        prev = Filters(date_from=end - timedelta(days=7), date_to=end - timedelta(days=7))
        versus = f"vs last {end:%a}"
        label = f"{end:%a %d %b %Y}"
    else:
        cur = Filters(date_from=end - timedelta(days=6), date_to=end)
        prev = Filters(date_from=end - timedelta(days=13), date_to=end - timedelta(days=7))
        versus = "vs the week before"
        label = f"{cur.date_from:%d %b} to {end:%d %b %Y}"

    cv = metric_values(q.build_totals(db, workspace.id, cur)[0])
    pv = metric_values(q.build_totals(db, workspace.id, prev)[0])
    cov_totals = q.build_totals(
        db, workspace.id, Filters(date_from=end - timedelta(days=27), date_to=end)
    )[0]
    coverage = metric_values(cov_totals)["cost_coverage"]

    sales_c = _pct(cv["net_sales"], pv["net_sales"])
    orders_c = _pct(cv["orders"], pv["orders"])
    use_margin = coverage is not None and coverage >= 80 and cv["gross_margin"] is not None
    headline: list[dict[str, Any]] = [
        {
            "key": "net_sales",
            "label": "Sales",
            "value": inr(cv["net_sales"] or 0),
            "change": sales_c,
            "unit": "pct",
        },
        {
            "key": "orders",
            "label": "Orders",
            "value": str(int(cv["orders"] or 0)),
            "change": orders_c,
            "unit": "pct",
        },
    ]
    if use_margin and cv["gross_margin"] is not None:
        pts = (
            (cv["gross_margin"] - pv["gross_margin"]).quantize(D("0.1"), rounding=ROUND_HALF_UP)
            if pv["gross_margin"] is not None
            else None
        )
        headline.append(
            {
                "key": "gross_margin",
                "label": "Margin",
                "value": f"{cv['gross_margin'].quantize(D('0.1'), rounding=ROUND_HALF_UP)}%",
                "change": pts,
                "unit": "pts",
            }
        )
    else:
        aov_c = _pct(cv["aov"], pv["aov"])
        headline.append(
            {
                "key": "aov",
                "label": "Average bill",
                "value": inr(cv["aov"] or 0),
                "change": aov_c,
                "unit": "pct",
            }
        )
    for h in headline:
        c = h["change"]
        h["text"] = _line(
            h["label"],
            h["value"],
            None
            if c is None
            else f"{_arrow(c)} {abs(c)}{'%' if h['unit'] == 'pct' else ' pts'} {versus}",
        )

    _, lapsed_rows = intelligence.scored(db, workspace, end, 365, 30, 30, 45)
    lapsed = sum(1 for r in lapsed_rows if r.orders >= 2 and r.recency_days >= 45)

    risers: list[dict[str, Any]] = []
    fallers: list[dict[str, Any]] = []
    watch: str | None = None
    run = forecast_service.latest_run(db, workspace.id)
    if run is not None and run.as_of >= end:
        ov = forecast_service.overview(db, workspace, run)
        risers, fallers = ov["risers"], ov["fallers"]
        k = ov["kpis"]
        watch = (
            f"Next {run.horizon} days: about {k['units_next']:,.0f} units "
            f"(likely {k['units_next_low']:,.0f} to {k['units_next_high']:,.0f})"
        )

    alert_service.refresh(db, workspace, as_of=end, today=today)
    high = [
        {"title": a.title, "detail": a.detail, "link": a.link}
        for a in alert_service.top_high(db, workspace.id)
    ]
    actions = choose_actions(ActionContext(lapsed, risers, fallers, coverage, sales_c, kind, high))
    notes: list[str] = []
    stale = (today - end).days
    if stale > STALE_AFTER_DAYS:
        notes.append(
            f"Latest sales are from {end:%d %b %Y}. Import newer sales for an up-to-date summary."
        )
    if not use_margin:
        notes.append("Margin is hidden until most sales have a cost.")

    base = get_settings().app_url.rstrip("/")
    name = "Daily" if kind == "daily" else "Weekly"
    subject = f"{workspace.name}: {name.lower()} summary, {end:%a %d %b}"
    lines = [f"*{workspace.name} · {name} summary*", label, ""]
    lines += [h["text"] for h in headline]
    lines += [
        "",
        f"Do this: {actions[0]['title']}.",
        f"  {actions[0]['detail']}",
        f"  Open: {base}{actions[0]['link']}",
    ]
    if len(actions) > 1:
        lines += ["", "Also: " + "; ".join(a["title"] for a in actions[1:3])]
    if watch:
        lines += ["", watch]
    lines += [""] + [f"Note: {n}" for n in notes] if notes else []
    text = "\n".join(lines).strip() + "\n"

    return {
        "kind": kind,
        "as_of": end,
        "label": label,
        "subject": subject,
        "versus": versus,
        "headline": [
            {k2: (str(v) if isinstance(v, Decimal) else v) for k2, v in h.items()} for h in headline
        ],
        "action": actions[0],
        "more_actions": actions[1:3],
        "watch": watch,
        "notes": notes,
        "stale_days": max(0, stale),
        "text": text,
        "html": _html(workspace.name, name, label, headline, actions, watch, notes, base),
    }


def _html(
    shop: str,
    name: str,
    label: str,
    headline: list[dict[str, Any]],
    actions: list[dict[str, str]],
    watch: str | None,
    notes: list[str],
    base: str,
) -> str:
    e = html.escape
    rows = "".join(f"<p style='margin:4px 0;font-size:16px'>{e(h['text'])}</p>" for h in headline)
    a = actions[0]
    more = ""
    if len(actions) > 1:
        more = (
            f"<p style='color:#776a59'>Also: {e('; '.join(x['title'] for x in actions[1:3]))}</p>"
        )
    extra = (f"<p>{e(watch)}</p>" if watch else "") + "".join(
        f"<p style='color:#776a59;font-size:13px'>{e(n)}</p>" for n in notes
    )
    return (
        "<div style='font-family:system-ui,sans-serif;max-width:520px;margin:auto;color:#1b1612'>"
        f"<h2 style='margin:0'>{e(shop)}</h2><p style='margin:2px 0 14px;color:#776a59'>{e(name)} summary · {e(label)}</p>"
        f"{rows}"
        f"<div style='margin:16px 0;padding:12px 14px;border-radius:12px;background:#f2a71b33'><b>Do this: {e(a['title'])}</b>"
        f"<br>{e(a['detail'])}<br><a href='{e(base + a['link'])}'>Open in Vyapar AI</a></div>"
        f"{more}{extra}</div>"
    )
