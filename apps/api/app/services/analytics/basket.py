"""Basket analysis: which products are bought together.

For a pair A, B over N completed orders (pair = orders containing both):
    support = pair / N        confidence(A→B) = pair / orders(A)
    lift = pair × N / (orders(A) × orders(B))
(lift 1 = independent; above 1 = bought together more often than chance)
Only pairs seen in at least ``min_orders`` orders are returned: lift is unstable on rare items.
Association is not causation: the wording everywhere is "bought together".
"""

import uuid
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from typing import Any

from sqlalchemy.orm import Session

from app.models.commerce import Order, Product
from app.services.analytics.queries import _lines
from app.services.analytics.types import Filters

# Larger baskets are skipped for pairing: they dominate the work and add noise.
MAX_ITEMS_PER_ORDER = 25


def pair_stats(
    baskets: dict[str, set[str]],
    names: dict[str, str],
    *,
    min_orders: int = 5,
    limit: int = 20,
    top_products: int = 60,
) -> dict[str, Any]:
    n_orders = len(baskets)
    item_orders: Counter[str] = Counter()
    for items in baskets.values():
        item_orders.update(items)
    keep = {sku for sku, _ in item_orders.most_common(top_products)}

    pair_orders: Counter[tuple[str, str]] = Counter()
    for items in baskets.values():
        usable = sorted(items & keep)
        if 2 <= len(usable) <= MAX_ITEMS_PER_ORDER:
            pair_orders.update(combinations(usable, 2))

    rows = []
    for (a, b), n in pair_orders.items():
        if n < min_orders:
            continue
        lift = Decimal(n * n_orders) / Decimal(item_orders[a] * item_orders[b])
        rows.append(
            {
                "a": a,
                "a_name": names.get(a, a),
                "b": b,
                "b_name": names.get(b, b),
                "orders": n,
                "support": (Decimal(n) / n_orders * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "confidence_a_to_b": (Decimal(n) / item_orders[a] * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "confidence_b_to_a": (Decimal(n) / item_orders[b] * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                "lift": lift.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            }
        )
    rows.sort(key=lambda r: (r["lift"], r["orders"]), reverse=True)
    multi = sum(1 for items in baskets.values() if len(items) >= 2)
    total_items = sum(len(items) for items in baskets.values())
    return {
        "orders": n_orders,
        "multi_item_orders": multi,
        "multi_item_share": (
            (Decimal(multi) / n_orders * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if n_orders
            else None
        ),
        "avg_items_per_order": (
            (Decimal(total_items) / n_orders).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if n_orders
            else None
        ),
        "pairs": rows[:limit],
        "pairs_found": len(rows),
        "min_orders": min_orders,
    }


def basket_pairs(
    db: Session, ws: uuid.UUID, f: Filters, *, min_orders: int = 5, limit: int = 20
) -> dict[str, Any]:
    rows = db.execute(_lines([Order.id, Product.sku, Product.name], ws, f).distinct()).all()
    baskets: dict[str, set[str]] = {}
    names: dict[str, str] = {}
    for order_id, sku, name in rows:
        baskets.setdefault(str(order_id), set()).add(sku)
        names[sku] = name
    return pair_stats(baskets, names, min_orders=min_orders, limit=limit)
