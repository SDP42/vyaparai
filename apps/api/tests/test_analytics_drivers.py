"""Price-volume-mix: hand-computed answers and the exact-sum identity."""

import random
from decimal import Decimal

import pytest

from app.services.analytics.compare import change, resolve_compare
from app.services.analytics.drivers import price_volume_mix
from app.services.analytics.metrics import BY_KEY
from app.services.analytics.types import ProductAgg, Totals, metric_values

D = Decimal


def agg(pid: str, units: int, price: str, discount: str = "0") -> ProductAgg:
    return ProductAgg(
        product_id=pid,
        sku=pid.upper(),
        name=f"Product {pid}",
        category="Cat",
        units=D(units),
        gross=D(units) * D(price),
        discount=D(discount),
    )


def by_key(result):
    return {e.key: e.amount for e in result.effects}


def test_hand_computed_volume_mix_price() -> None:
    # A: 100 @ 10 -> 120 @ 11 · B: 50 @ 20 -> 40 @ 20
    prev = [agg("a", 100, "10"), agg("b", 50, "20")]
    cur = [agg("a", 120, "11"), agg("b", 40, "20")]
    r = price_volume_mix(cur, prev)
    e = by_key(r)
    assert e["volume"] == D("133.33")
    assert e["mix"] == D("-133.33")
    assert e["price"] == D("120.00")
    assert e["new_discontinued"] == D("0.00")
    assert e["discounts"] == D("0.00")
    assert r.net_change == D("120.00")
    assert sum(e.values()) == r.net_change


def test_new_discontinued_and_discount_effects() -> None:
    prev = [agg("a", 100, "10", "50"), agg("b", 50, "20"), agg("d", 20, "5")]
    cur = [agg("a", 120, "11", "80"), agg("b", 40, "20"), agg("c", 10, "30")]
    r = price_volume_mix(cur, prev)
    e = by_key(r)
    assert e["new_discontinued"] == D("200.00")  # +300 new C, -100 gone D
    assert e["discounts"] == D("-30.00")  # discounts rose 50 -> 80
    # net: prev = 2100 - 50 = 2050; cur = (1320 + 800 + 300) - 80 = 2340; change = 290
    assert r.net_change == D("290.00")
    assert sum(e.values()) == r.net_change
    assert (r.continuing_products, r.new_products, r.discontinued_products) == (2, 1, 1)
    assert r.moves[0].delta <= r.moves[-1].delta  # sorted ascending


def test_no_overlap_means_everything_is_new_or_discontinued() -> None:
    r = price_volume_mix([agg("c", 10, "30")], [agg("d", 20, "5")])
    e = by_key(r)
    assert e["volume"] == e["mix"] == e["price"] == D("0.00")
    assert e["new_discontinued"] == D("200.00")
    assert sum(e.values()) == r.net_change == D("200.00")


def test_empty_periods() -> None:
    r = price_volume_mix([], [])
    assert r.net_change == D("0.00")
    assert all(e.amount == D("0.00") for e in r.effects)


@pytest.mark.parametrize("seed", range(25))
def test_effects_always_sum_to_the_change(seed: int) -> None:
    rnd = random.Random(seed)  # noqa: S311 - deterministic test data, not security
    ids = [f"p{i}" for i in range(rnd.randint(1, 12))]

    def period() -> list[ProductAgg]:
        out = []
        for pid in ids:
            if rnd.random() < 0.8:
                units = rnd.randint(1, 500)
                price = f"{rnd.uniform(5, 900):.2f}"
                gross = D(units) * D(price)
                disc = f"{float(gross) * rnd.uniform(0, 0.2):.2f}"
                out.append(agg(pid, units, price, disc))
        return out

    prev, cur = period(), period()
    r = price_volume_mix(cur, prev)
    expected = sum((p.net for p in cur), D(0)) - sum((p.net for p in prev), D(0))
    assert abs(r.net_change - expected) <= D("0.01")
    assert (
        sum((e.amount for e in r.effects), D(0)) == r.net_change
    )  # exact after residual placement


def test_metric_values_hand_computed() -> None:
    t = Totals(
        gross=D("1000"),
        discount=D("100"),
        units=D("50"),
        cogs=D("540"),
        covered_net=D("900"),
        orders=10,
        anonymous_orders=3,
    )
    v = metric_values(t)
    assert v["net_sales"] == D("900.00")
    assert v["aov"] == D("90.00")
    assert v["units_per_order"] == D("5.00")
    assert v["discount_rate"] == D("10.00")
    assert v["gross_profit"] == D("360.00")
    assert v["gross_margin"] == D("40.00")
    assert v["cost_coverage"] == D("100.00")
    assert v["anonymous_order_share"] == D("30.00")


def test_metrics_are_none_not_infinity_when_undefined() -> None:
    v = metric_values(Totals())
    assert v["aov"] is None
    assert v["gross_margin"] is None
    assert v["discount_rate"] is None
    assert v["net_sales"] == D("0.00")


def test_change_handles_zero_previous_and_points() -> None:
    net = BY_KEY["net_sales"]
    assert change(net, D("120"), D("100")) == (D("20.00"), D("20.00"))
    assert change(net, D("50"), D("0")) == (D("50.00"), None)  # never infinity
    assert change(net, None, D("1")) == (None, None)
    margin = BY_KEY["gross_margin"]
    assert change(margin, D("40"), D("35")) == (D("5.00"), None)  # percentage points


def test_comparison_ranges() -> None:
    from datetime import date

    assert resolve_compare(date(2026, 10, 1), date(2026, 10, 7), "none") is None
    # previous period: same 7 days immediately before
    assert resolve_compare(date(2026, 10, 8), date(2026, 10, 14), "previous_period") == (
        date(2026, 10, 1),
        date(2026, 10, 7),
    )
    # same weekdays last year = 364 days earlier, so the weekday is preserved
    prev = resolve_compare(date(2026, 10, 8), date(2026, 10, 14), "previous_year")
    assert prev == (date(2025, 10, 9), date(2025, 10, 15))
    assert prev is not None
    assert prev[0].weekday() == date(2026, 10, 8).weekday()
