"""Product classification and basket statistics on hand-computed inputs (no database)."""

from decimal import Decimal

from app.services.analytics.basket import pair_stats
from app.services.analytics.products import (
    ProductPerf,
    by_category,
    classify,
    overall_margin,
    portfolio_summary,
)

D = Decimal


def perf(
    key, category, units, gross, discount, cogs, covered, previous=None, lines=10, disc_lines=0
):
    return ProductPerf(
        key=key,
        name=f"Product {key}",
        category=category,
        units=D(units),
        gross=D(gross),
        discount=D(discount),
        cogs=D(cogs),
        covered_net=D(covered),
        lines=lines,
        discounted_lines=disc_lines,
        previous_net=None if previous is None else D(previous),
    )


# P1 star · P2 workhorse (discounts) · P3 puzzle · P4 dog · P5 no cost
ROWS = [
    perf("P1", "Staples", 100, 10000, 0, 5000, 10000, previous=12500),
    perf("P2", "Staples", 80, 4000, 400, 2400, 3600, previous=3000, lines=40, disc_lines=30),
    perf("P3", "Dairy", 4, 2000, 0, 800, 2000, previous=2000),
    perf("P4", None, 3, 300, 0, 270, 300, previous=0),
    perf("P5", None, 5, 400, 0, 0, 0),
]


def by_key(items):
    return {i["key"]: i for i in items}


def test_overall_margin_uses_only_costed_lines() -> None:
    # covered 15900, cogs 8470 -> profit 7430 -> 46.73 %
    assert overall_margin(ROWS) == D("46.73")


def test_abc_classes_and_cumulative_shares() -> None:
    items = classify(ROWS)
    assert [i["key"] for i in items] == ["P1", "P2", "P3", "P5", "P4"]  # by net sales
    k = by_key(items)
    assert k["P1"]["share"] == D("61.35")
    assert [k[x]["abc"] for x in ("P1", "P2", "P3", "P5", "P4")] == ["A", "A", "B", "C", "C"]
    assert k["P5"]["cumulative_share"] == D("98.16")
    assert abs(sum(i["share"] for i in items) - 100) <= D("0.05")


def test_portfolio_quadrants() -> None:
    k = by_key(classify(ROWS))
    assert k["P1"]["margin_pct"] == D("50.00")
    assert k["P1"]["quadrant"] == "Star"  # popular and above the 46.73 % overall margin
    assert k["P2"]["margin_pct"] == D("33.33")
    assert k["P2"]["quadrant"] == "Workhorse"  # popular, low margin
    assert k["P3"]["quadrant"] == "Puzzle"  # 60 % margin, few units
    assert k["P4"]["quadrant"] == "Dog"  # 10 % margin, few units
    assert k["P5"]["quadrant"] == "Unknown"  # no cost recorded
    assert k["P5"]["margin_pct"] is None
    assert k["P5"]["margin_amount"] is None


def test_discount_and_change_flags() -> None:
    k = by_key(classify(ROWS))
    assert k["P2"]["discount_rate"] == D("10.00")
    assert "discount_heavy" in k["P2"]["flags"]  # 10 % vs the 4.8 % cut-off (2x the 2.4 % overall)
    assert k["P2"]["discounted_line_share"] == D("75.00")
    assert "discount_heavy" not in k["P1"]["flags"]
    assert k["P1"]["change_pct"] == D("-20.00")
    assert "declining" in k["P1"]["flags"]
    assert k["P2"]["change_pct"] == D("20.00")
    assert "rising" in k["P2"]["flags"]
    assert k["P3"]["change_pct"] == D("0.00")
    assert k["P4"]["change_pct"] is None  # nothing sold before: no percentage
    assert "no_cost" in k["P5"]["flags"]


def test_category_rollup() -> None:
    cats = {c["category"]: c for c in by_category(ROWS)}
    assert cats["Staples"]["net"] == D("13600.00")
    assert cats["Staples"]["margin_pct"] == D("45.59")  # (13600 - 7400) / 13600
    assert cats["Staples"]["discount_rate"] == D("2.86")  # 400 / 14000
    assert cats["Staples"]["products"] == 2
    assert cats["Dairy"]["margin_pct"] == D("60.00")
    assert cats["Unspecified"]["net"] == D("700.00")
    assert cats["Unspecified"]["cost_coverage_pct"] == D("42.86")  # only P4 has a cost
    assert sum(c["share"] for c in cats.values()) - 100 <= D("0.05")


def test_portfolio_summary_counts() -> None:
    s = portfolio_summary(classify(ROWS))
    q = {x["quadrant"]: x["products"] for x in s["quadrants"]}
    assert q == {"Star": 1, "Workhorse": 1, "Puzzle": 1, "Dog": 1, "Unknown": 1}
    assert s["abc"] == {"A": 2, "B": 1, "C": 2}
    assert s["discount_heavy"] == 1
    assert (s["declining"], s["rising"]) == (1, 1)


def test_empty_and_single_product() -> None:
    assert classify([]) == []
    one = classify([perf("X", "C", 5, 500, 0, 300, 500)])
    assert one[0]["abc"] == "A"
    assert one[0]["share"] == D("100.00")
    assert one[0]["quadrant"] in {"Star", "Workhorse", "Puzzle", "Dog"}


# ------------------------------------------------------------------ basket

BASKETS = {
    **{f"o{i}": {"A", "B"} for i in range(1, 7)},
    "o7": {"A"},
    "o8": {"A", "C"},
    "o9": {"C"},
    "o10": {"D"},
}
NAMES = {"A": "Atta", "B": "Biscuits", "C": "Cola", "D": "Dal"}


def test_pair_support_confidence_and_lift() -> None:
    r = pair_stats(BASKETS, NAMES, min_orders=5)
    assert r["orders"] == 10
    assert len(r["pairs"]) == 1  # A+C has only one order, below the minimum
    p = r["pairs"][0]
    assert (p["a"], p["b"], p["orders"]) == ("A", "B", 6)
    assert p["support"] == D("60.00")
    assert p["confidence_a_to_b"] == D("75.00")  # 6 of the 8 Atta orders
    assert p["confidence_b_to_a"] == D("100.00")
    assert p["lift"] == D("1.25")  # 6 * 10 / (8 * 6)
    assert p["a_name"] == "Atta"


def test_minimum_orders_filter_and_lift_below_one() -> None:
    r = pair_stats(BASKETS, NAMES, min_orders=1)
    by_pair = {(p["a"], p["b"]): p for p in r["pairs"]}
    ac = by_pair[("A", "C")]
    assert ac["lift"] == D("0.63")  # 1 * 10 / (8 * 2) = 0.625
    assert ac["confidence_b_to_a"] == D("50.00")
    assert r["pairs_found"] == 2
    assert r["pairs"][0]["a"] == "A"
    assert r["pairs"][0]["b"] == "B"  # sorted by lift, highest first


def test_basket_summary_numbers() -> None:
    r = pair_stats(BASKETS, NAMES)
    assert r["multi_item_orders"] == 7
    assert r["multi_item_share"] == D("70.00")
    assert r["avg_items_per_order"] == D("1.70")


def test_top_products_cap_and_huge_baskets_are_handled() -> None:
    capped = pair_stats(BASKETS, NAMES, min_orders=1, top_products=2)
    assert {(p["a"], p["b"]) for p in capped["pairs"]} == {("A", "B")}  # only A and B kept
    huge = {"big": {f"S{i}" for i in range(30)}, **{f"o{i}": {"A", "B"} for i in range(6)}}
    r = pair_stats(huge, {}, min_orders=1)
    assert all(p["a"] in {"A", "B"} for p in r["pairs"])  # the 30-item basket is not paired


def test_empty_baskets() -> None:
    r = pair_stats({}, {})
    assert r["orders"] == 0
    assert r["pairs"] == []
    assert r["multi_item_share"] is None
