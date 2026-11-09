"""The forecasting engine on panels whose right answer is known."""

from datetime import date, timedelta

import numpy as np

from app.services.forecasting import engine
from app.services.forecasting.panel import Panel

WEEK = [8.0, 8.0, 8.0, 9.0, 10.0, 16.0, 14.0]  # Monday first


def make_panel(days: int, *, seed: int = 1, noise: bool = True) -> Panel:
    rng = np.random.default_rng(seed)
    start = date(2026, 1, 5)  # a Monday
    dates = [start + timedelta(days=i) for i in range(days)]
    weekly = np.array([WEEK[d.weekday()] for d in dates])
    rows = [
        weekly + (rng.poisson(2, days) - 2 if noise else 0),
        np.full(days, 5.0) + (rng.poisson(1, days) - 1 if noise else 0),
        np.where(np.arange(days) % 9 == 0, 1.0, 0.0),
    ]
    y = np.clip(np.vstack(rows).astype(float), 0, None)
    return Panel(
        skus=["A", "B", "C"],
        names=["Weekly", "Steady", "Rare"],
        categories=[None, None, None],
        dates=dates,
        y=y,
        disc=np.zeros_like(y),
        stockout=np.zeros_like(y, dtype=bool),
        net_per_unit=np.array([100.0, 50.0, 200.0]),
    )


def test_too_little_history_gives_nothing() -> None:
    assert engine.run(make_panel(10)) is None


def test_short_history_uses_the_simple_method_and_says_so() -> None:
    res = engine.run(make_panel(40))
    assert res is not None
    assert {s.model for s in res.series} == {"seasonal_average"}
    assert any("simple recent-average" in w for w in res.summary["warnings"])


def test_forecast_is_sane_and_intervals_are_ordered() -> None:
    res = engine.run(make_panel(120))
    assert res is not None
    assert res.horizon == 14
    weekly = next(s for s in res.series if s.sku == "A")
    # true next-14-day total for the weekly product is 2 weeks x 73 = 146
    assert 120 <= weekly.units_next <= 175
    for s in res.series:
        assert all(v >= 0 for v in s.data["p10"])
        for lo, mid, hi in zip(s.data["p10"], s.data["p50"], s.data["p90"], strict=True):
            assert lo <= mid <= hi
        assert s.units_next_low <= s.units_next <= s.units_next_high
    tot = res.summary["totals"]["forecast"]
    assert len(tot) == 14
    assert all(t["p10"] <= t["p50"] <= t["p90"] for t in tot)


def test_weekday_shape_is_learned() -> None:
    res = engine.run(make_panel(120, noise=False))
    assert res is not None
    a = next(s for s in res.series if s.sku == "A")
    start = date.fromisoformat(a.data["fc_start"])
    by_dow = {(start + timedelta(days=k)).weekday(): v for k, v in enumerate(a.data["p50"][:7])}
    assert by_dow[5] > by_dow[1] * 1.4  # Saturday clearly above Tuesday


def test_runs_are_reproducible() -> None:
    a, b = engine.run(make_panel(100)), engine.run(make_panel(100))
    assert a is not None
    assert b is not None
    assert [s.data["p50"] for s in a.series] == [s.data["p50"] for s in b.series]


def test_interval_coverage_is_calibrated_and_reported() -> None:
    res = engine.run(make_panel(200))
    assert res is not None
    acc = res.summary["accuracy"]
    assert acc["windows"] == 3
    assert acc["interval_coverage_80"] >= 0.78  # calibrated to about 80 %
    assert acc["interval_scale"] >= 1.0


def test_stockout_days_do_not_teach_zero_demand() -> None:
    p = make_panel(150)
    p.y[1, 100:108] = 0.0  # the steady product vanishes for 8 days
    p.stockout[1, 100:108] = True
    res = engine.run(p)
    assert res is not None
    steady = next(s for s in res.series if s.sku == "B")
    assert steady.units_next > 14 * 3.5  # still forecast near 5 a day


def test_festive_peak_warning_only_when_history_is_short() -> None:
    short = make_panel(90)
    short.dates = [date(2026, 8, 1) + timedelta(days=i) for i in range(90)]  # ends 29 Oct 2026
    res = engine.run(short)
    assert res is not None
    assert any("festive season" in w for w in res.summary["warnings"])
