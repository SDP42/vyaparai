"""RFM scoring, segment rules, status and top-share on hand-computed inputs (no database)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.services.analytics.customers import (
    SEGMENTS,
    CustomerStat,
    percentile_scores,
    score_customers,
    segment_for,
    status_for,
    summarise,
    top_share,
)

D = Decimal
AS_OF = date(2026, 10, 31)


def test_percentile_scores_distinct_values_split_into_five_buckets() -> None:
    assert percentile_scores([10, 20, 30, 40, 50]) == [1, 2, 3, 4, 5]
    assert percentile_scores([50, 40, 30, 20, 10]) == [5, 4, 3, 2, 1]
    # lower is better (recency in days)
    assert percentile_scores([1, 2, 3, 4, 5], higher_is_better=False) == [5, 4, 3, 2, 1]


def test_percentile_scores_ties_share_a_score() -> None:
    assert percentile_scores([7, 7, 7, 7]) == [3, 3, 3, 3]
    scores = percentile_scores([1, 1, 5, 5, 9])
    assert scores[0] == scores[1]
    assert scores[2] == scores[3]
    assert scores[0] < scores[2] < scores[4]


def test_percentile_scores_edge_cases() -> None:
    assert percentile_scores([]) == []
    assert percentile_scores([42]) == [3]
    assert all(1 <= s <= 5 for s in percentile_scores([float(i) for i in range(100)]))


def test_every_rf_pair_maps_to_exactly_one_known_segment() -> None:
    first = AS_OF - timedelta(days=400)  # long ago, so "New" cannot trigger
    seen = set()
    for r in range(1, 6):
        for f in range(1, 6):
            for m in range(1, 6):
                seg = segment_for(r, f, m, orders=5, first_order=first, as_of=AS_OF)
                assert seg in SEGMENTS
                seen.add(seg)
    assert seen == set(SEGMENTS) - {"New"}


@pytest.mark.parametrize(
    ("r", "f", "m", "expected"),
    [
        (5, 5, 5, "Champions"),
        (4, 4, 1, "Champions"),
        (5, 3, 3, "Loyal"),
        (3, 3, 1, "Loyal"),
        (4, 2, 3, "Promising"),
        (5, 1, 1, "Promising"),
        (3, 2, 5, "Needs attention"),
        (2, 5, 5, "Can't lose"),
        (1, 4, 4, "Can't lose"),
        (2, 5, 3, "At risk"),
        (1, 3, 5, "At risk"),
        (2, 2, 5, "Hibernating"),
        (1, 1, 1, "Hibernating"),
    ],
)
def test_segment_rules(r: int, f: int, m: int, expected: str) -> None:
    long_ago = AS_OF - timedelta(days=300)
    assert segment_for(r, f, m, orders=6, first_order=long_ago, as_of=AS_OF) == expected


def test_new_segment_needs_one_order_and_a_recent_first_order() -> None:
    recent = AS_OF - timedelta(days=10)
    assert segment_for(5, 1, 1, orders=1, first_order=recent, as_of=AS_OF) == "New"
    assert segment_for(5, 1, 1, orders=2, first_order=recent, as_of=AS_OF) == "Promising"
    assert (
        segment_for(5, 1, 1, orders=1, first_order=AS_OF - timedelta(days=31), as_of=AS_OF)
        == "Promising"
    )
    # a frequent recent customer is still Champions, not New
    assert segment_for(5, 5, 5, orders=1, first_order=recent, as_of=AS_OF) == "Champions"


def test_status_thresholds() -> None:
    assert status_for(0) == "Active"
    assert status_for(30) == "Active"
    assert status_for(31) == "Cooling"
    assert status_for(44) == "Cooling"
    assert status_for(45) == "Lapsed"
    assert status_for(10, active_days=7, lapse_days=14) == "Cooling"


def stat(
    key: str, last_days_ago: int, orders: int, net: str, first_days_ago: int = 200
) -> CustomerStat:
    return CustomerStat(
        key=key,
        region="MH",
        city=None,
        first_order=AS_OF - timedelta(days=first_days_ago),
        last_order=AS_OF - timedelta(days=last_days_ago),
        orders=orders,
        net=D(net),
    )


def test_score_customers_end_to_end_on_a_small_book() -> None:
    stats = [
        stat("A", 1, 20, "9000"),  # best on everything
        stat("B", 5, 12, "6000"),
        stat("C", 20, 6, "3000"),
        stat("D", 50, 3, "1500"),
        stat("E", 120, 1, "300", first_days_ago=120),  # worst on everything
    ]
    rows = {r.key: r for r in score_customers(stats, AS_OF)}
    assert (rows["A"].r, rows["A"].f, rows["A"].m) == (5, 5, 5)
    assert (rows["E"].r, rows["E"].f, rows["E"].m) == (1, 1, 1)
    assert rows["A"].segment == "Champions"
    assert rows["E"].segment == "Hibernating"
    assert rows["A"].status == "Active"
    assert rows["D"].status == "Lapsed"  # 50 days
    assert rows["C"].status == "Active"  # 20 days
    assert rows["A"].recency_days == 1
    assert rows["B"].aov == D("500.00")


def test_summary_counts_reconcile_and_metrics() -> None:
    stats = [
        stat("A", 1, 20, "9000"),
        stat("B", 5, 12, "6000"),
        stat("C", 20, 6, "3000"),
        stat("D", 50, 3, "1500"),
        stat("E", 120, 1, "300", first_days_ago=120),
    ]
    s = summarise(score_customers(stats, AS_OF))
    assert s["customers"] == 5
    assert sum(seg["customers"] for seg in s["segments"]) == 5
    assert sum(seg["net"] for seg in s["segments"]) == s["net"] == D("19800.00")
    assert sum(s["status_counts"].values()) == 5
    assert sum(sum(row) for row in s["rfm_grid"]) == 5
    assert s["repeat_customers"] == 4  # everyone but E
    assert s["repeat_rate"] == D("80.00")
    assert s["revenue_per_customer"] == D("3960.00")
    assert s["lapsed_regulars"] == 1  # D: lapsed with >= 2 orders
    assert s["top_decile_share"] == D("45.45")  # best 1 of 5 customers: 9000 / 19800
    assert s["avg_orders_per_customer"] == D("8.4")


def test_top_share_edge_cases() -> None:
    assert top_share([]) is None
    assert top_share([D("0"), D("0")]) is None
    assert top_share([D("100")]) == D("100.00")
    assert top_share([D(i) for i in range(1, 11)]) == D("18.18")  # top 1 of 10: 10 / 55


def test_empty_book() -> None:
    assert score_customers([], AS_OF) == []
    s = summarise([])
    assert s["customers"] == 0
    assert s["repeat_rate"] is None
    assert s["revenue_per_customer"] is None
