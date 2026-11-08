"""Rule-based, deterministic insights. Wording is attributional ("accounts for"), never causal."""

from decimal import Decimal
from typing import Any

from app.services.analytics.drivers import DriverResult
from app.services.analytics.text import inr, pct

Insight = dict[str, Any]
ZERO = Decimal(0)


def _ins(id_: str, tone: str, title: str, body: str, evidence: list[str]) -> Insight:
    return {"id": id_, "tone": tone, "title": title, "body": body, "evidence": evidence}


def build_insights(
    *,
    current: dict[str, Decimal | None],
    previous: dict[str, Decimal | None] | None,
    compare_label: str | None,
    drivers: DriverResult | None,
    category_mix: list[dict[str, Any]],
    days_in_period: int,
) -> list[Insight]:
    out: list[Insight] = []
    net = current["net_sales"] or ZERO

    if previous is None or compare_label is None or (previous["net_sales"] or ZERO) == 0:
        out.append(
            _ins(
                "headline",
                "neutral",
                f"{inr(net)} net sales in {days_in_period} days",
                "There is no earlier period with sales to compare against yet.",
                ["metric:net_sales@v1"],
            )
        )
        return out

    prev_net = previous["net_sales"] or ZERO
    delta = net - prev_net
    delta_pct = delta / prev_net * 100
    tone = "good" if delta > 0 else "bad" if delta < 0 else "neutral"
    verb = "rose" if delta > 0 else "fell" if delta < 0 else "was flat"
    body = f"Compared with the {compare_label}, net sales {verb} by {inr(abs(delta))}."
    if drivers and delta != 0:
        top = max(drivers.effects, key=lambda e: abs(e.amount))
        if abs(top.amount) > 0:
            body += (
                f" The biggest part of that is {top.label.lower()} "
                f"({inr(top.amount, signed=True)}). "
                "This is an attribution of the change, not proof of its cause."
            )
    out.append(
        _ins(
            "headline",
            tone,
            f"Net sales {verb} {pct(abs(delta_pct), signed=False)} to {inr(net)}"
            if delta != 0
            else f"Net sales held at {inr(net)}",
            body,
            ["metric:net_sales@v1", "drivers:price_volume_mix"],
        )
    )

    # Orders vs basket size: the two ingredients of net sales.
    o1, o0 = current["orders"] or ZERO, previous["orders"] or ZERO
    a1, a0 = current["aov"], previous["aov"]
    if o0 > 0 and a1 is not None and a0 is not None and a0 > 0:
        o_pct = (o1 - o0) / o0 * 100
        a_pct = (a1 - a0) / a0 * 100
        if abs(o_pct) >= 2 or abs(a_pct) >= 2:
            both_up = o_pct > 0 and a_pct > 0
            both_down = o_pct < 0 and a_pct < 0
            t = "good" if both_up else "bad" if both_down else "neutral"
            out.append(
                _ins(
                    "orders_vs_aov",
                    t,
                    f"Orders {pct(o_pct)}, average order value {pct(a_pct)}",
                    f"{int(o1):,} orders at {inr(a1)} each, against {int(o0):,} at {inr(a0)}. "
                    "Net sales is orders times average order value.",
                    ["metric:orders@v1", "metric:aov@v1"],
                )
            )

    # Which category accounts for most of the change.
    movers = [
        r for r in category_mix if r.get("share_of_change") is not None and r["delta"] is not None
    ]
    if movers and delta != 0:
        lead = max(movers, key=lambda r: abs(r["delta"]))
        share = lead["share_of_change"]
        if abs(lead["delta"]) > 0 and abs(share) >= 30 and len(movers) > 1:
            out.append(
                _ins(
                    f"category:{lead['key']}",
                    "bad" if lead["delta"] < 0 else "good",
                    f"{lead['label']} accounts for {pct(abs(share), signed=False)} of the change",
                    f"{lead['label']} moved {inr(lead['delta'], signed=True)} "
                    f"({inr(lead['previous_net'])} to {inr(lead['net'])}) out of a total change of "
                    f"{inr(delta, signed=True)}.",
                    [f"breakdown:category:{lead['key']}"],
                )
            )

    # Discounting.
    r1, r0 = current["discount_rate"], previous["discount_rate"]
    if r1 is not None and r0 is not None and abs(r1 - r0) >= 1:
        out.append(
            _ins(
                "discount_rate",
                "bad" if r1 > r0 else "good",
                f"Discount rate {'rose' if r1 > r0 else 'fell'} to {r1}%",
                f"It was {r0}% in the {compare_label}. "
                f"Discounts cost {inr(current['discounts'] or ZERO)} this period.",
                ["metric:discount_rate@v1", "drivers:discounts"],
            )
        )

    # Individual products behind the movement.
    if drivers and drivers.moves and delta != 0:
        movers_list = drivers.moves[:2] if delta < 0 else list(reversed(drivers.moves))[:2]
        movers_list = [m for m in movers_list if (m.delta < 0) == (delta < 0) and m.delta != 0]
        if movers_list:
            parts = [
                f"{m.name} ({inr(m.delta, signed=True)}, units {m.units_prev:g} to {m.units_cur:g})"
                for m in movers_list
            ]
            out.append(
                _ins(
                    "product_movers",
                    "bad" if delta < 0 else "good",
                    "Biggest product movers" if delta < 0 else "Strongest product gains",
                    "; ".join(parts) + ".",
                    [f"product:{m.sku}" for m in movers_list],
                )
            )
    return out
