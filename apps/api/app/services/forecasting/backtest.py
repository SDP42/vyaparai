"""Rolling-origin backtesting.

Each fold trains on everything before the origin and predicts the next ``horizon`` points, so a
model is never scored on data it has seen. The final ``holdout`` points are kept aside and only
scored once, after model choice (used for the single-use holdout in the ML plan).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.services.forecasting import metrics
from app.services.forecasting.baselines import Forecaster


@dataclass(slots=True)
class Fold:
    origin: int  # index of the first forecast point
    actual: list[float]
    forecast: list[float]


@dataclass(slots=True)
class BacktestResult:
    folds: list[Fold] = field(default_factory=list)

    def pooled(self) -> tuple[list[float], list[float]]:
        a = [x for f in self.folds for x in f.actual]
        p = [x for f in self.folds for x in f.forecast]
        return a, p

    def summary(self) -> dict[str, float | None]:
        a, p = self.pooled()
        return {
            "folds": float(len(self.folds)),
            "wape": metrics.wape(a, p),
            "mae": metrics.mae(a, p),
            "rmse": metrics.rmse(a, p),
            "bias": metrics.bias(a, p),
        }


def split_holdout(series: Sequence[float], holdout: int) -> tuple[list[float], list[float]]:
    if holdout < 0 or holdout >= len(series):
        raise ValueError("holdout must be smaller than the series")
    cut = len(series) - holdout
    return list(series[:cut]), list(series[cut:])


def rolling_origin(
    series: Sequence[float],
    forecaster: Forecaster,
    *,
    horizon: int,
    folds: int,
    step: int | None = None,
    min_train: int = 28,
) -> BacktestResult:
    """Run up to ``folds`` forecasts, the last one ending at the end of ``series``."""
    if horizon < 1 or folds < 1:
        raise ValueError("horizon and folds must be at least 1")
    step = step or horizon
    last_origin = len(series) - horizon
    result = BacktestResult()
    for k in range(folds - 1, -1, -1):
        origin = last_origin - k * step
        if origin < min_train:
            continue
        train = series[:origin]
        result.folds.append(
            Fold(
                origin=origin,
                actual=[float(x) for x in series[origin : origin + horizon]],
                forecast=forecaster(train, horizon),
            )
        )
    if not result.folds:
        raise ValueError("series too short for the requested folds, horizon and min_train")
    return result


def compare(
    series: Sequence[float],
    forecasters: dict[str, Forecaster],
    *,
    horizon: int,
    folds: int,
    reference: str = "seasonal_naive",
) -> list[dict[str, float | str | None]]:
    """Score several forecasters on the same folds; ``fva`` is the gain over ``reference``."""
    scored = {
        name: rolling_origin(series, fn, horizon=horizon, folds=folds).summary()
        for name, fn in forecasters.items()
    }
    ref = scored.get(reference, {}).get("wape")
    rows: list[dict[str, float | str | None]] = []
    for name, s in scored.items():
        w = s["wape"]
        rows.append(
            {
                **s,
                "model": name,
                "fva": None if ref is None or w is None else metrics.forecast_value_added(w, ref),
            }
        )
    return sorted(rows, key=lambda r: (r["wape"] is None, r["wape"] or 0.0))
