"""Forecast error metrics. All take equal-length actual and forecast sequences."""

from collections.abc import Sequence
from math import sqrt


def _check(actual: Sequence[float], forecast: Sequence[float]) -> None:
    if len(actual) != len(forecast):
        raise ValueError("actual and forecast must have the same length")
    if not actual:
        raise ValueError("need at least one point")


def mae(actual: Sequence[float], forecast: Sequence[float]) -> float:
    _check(actual, forecast)
    return sum(abs(a - f) for a, f in zip(actual, forecast, strict=True)) / len(actual)


def rmse(actual: Sequence[float], forecast: Sequence[float]) -> float:
    _check(actual, forecast)
    return sqrt(sum((a - f) ** 2 for a, f in zip(actual, forecast, strict=True)) / len(actual))


def wape(actual: Sequence[float], forecast: Sequence[float]) -> float | None:
    """Weighted absolute percentage error: sum|error| / sum(actual). Headline metric."""
    _check(actual, forecast)
    total = sum(abs(a) for a in actual)
    if total == 0:
        return None
    return sum(abs(a - f) for a, f in zip(actual, forecast, strict=True)) / total


def smape(actual: Sequence[float], forecast: Sequence[float]) -> float | None:
    """Symmetric MAPE in [0, 2]; points where both are zero are skipped."""
    _check(actual, forecast)
    terms = [
        abs(a - f) / ((abs(a) + abs(f)) / 2)
        for a, f in zip(actual, forecast, strict=True)
        if abs(a) + abs(f) > 0
    ]
    return sum(terms) / len(terms) if terms else None


def bias(actual: Sequence[float], forecast: Sequence[float]) -> float | None:
    """(sum forecast - sum actual) / sum actual. Positive = over-forecasting."""
    _check(actual, forecast)
    total = sum(actual)
    if total == 0:
        return None
    return (sum(forecast) - total) / total


def mase(
    actual: Sequence[float], forecast: Sequence[float], history: Sequence[float], season: int = 1
) -> float | None:
    """MAE scaled by the in-sample seasonal-naive MAE. Below 1 beats the seasonal-naive method."""
    _check(actual, forecast)
    if len(history) <= season:
        return None
    scale = sum(abs(history[i] - history[i - season]) for i in range(season, len(history))) / (
        len(history) - season
    )
    if scale == 0:
        return None
    return mae(actual, forecast) / scale


def pinball(actual: Sequence[float], forecast: Sequence[float], quantile: float) -> float:
    """Pinball (quantile) loss for one quantile forecast."""
    _check(actual, forecast)
    if not 0 < quantile < 1:
        raise ValueError("quantile must be between 0 and 1")
    loss = 0.0
    for a, f in zip(actual, forecast, strict=True):
        d = a - f
        loss += quantile * d if d >= 0 else (quantile - 1) * d
    return loss / len(actual)


def coverage(actual: Sequence[float], lower: Sequence[float], upper: Sequence[float]) -> float:
    """Share of actuals inside [lower, upper]."""
    _check(actual, lower)
    _check(actual, upper)
    inside = sum(1 for a, lo, hi in zip(actual, lower, upper, strict=True) if lo <= a <= hi)
    return inside / len(actual)


def forecast_value_added(model_error: float, baseline_error: float) -> float | None:
    """Share of the baseline error the model removes: 0.2 = 20 % better. Negative = worse."""
    if baseline_error == 0:
        return None
    return (baseline_error - model_error) / baseline_error
