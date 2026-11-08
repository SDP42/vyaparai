"""Plain data types shared by the analytics engine."""

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

ZERO = Decimal("0")
CENT = Decimal("0.01")
UNSPECIFIED = "Unspecified"

Dimension = Literal["category", "channel", "region", "product"]
CompareMode = Literal["previous_period", "previous_year", "none"]
Granularity = Literal["day", "week", "month"]


def money(x: Any) -> Decimal:
    """Round any number-like to 2 decimals using Decimal (never float math on money)."""
    if x is None:
        return ZERO
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def dec(x: Any) -> Decimal:
    """A Decimal that keeps units precision (quantities can have 3 decimals)."""
    return ZERO if x is None else Decimal(str(x))


@dataclass(frozen=True, slots=True)
class Filters:
    """An inclusive business-date range plus optional dimension filters."""

    date_from: date
    date_to: date
    categories: tuple[str, ...] = ()
    channels: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    skus: tuple[str, ...] = ()

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1

    def with_range(self, date_from: date, date_to: date) -> "Filters":
        return replace(self, date_from=date_from, date_to=date_to)

    def as_dict(self) -> dict[str, Any]:
        return {
            "categories": list(self.categories),
            "channels": list(self.channels),
            "regions": list(self.regions),
            "skus": list(self.skus),
        }


@dataclass(slots=True)
class ProductAgg:
    product_id: str
    sku: str
    name: str
    category: str | None
    units: Decimal = ZERO
    gross: Decimal = ZERO
    discount: Decimal = ZERO
    cogs: Decimal = ZERO
    covered_net: Decimal = ZERO

    @property
    def net(self) -> Decimal:
        return self.gross - self.discount

    @property
    def gross_price(self) -> Decimal:
        """Average billed (pre-discount) price per unit."""
        return self.gross / self.units if self.units else ZERO


@dataclass(slots=True)
class Totals:
    """Everything the headline metrics need, for one period."""

    gross: Decimal = ZERO
    discount: Decimal = ZERO
    units: Decimal = ZERO
    cogs: Decimal = ZERO
    covered_net: Decimal = ZERO
    orders: int = 0
    active_customers: int = 0
    new_customers: int = 0
    repeat_customers: int = 0
    anonymous_orders: int = 0
    days_with_data: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def net(self) -> Decimal:
        return self.gross - self.discount


def metric_values(t: Totals) -> dict[str, Decimal | None]:
    """Compute every registry metric from the period's totals. ``None`` means 'not defined'."""
    net = t.net
    gp = t.covered_net - t.cogs

    def ratio(a: Decimal, b: Decimal, scale: Decimal = Decimal(1)) -> Decimal | None:
        return None if b == 0 else (a / b * scale)

    hundred = Decimal(100)
    return {
        "gross_sales": money(t.gross),
        "discounts": money(t.discount),
        "net_sales": money(net),
        "orders": Decimal(t.orders),
        "units": dec(t.units).quantize(Decimal("0.001")).normalize(),
        "aov": _m(ratio(net, Decimal(t.orders))),
        "units_per_order": _m(ratio(t.units, Decimal(t.orders))),
        "discount_rate": _m(ratio(t.discount, t.gross, hundred)),
        "cogs": money(t.cogs),
        "gross_profit": money(gp),
        "gross_margin": _m(ratio(gp, t.covered_net, hundred)),
        "cost_coverage": _m(ratio(t.covered_net, net, hundred)),
        "active_customers": Decimal(t.active_customers),
        "new_customers": Decimal(t.new_customers),
        "repeat_customers": Decimal(t.repeat_customers),
        "anonymous_order_share": _m(ratio(Decimal(t.anonymous_orders), Decimal(t.orders), hundred)),
    }


def _m(x: Decimal | None) -> Decimal | None:
    return None if x is None else x.quantize(CENT, rounding=ROUND_HALF_UP)
