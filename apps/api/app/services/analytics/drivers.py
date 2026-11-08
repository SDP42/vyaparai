"""Price-volume-mix driver analysis for net sales.

Convention (documented in docs/METRICS.md and research/PHASE-2-RESEARCH.md): for products sold in
both periods, with gross price g, units q and prior average gross price ḡ0:

    Volume = (Q1 - Q0) * ḡ0
    Mix    = Q1 * Σ (s1_i - s0_i) * (g0_i - ḡ0)      (s = share of units)
    Price  = Σ q1_i * (g1_i - g0_i)

Products sold in only one period form "new & discontinued"; discounts are their own effect. The
five effects sum exactly to the change in net sales. They are arithmetic attributions, not proof
of cause.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.services.analytics.types import ZERO, ProductAgg, money


@dataclass(slots=True)
class Effect:
    key: str
    label: str
    amount: Decimal
    explanation: str


@dataclass(slots=True)
class ProductMove:
    sku: str
    name: str
    category: str | None
    units_prev: Decimal
    units_cur: Decimal
    net_prev: Decimal
    net_cur: Decimal

    @property
    def delta(self) -> Decimal:
        return self.net_cur - self.net_prev


@dataclass(slots=True)
class DriverResult:
    net_change: Decimal
    effects: list[Effect]
    moves: list[ProductMove]
    continuing_products: int
    new_products: int
    discontinued_products: int


def price_volume_mix(cur: list[ProductAgg], prev: list[ProductAgg]) -> DriverResult:
    cur_map = {p.product_id: p for p in cur if p.units > 0}
    prev_map = {p.product_id: p for p in prev if p.units > 0}
    both = [pid for pid in cur_map if pid in prev_map]
    new_ids = [pid for pid in cur_map if pid not in prev_map]
    gone_ids = [pid for pid in prev_map if pid not in cur_map]

    q0 = sum((prev_map[i].units for i in both), ZERO)
    q1 = sum((cur_map[i].units for i in both), ZERO)
    g0_total = sum((prev_map[i].gross for i in both), ZERO)

    volume = mix = price = ZERO
    if q0 > 0 and q1 > 0:
        avg0 = g0_total / q0
        volume = (q1 - q0) * avg0
        for i in both:
            a, b = prev_map[i], cur_map[i]
            mix += (b.units / q1 - a.units / q0) * (a.gross_price - avg0)
            price += b.units * (b.gross_price - a.gross_price)
        mix *= q1
    else:
        # nothing sold in both periods: everything is new or discontinued
        both = []

    new_gone = sum((cur_map[i].gross for i in new_ids), ZERO) - sum(
        (prev_map[i].gross for i in gone_ids), ZERO
    )
    d1 = sum((p.discount for p in cur_map.values()), ZERO)
    d0 = sum((p.discount for p in prev_map.values()), ZERO)
    discount_effect = -(d1 - d0)

    n1 = sum((p.net for p in cur_map.values()), ZERO)
    n0 = sum((p.net for p in prev_map.values()), ZERO)
    net_change = n1 - n0

    raw = [
        ("volume", "Volume", volume, "Selling more or fewer units, at last period's average price"),
        ("mix", "Mix", mix, "Units shifting towards pricier or cheaper products"),
        ("price", "Price", price, "Change in billed price on this period's units"),
        (
            "new_discontinued",
            "New & discontinued",
            new_gone,
            "Products sold in only one of the two periods",
        ),
        (
            "discounts",
            "Discounts",
            discount_effect,
            "More discount given lowers net sales (and vice versa)",
        ),
    ]
    rounded = [money(a) for _, _, a, _ in raw]
    # Put the rounding residual (a few paise) into the largest effect so the parts add up exactly.
    residual = money(net_change) - sum(rounded, ZERO)
    if residual != 0:
        biggest = max(range(len(rounded)), key=lambda k: abs(rounded[k]))
        rounded[biggest] += residual
    effects = [Effect(k, label, rounded[i], expl) for i, (k, label, _, expl) in enumerate(raw)]

    moves: list[ProductMove] = []
    for pid in {*cur_map, *prev_map}:
        c, p = cur_map.get(pid), prev_map.get(pid)
        ref = c or p
        assert ref is not None  # noqa: S101 - pid comes from one of the two maps
        moves.append(
            ProductMove(
                sku=ref.sku,
                name=ref.name,
                category=ref.category,
                units_prev=p.units if p else ZERO,
                units_cur=c.units if c else ZERO,
                net_prev=p.net if p else ZERO,
                net_cur=c.net if c else ZERO,
            )
        )
    moves.sort(key=lambda m: m.delta)
    return DriverResult(
        net_change=money(net_change),
        effects=effects,
        moves=moves,
        continuing_products=len(both),
        new_products=len(new_ids),
        discontinued_products=len(gone_ids),
    )
