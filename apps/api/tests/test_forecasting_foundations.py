"""Forecasting foundations verified against hand-computed values."""

import pytest

from app.services.forecasting import backtest, baselines, demand, metrics

A = [10.0, 20.0, 30.0, 40.0]
F = [12.0, 18.0, 33.0, 36.0]  # errors: +2, -2, +3, -4


def test_error_metrics() -> None:
    assert metrics.mae(A, F) == pytest.approx(2.75)  # (2+2+3+4)/4
    assert metrics.rmse(A, F) == pytest.approx((33 / 4) ** 0.5)  # (4+4+9+16)/4
    assert metrics.wape(A, F) == pytest.approx(11 / 100)
    assert metrics.bias(A, F) == pytest.approx(-1 / 100)  # forecast 99 vs actual 100
    # smape: 2/11 + 2/19 + 3/31.5 + 4/38 each over 4
    expected = (2 / 11 + 2 / 19 + 3 / 31.5 + 4 / 38) / 4
    assert metrics.smape(A, F) == pytest.approx(expected)


def test_zero_demand_gives_none_not_a_crash() -> None:
    assert metrics.wape([0, 0], [1, 1]) is None
    assert metrics.bias([0, 0], [1, 1]) is None
    assert metrics.smape([0, 0], [0, 0]) is None


def test_mase_scales_by_naive_error() -> None:
    history = [1.0, 3.0, 2.0, 4.0]  # naive diffs: 2, 1, 2 -> mean 5/3
    assert metrics.mase([5.0], [6.0], history) == pytest.approx(1 / (5 / 3))
    assert metrics.mase([5.0], [6.0], [3.0, 3.0, 3.0]) is None  # flat history: undefined


def test_pinball_and_coverage() -> None:
    # q=0.9: under-forecast by 10 costs 9, over-forecast by 10 costs 1
    assert metrics.pinball([20.0], [10.0], 0.9) == pytest.approx(9.0)
    assert metrics.pinball([10.0], [20.0], 0.9) == pytest.approx(1.0)
    assert metrics.coverage([5, 15, 25], [0, 0, 0], [10, 10, 30]) == pytest.approx(2 / 3)
    with pytest.raises(ValueError, match="between 0 and 1"):
        metrics.pinball([1.0], [1.0], 1.5)


def test_forecast_value_added() -> None:
    assert metrics.forecast_value_added(0.8, 1.0) == pytest.approx(0.2)
    assert metrics.forecast_value_added(1.2, 1.0) == pytest.approx(-0.2)
    assert metrics.forecast_value_added(1.0, 0) is None


def test_length_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="same length"):
        metrics.mae([1.0], [1.0, 2.0])


WEEK = [5.0, 6.0, 7.0, 8.0, 9.0, 20.0, 25.0]


def test_baselines() -> None:
    hist = WEEK * 3
    assert baselines.naive(hist, 2) == [25.0, 25.0]
    assert baselines.seasonal_naive(hist, 9) == [*WEEK, 5.0, 6.0]
    assert baselines.moving_average([1, 2, 3, 4], 2, window=2) == [3.5, 3.5]
    assert baselines.drift([10, 12, 14], 2) == [16.0, 18.0]
    assert baselines.seasonal_average(WEEK * 2, 7) == WEEK
    # short history falls back instead of failing
    assert baselines.seasonal_naive([4.0, 5.0], 3) == [5.0, 5.0, 5.0]


def test_rolling_origin_never_peeks() -> None:
    series = [float(i) for i in range(60)]
    seen_lengths: list[int] = []

    def spy(history, horizon):  # type: ignore[no-untyped-def]
        seen_lengths.append(len(history))
        return [float(history[-1])] * horizon

    res = backtest.rolling_origin(series, spy, horizon=7, folds=3, min_train=28)
    assert [f.origin for f in res.folds] == [39, 46, 53]
    assert seen_lengths == [39, 46, 53]  # each fold trained only on what came before
    assert res.folds[-1].actual == series[53:60]  # last fold ends at the end of the series


def test_backtest_ranks_seasonal_data_correctly() -> None:
    series = WEEK * 12  # a perfectly weekly series
    rows = backtest.compare(
        series,
        {"naive": baselines.naive, "seasonal_naive": baselines.seasonal_naive},
        horizon=7,
        folds=4,
    )
    assert rows[0]["model"] == "seasonal_naive"
    assert rows[0]["wape"] == pytest.approx(0.0)
    assert rows[1]["fva"] is None  # reference error is 0, so a relative gain is undefined


def test_holdout_split_and_short_series() -> None:
    train, hold = backtest.split_holdout(list(range(10)), 3)
    assert train == list(range(7))
    assert hold == [7, 8, 9]
    with pytest.raises(ValueError, match="holdout"):
        backtest.split_holdout([1, 2], 2)
    with pytest.raises(ValueError, match="too short"):
        backtest.rolling_origin([1.0] * 10, baselines.naive, horizon=7, folds=2, min_train=28)


def test_demand_classification() -> None:
    assert demand.classify([10, 11, 9, 10, 12, 10, 11])["pattern"] == "smooth"
    assert demand.classify([1, 30, 2, 25, 1, 40, 3])["pattern"] == "erratic"
    assert demand.classify([0, 0, 5, 0, 0, 6, 0, 0, 5, 0])["pattern"] == "intermittent"
    assert demand.classify([0, 0, 1, 0, 0, 0, 50, 0, 0, 3])["pattern"] == "lumpy"
    assert demand.classify([0, 0, 0, 4])["pattern"] == "insufficient"
    adi = demand.classify([0, 0, 5, 0, 0, 6, 0, 0, 5, 0])["adi"]
    assert adi == pytest.approx(10 / 3, abs=0.001)


def test_stockout_suspects_only_interior_runs() -> None:
    s = [3, 4, 0, 0, 0, 0, 0, 0, 5, 4, 0, 0, 0, 0, 0]  # last run touches the end: not flagged
    assert demand.stockout_suspects(s, min_run=5) == [(2, 6)]
