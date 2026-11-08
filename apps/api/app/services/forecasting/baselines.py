"""Baseline forecasters. A real model has to beat the seasonal naive one to be shipped."""

from collections.abc import Callable, Sequence

Forecaster = Callable[[Sequence[float], int], list[float]]


def naive(history: Sequence[float], horizon: int) -> list[float]:
    """Repeat the last observed value."""
    if not history:
        raise ValueError("history is empty")
    return [float(history[-1])] * horizon


def seasonal_naive(history: Sequence[float], horizon: int, season: int = 7) -> list[float]:
    """Repeat the value from one season ago (same weekday last week for daily data)."""
    if len(history) < season:
        return naive(history, horizon)
    cycle = history[-season:]
    return [float(cycle[i % season]) for i in range(horizon)]


def moving_average(history: Sequence[float], horizon: int, window: int = 28) -> list[float]:
    if not history:
        raise ValueError("history is empty")
    recent = history[-window:]
    return [sum(recent) / len(recent)] * horizon


def seasonal_average(
    history: Sequence[float], horizon: int, season: int = 7, cycles: int = 4
) -> list[float]:
    """Average of the same position over the last few seasons: smoother than seasonal naive."""
    if len(history) < season:
        return moving_average(history, horizon)
    use = min(cycles, len(history) // season)
    out = []
    for h in range(horizon):
        vals = [history[len(history) - season * k + (h % season)] for k in range(1, use + 1)]
        out.append(sum(vals) / len(vals))
    return out


def drift(history: Sequence[float], horizon: int) -> list[float]:
    """Straight line between the first and last observation, extended forward."""
    if len(history) < 2:
        return naive(history, horizon)
    slope = (history[-1] - history[0]) / (len(history) - 1)
    return [float(history[-1] + slope * (h + 1)) for h in range(horizon)]


BASELINES: dict[str, Forecaster] = {
    "naive": naive,
    "seasonal_naive": seasonal_naive,
    "moving_average": moving_average,
    "seasonal_average": seasonal_average,
    "drift": drift,
}
