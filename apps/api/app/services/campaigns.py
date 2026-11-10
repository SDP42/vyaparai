"""Segment campaigns: who to contact, what to say, which offer is safe, what it might cost.

Nothing here sends a message. It prepares an audience, an offer that keeps a margin floor, message
text, a holdout group for honest measurement, and a CSV for manual sending (docs/research/
CAMPAIGNS-PLAN.md). Consent is not stored yet, so every row says ``not_recorded``.
"""

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.commerce import Customer, Order, OrderItem, OrderStatus, Product
from app.models.workspace import Workspace
from app.services.analytics import customers, intelligence, products
from app.services.analytics.types import ZERO, Filters, dec, money

Language = Literal["en", "hinglish"]
D = Decimal
CHUNK = 500
ASSUMPTION = (
    "Redemption rates are assumptions to plan with, not predictions. The holdout group measures "
    "what the campaign really achieves."
)
CONSENT_NOTE = (
    "Only message customers who agreed to hear from you. Record consent, with how and when, on the "
    "Campaigns > Consent page; a STOP is final until the customer agrees again."
)


class UnknownSegmentError(AppError):
    status_code = 422
    code = "unknown_segment"


@dataclass(frozen=True, slots=True)
class Play:
    kind: str  # reward | grow | welcome | nudge | winback
    goal: str
    idea: str
    max_discount: int  # default ceiling, in percent
    redemption: Decimal  # assumed share of contacted customers who buy, in percent


PLAYS: dict[str, Play] = {
    "Champions": Play(
        "reward",
        "Keep and reward your best customers",
        "Thank them; early access to new stock. No discount needed.",
        0,
        D(20),
    ),
    "Loyal": Play(
        "grow",
        "Raise how often they buy",
        "Suggest what goes with their usual items; small, margin-checked offer.",
        5,
        D(12),
    ),
    "New": Play(
        "welcome",
        "Win a second order within 30 days",
        "A welcome-back note while the first visit is fresh.",
        10,
        D(20),
    ),
    "Promising": Play(
        "grow",
        "Turn recent buyers into regulars",
        "Remind them of their favourites; small offer on a second basket.",
        5,
        D(12),
    ),
    "Needs attention": Play(
        "nudge",
        "Re-engage before they drift",
        "A reminder of their usual products; optional small offer.",
        8,
        D(10),
    ),
    "Can't lose": Play(
        "winback",
        "Win back big spenders",
        "A personal message first; a stronger offer only if they stay quiet.",
        15,
        D(10),
    ),
    "At risk": Play(
        "winback",
        "Win back former regulars",
        "Reach out soon after their usual gap has passed; escalate the offer.",
        12,
        D(8),
    ),
    "Hibernating": Play(
        "winback",
        "One last win-back, then stop",
        "A single capped offer; stop contacting if there is no reply.",
        15,
        D(4),
    ),
}

MESSAGES: dict[str, dict[str, Any]] = {
    "en": {
        "offer": {
            "winback": "Hello! It has been a while since your last visit to {shop}. Your usual {product} is {d}% off for the next {days} days.",
            "welcome": "Thanks for shopping at {shop}! Come back within {days} days and get {d}% off {product}.",
            "grow": "Hello from {shop}! Take {d}% off {product} in the next {days} days.",
            "nudge": "Hello from {shop}! Take {d}% off {product} in the next {days} days.",
            "reward": "Thank you for being one of {shop}'s best customers! Your favourite {product} is always set aside for you.",
        },
        "value": {
            "winback": "Hello! It has been a while since your last visit to {shop}. Your usual {product} is back in stock and waiting for you.",
            "welcome": "Thanks for shopping at {shop}! Your {product} is ready whenever you need it again.",
            "grow": "Hello from {shop}! Your usual {product} is in stock. Drop by whenever you like.",
            "nudge": "Hello from {shop}! Your usual {product} is in stock. Drop by whenever you like.",
            "reward": "Thank you for being one of {shop}'s best customers! Your favourite {product} is always set aside for you.",
        },
        "stop": "Reply STOP to opt out.",
    },
    "hinglish": {
        "offer": {
            "winback": "Hello! {shop} mein aapko kaafi time ho gaya. Aapka usual {product} agle {days} din {d}% off hai.",
            "welcome": "{shop} se shopping ke liye thanks! {days} din ke andar wapas aaiye, {product} par {d}% off milega.",
            "grow": "Hello from {shop}! Agle {days} din {product} par {d}% off lijiye.",
            "nudge": "Hello from {shop}! Agle {days} din {product} par {d}% off lijiye.",
            "reward": "{shop} ke best customers mein se ek hone ke liye thanks! Aapka favourite {product} hamesha aapke liye alag rakha hai.",
        },
        "value": {
            "winback": "Hello! {shop} mein aapko kaafi time ho gaya. Aapka usual {product} wapas stock mein hai.",
            "welcome": "{shop} se shopping ke liye thanks! Aapka {product} jab chahiye tab ready hai.",
            "grow": "Hello from {shop}! Aapka usual {product} stock mein hai. Jab marzi aaiye.",
            "nudge": "Hello from {shop}! Aapka usual {product} stock mein hai. Jab marzi aaiye.",
            "reward": "{shop} ke best customers mein se ek hone ke liye thanks! Aapka favourite {product} hamesha aapke liye alag rakha hai.",
        },
        "stop": "Band karne ke liye STOP likhiye.",
    },
}


# ------------------------------------------------------------------ pure logic


def max_safe_discount(margin_pct: Decimal | None, floor_pct: Decimal) -> Decimal:
    """Largest discount (percent) that keeps margin at or above the floor.

    Unit cost c and net price p give margin m = 1 - c/p. After discount d the margin is
    1 - (1-m)/(1-d). Requiring it to stay at least f gives d <= 1 - (1-m)/(1-f).
    """
    if margin_pct is None or floor_pct >= 100:
        return ZERO
    m, f = margin_pct / 100, floor_pct / 100
    d = (1 - (1 - m) / (1 - f)) * 100
    return max(ZERO, d)


def margin_after(margin_pct: Decimal, discount_pct: Decimal) -> Decimal:
    m, d = margin_pct / 100, discount_pct / 100
    return ((1 - (1 - m) / (1 - d)) * 100).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def whole(x: Decimal) -> Decimal:
    return x.quantize(D(1), rounding=ROUND_DOWN)


def in_holdout(segment: str, customer_key: str, pct: int) -> bool:
    """Stable choice, so the same customer is in the same group every time the plan is made."""
    if pct <= 0:
        return False
    h = int.from_bytes(hashlib.sha256(f"{segment}|{customer_key}".encode()).digest()[:4], "big")
    return h % 100 < pct


def message(
    kind: str, language: Language, shop: str, product: str, discount: Decimal, days: int
) -> str:
    t = MESSAGES[language]
    body = (t["offer"] if discount > 0 else t["value"])[kind]
    text = body.format(shop=shop, product=product, d=int(discount), days=days)
    return f"{text} {t['stop']}"


def ladder(play: Play, discount: Decimal) -> list[dict[str, Any]]:
    """Escalate: value first, a small offer next, the strongest last (never open with the deepest)."""
    if play.kind == "reward" or discount <= 0:
        return [{"step": 1, "name": "Friendly message", "discount_pct": 0, "when": "Day 0"}]
    half = max(D(1), whole(discount / 2))
    steps = [{"step": 1, "name": "Friendly message", "discount_pct": 0, "when": "Day 0"}]
    if half < discount:
        steps.append(
            {
                "step": 2,
                "name": "Small offer",
                "discount_pct": int(half),
                "when": "Day 7, if no purchase",
            }
        )
    steps.append(
        {
            "step": len(steps) + 1,
            "name": "Best offer",
            "discount_pct": int(discount),
            "when": "Day 14, if no purchase",
        }
    )
    return steps


# ------------------------------------------------------------------ data


@dataclass(slots=True)
class Audience:
    key: str
    city: str | None
    last_order: date
    recency_days: int
    orders: int
    net: Decimal
    overdue: Decimal | None
    favourites: list[tuple[str, str, Decimal]]  # sku, name, units


def _chunks(xs: list[str]) -> list[list[str]]:
    return [xs[i : i + CHUNK] for i in range(0, len(xs), CHUNK)]


def _favourites_and_gaps(
    db: Session, ws: uuid.UUID, keys: list[str], start: date, end: date
) -> tuple[dict[str, list[tuple[str, str, Decimal]]], dict[str, list[date]]]:
    units: dict[str, dict[str, tuple[str, Decimal]]] = defaultdict(dict)
    days: dict[str, set[date]] = defaultdict(set)
    base_where = (
        OrderItem.workspace_id == ws,
        Order.workspace_id == ws,
        Order.status == OrderStatus.COMPLETED,
        Order.business_date >= start,
        Order.business_date <= end,
    )
    for part in _chunks(keys):
        stmt = (
            select(
                Customer.external_key,
                Product.sku,
                Product.name,
                OrderItem.quantity,
                Order.business_date,
            )
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .join(Product, Product.id == OrderItem.product_id)
            .join(Customer, Customer.id == Order.customer_id)
            .where(*base_where, Customer.external_key.in_(part))
        )
        for key, sku, name, qty, day in db.execute(stmt):
            old = units[key].get(sku, (name, ZERO))[1]
            units[key][sku] = (name, old + dec(qty))
            days[key].add(day)
    fav = {
        k: sorted(((s, n, u) for s, (n, u) in v.items()), key=lambda t: (-t[2], t[0]))
        for k, v in units.items()
    }
    return fav, {k: sorted(v) for k, v in days.items()}


def build_audience(
    db: Session, ws: uuid.UUID, rows: list[customers.CustomerRow], start: date, end: date
) -> list[Audience]:
    fav, order_days = _favourites_and_gaps(db, ws, [r.key for r in rows], start, end)
    out = []
    for r in sorted(rows, key=lambda x: (-x.net, x.key)):
        ds = order_days.get(r.key, [])
        gap = D((ds[-1] - ds[0]).days) / (len(ds) - 1) if len(ds) >= 2 else None
        overdue = (
            (D(r.recency_days) / gap).quantize(D("0.01"), rounding=ROUND_HALF_UP) if gap else None
        )
        out.append(
            Audience(
                r.key,
                r.city,
                r.last_order,
                r.recency_days,
                r.orders,
                r.net,
                overdue,
                fav.get(r.key, []),
            )
        )
    return out


# ------------------------------------------------------------------ plans


def playbook(
    db: Session, workspace: Workspace, as_of: date | None, lookback: int
) -> list[dict[str, Any]]:
    _, rows = intelligence.scored(db, workspace, as_of, lookback, 30, 30, 45)
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.segment] += 1
    return [
        {
            "segment": s,
            "help": customers.SEGMENT_HELP[s],
            "kind": p.kind,
            "goal": p.goal,
            "idea": p.idea,
            "customers": counts.get(s, 0),
            "default_max_discount": p.max_discount,
            "assumed_redemption": p.redemption,
        }
        for s, p in PLAYS.items()
    ]


def plan(
    db: Session,
    workspace: Workspace,
    *,
    segment: str,
    as_of: date | None,
    lookback: int,
    max_discount: int | None,
    margin_floor: int,
    holdout_pct: int,
    language: Language,
    valid_days: int,
) -> dict[str, Any]:
    if segment not in PLAYS:
        raise UnknownSegmentError("Unknown segment")
    play = PLAYS[segment]
    cap = D(play.max_discount if max_discount is None else max_discount)
    day, rows = intelligence.scored(db, workspace, as_of, lookback, 30, 30, 45)
    rows = [r for r in rows if r.segment == segment]
    start = day - timedelta(days=lookback - 1)
    audience = build_audience(db, workspace.id, rows, start, day)

    perf = {
        p.key: p
        for p in products.product_perf(db, workspace.id, Filters(date_from=start, date_to=day))
    }
    floor = D(margin_floor)

    def offer_for(sku: str) -> dict[str, Any] | None:
        p = perf.get(sku)
        if p is None or p.units <= 0:
            return None
        margin = products.pct(p.covered_net - p.cogs, p.covered_net) if p.covered_net else None
        safe = max_safe_discount(margin, floor)
        chosen = min(cap, whole(safe)) if margin is not None else ZERO
        return {
            "sku": sku,
            "name": p.name,
            "price": money(p.net / p.units),
            "margin_pct": margin,
            "safe_discount_pct": whole(safe) if margin is not None else None,
            "discount_pct": chosen,
            "margin_after_pct": margin_after(margin, chosen) if margin is not None else None,
            "flag": (
                "no_cost"
                if margin is None
                else "no_safe_discount"
                if chosen <= 0 and cap > 0
                else None
            ),
        }

    seg_units: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for a in audience:
        for sku, _n, u in a.favourites[:2]:
            seg_units[sku] += u
    offers: list[dict[str, Any]] = []
    for sku, units in sorted(seg_units.items(), key=lambda kv: (-kv[1], kv[0]))[:8]:
        o = offer_for(sku)
        if o:
            offers.append({**o, "segment_units": units})
    by_sku = {o["sku"]: o for o in offers}

    contact_rows: list[dict[str, Any]] = []
    for a in audience:
        pick = next(
            (f for f in a.favourites if (offer_for(f[0]) or {}).get("discount_pct", ZERO) > 0), None
        )
        fav = pick or (a.favourites[0] if a.favourites else None)
        o = by_sku.get(fav[0]) if fav else None
        if fav and o is None:
            o = offer_for(fav[0])
        disc = D(o["discount_pct"]) if o else ZERO
        held = in_holdout(segment, a.key, holdout_pct)
        name = fav[1] if fav else "favourites"
        contact_rows.append(
            {
                "key": a.key,
                "city": a.city,
                "last_order": a.last_order,
                "recency_days": a.recency_days,
                "orders": a.orders,
                "net": a.net,
                "overdue_ratio": a.overdue,
                "reason": (
                    f"{a.overdue}× their usual gap between orders"
                    if a.overdue
                    else f"{a.recency_days} days since last order"
                ),
                "product": name,
                "discount_pct": disc,
                "holdout": held,
                "consent_status": "not_recorded",
                "message": message(play.kind, language, workspace.name, name, disc, valid_days),
            }
        )

    contact = [c for c in contact_rows if not c["holdout"]]
    n_contact = len(contact)
    orders = sum(a.orders for a in audience)
    aov = money(sum((a.net for a in audience), ZERO) / orders) if orders else ZERO
    redeemers = (D(n_contact) * play.redemption / 100).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    avg_disc = sum((D(c["discount_pct"]) for c in contact), ZERO) / n_contact if n_contact else ZERO
    sales = money(redeemers * aov)
    given = money(sales * avg_disc / (100 - avg_disc)) if avg_disc < 100 else ZERO

    warnings: list[str] = []
    if not audience:
        warnings.append("No customers are in this segment right now.")
    elif len(audience) < 10 and holdout_pct > 0:
        warnings.append("A small segment makes the holdout group tiny; results will be noisy.")
    if play.kind != "reward" and offers and all(o["flag"] == "no_cost" for o in offers):
        warnings.append(
            "No cost is recorded for these products, so only value messages are suggested."
        )
    elif any(o["flag"] == "no_safe_discount" for o in offers):
        warnings.append(
            "Some products cannot be discounted without dropping below your margin floor."
        )

    return {
        "segment": segment,
        "kind": play.kind,
        "goal": play.goal,
        "idea": play.idea,
        "as_of": day,
        "audience": {
            "total": len(audience),
            "contact": n_contact,
            "holdout": len(audience) - n_contact,
        },
        "params": {
            "max_discount": int(cap),
            "margin_floor": margin_floor,
            "holdout_pct": holdout_pct,
            "language": language,
            "valid_days": valid_days,
        },
        "ladder": ladder(play, cap),
        "offers": offers,
        "projection": {
            "assumed_redemption_pct": play.redemption,
            "expected_redeemers": redeemers,
            "avg_order_value": aov,
            "expected_sales": sales,
            "avg_discount_pct": avg_disc.quantize(D("0.01"), rounding=ROUND_HALF_UP),
            "expected_discount_given": given,
            "note": ASSUMPTION,
        },
        "consent_note": CONSENT_NOTE,
        "warnings": warnings,
        "rows": contact_rows,
        "currency": workspace.currency,
    }
