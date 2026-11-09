"""The forecasting engine: global LightGBM, a seasonal-average fallback, backtests and intervals.

Design (docs/research/PHASE-4-BENCHMARK.md):
- One LightGBM model across all products (direct multi-horizon: the step ahead is a feature).
- Rolling-origin backtests pick, per product, between LightGBM and a seasonal average. A model must
  also be judged against a seasonal-naive baseline, and the run reports whether it beat it.
- Intervals are conformal: empirical quantiles of the model's own backtest errors, checked by
  leaving each backtest window out in turn.
- Future promotions are unknown, so forecasts assume none; this is stated in the model card.
"""

import math
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray

from app.services.forecasting.demand import classify
from app.services.forecasting.panel import Arr, Panel, clean

H = 14
MIN_DAYS_FORECAST = 14  # below this there is nothing sensible to say
MIN_DAYS_GBM = 56  # LightGBM needs lag windows and some training origins
FIRST_BACKTEST_ORIGIN = 42
MAX_WINDOWS = 3
MAX_TRAIN_ROWS = 150_000
LAGS = (1, 2, 3, 7, 14, 21, 28)

# Festive-season peaks move each year, so they are a dated table, not a formula.
FESTIVE_PEAKS = (date(2024, 11, 1), date(2025, 10, 20), date(2026, 11, 8), date(2027, 10, 29))
PEAK_WARN_DAYS = 10
TARGET_COVERAGE = 0.80
MAX_SCALE = 2.5

GBM_PARAMS: dict[str, Any] = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 10,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "lambda_l2": 0.1,
}

Mask = NDArray[np.bool_]


@dataclass(slots=True)
class Calendar:
    dow: Arr
    dom: Arr
    doy: Arr
    month: Arr
    gap: Arr  # days to the nearest festive peak, capped


def calendar(dates: list[date]) -> Calendar:
    return Calendar(
        dow=np.array([d.weekday() for d in dates], float),
        dom=np.array([d.day for d in dates], float),
        doy=np.array([d.timetuple().tm_yday for d in dates], float),
        month=np.array([d.month for d in dates], float),
        gap=np.array(
            [min(60, min(abs((d - p).days) for p in FESTIVE_PEAKS)) for d in dates], float
        ),
    )


def _features(
    y: Arr, disc: Arr, cal: Calendar, origin: int, h: int, *, yearly: bool
) -> tuple[Arr, NDArray[np.int64], NDArray[np.int64]]:
    """Feature rows for forecasting days origin..origin+h-1 of every series (k-major blocks)."""
    s = y.shape[0]
    hist = y[:, :origin]
    base = [hist[:, -i] for i in LAGS]
    base += [hist[:, -w:].mean(axis=1) for w in (7, 14, 28)]
    base.append(hist[:, -56:].mean(axis=1) if origin >= 56 else np.full(s, np.nan))
    base.append(hist[:, -28:].std(axis=1))
    base.append(np.arange(s, dtype=float))
    base_m = np.column_stack(base)
    blocks, ks, js = [], [], []
    total = y.shape[1]
    for k in range(1, h + 1):
        j = origin + k - 1
        m = math.ceil(k / 7)
        sw1 = y[:, j - 7 * m] if j - 7 * m >= 0 else np.full(s, np.nan)
        sw2 = y[:, j - 7 * (m + 1)] if j - 7 * (m + 1) >= 0 else np.full(s, np.nan)
        d = disc[:, j] if j < total else np.zeros(s)  # future promotions are unknown: assume none
        cols = [
            np.full(s, float(k)),
            np.full(s, cal.dow[j]),
            np.full(s, cal.dom[j]),
            np.full(s, cal.month[j]),
            d,
            sw1,
            sw2,
        ]
        if yearly:
            cols += [np.full(s, cal.doy[j]), np.full(s, cal.gap[j])]
        blocks.append(np.column_stack([base_m, *cols]))
        ks.append(np.full(s, k))
        js.append(np.full(s, j))
    return np.vstack(blocks), np.concatenate(ks), np.concatenate(js)


def _train(
    yc: Arr, disc: Arr, stock: Mask, cal: Calendar, origin: int, h: int, *, yearly: bool
) -> lgb.Booster | None:
    """Fit on windows whose targets all lie before ``origin``."""
    origins = list(range(28, origin - h + 1))
    if len(origins) < 7:
        return None
    step = max(1, math.ceil(len(origins) * yc.shape[0] * h / MAX_TRAIN_ROWS))
    xs, ys = [], []
    for o in origins[::step]:
        x, _k, j = _features(yc, disc, cal, o, h, yearly=yearly)
        s_idx = np.tile(np.arange(yc.shape[0]), h)
        target = yc[s_idx, j]
        ok = ~stock[s_idx, j]
        xs.append(x[ok])
        ys.append(target[ok])
    x_all, y_all = np.vstack(xs), np.concatenate(ys)
    if len(y_all) < 200:
        return None
    sku_col = 12  # position of the series id in the feature matrix
    params = {
        "objective": "regression",
        "learning_rate": GBM_PARAMS["learning_rate"],
        "num_leaves": GBM_PARAMS["num_leaves"],
        "min_data_in_leaf": GBM_PARAMS["min_child_samples"],
        "feature_fraction": GBM_PARAMS["feature_fraction"],
        "bagging_fraction": GBM_PARAMS["bagging_fraction"],
        "bagging_freq": GBM_PARAMS["bagging_freq"],
        "lambda_l2": GBM_PARAMS["lambda_l2"],
        "seed": 0,
        "verbosity": -1,
        "num_threads": 4,
    }
    data = lgb.Dataset(x_all, y_all, categorical_feature=[sku_col], free_raw_data=False)
    model = lgb.train(params, data, num_boost_round=GBM_PARAMS["n_estimators"])
    return model


def _predict_gbm(
    model: lgb.Booster,
    yc: Arr,
    disc: Arr,
    cal: Calendar,
    origin: int,
    h: int,
    *,
    yearly: bool,
) -> Arr:
    x, _k, _j = _features(yc, disc, cal, origin, h, yearly=yearly)
    pred = np.asarray(model.predict(x), dtype=float).reshape(h, yc.shape[0]).T
    return np.asarray(np.clip(pred, 0, None), dtype=float)


def seasonal_average(yc: Arr, cal: Calendar, origin: int, h: int) -> Arr:
    """Recent level times a shrunk weekday shape: robust for slow and short series."""
    hist = yc[:, :origin]
    level = hist[:, -28:].mean(axis=1)
    out = np.zeros((yc.shape[0], h))
    recent = hist[:, -56:]
    dows = cal.dow[max(0, origin - recent.shape[1]) : origin]
    factor = np.ones((yc.shape[0], 7))
    overall = np.maximum(recent.mean(axis=1), 1e-9)
    for d in range(7):
        sel = dows == d
        if sel.sum() >= 3:
            raw = recent[:, sel].mean(axis=1) / overall
            factor[:, d] = 0.5 * raw + 0.5  # shrink toward 1: few weeks of data are noisy
    for k in range(h):
        out[:, k] = level * factor[:, int(cal.dow[origin + k])]
    return out


def seasonal_naive(yc: Arr, origin: int, h: int) -> Arr:
    cycle = yc[:, origin - 7 : origin]
    return np.column_stack([cycle[:, k % 7] for k in range(h)])


def wape(actual: Arr, pred: Arr, mask: Mask) -> float | None:
    a, p = actual[mask], pred[mask]
    tot = float(np.abs(a).sum())
    return None if tot == 0 else float(np.abs(p - a).sum() / tot)


def bias(actual: Arr, pred: Arr, mask: Mask) -> float | None:
    a, p = actual[mask], pred[mask]
    tot = float(a.sum())
    return None if tot == 0 else float((p.sum() - tot) / tot)


@dataclass(slots=True)
class SeriesResult:
    sku: str
    name: str
    category: str | None
    model: str
    pattern: str
    confidence: str
    backtest_wape: float | None
    backtest_bias: float | None
    units_last: float
    units_next: float
    units_next_low: float
    units_next_high: float
    net_per_unit: float
    data: dict[str, Any]


@dataclass(slots=True)
class RunResult:
    as_of: date
    horizon: int
    history_days: int
    n_series: int
    seconds: float
    series: list[SeriesResult]
    summary: dict[str, Any] = field(default_factory=dict)


def _quantiles(res: Arr) -> tuple[float, float]:
    return float(np.quantile(res, 0.1)), float(np.quantile(res, 0.9))


def _interval(pred: Arr, res: Arr | None) -> tuple[Arr, Arr]:
    """p10/p90 around ``pred``: conformal when enough errors exist, else a Poisson-style band."""
    if res is not None and len(res) >= 20:
        lo_q, hi_q = _quantiles(res)
        lo_q, hi_q = min(lo_q, 0.0), max(hi_q, 0.0)
        return np.clip(pred + lo_q, 0, None), pred + hi_q
    width = 1.28 * 1.2 * np.sqrt(np.maximum(pred, 0.5))
    return np.clip(pred - width, 0, None), pred + width


def run(panel: Panel, h: int = H) -> RunResult | None:
    t0 = time.perf_counter()
    t_days = panel.n_days
    if t_days < MIN_DAYS_FORECAST:
        return None
    s = len(panel.skus)
    yc = np.vstack([clean(panel.y[i], panel.stockout[i]) for i in range(s)])
    dates_ext = panel.dates + [panel.dates[-1] + timedelta(days=i + 1) for i in range(h)]
    cal = calendar(dates_ext)
    yearly = t_days >= 365
    can_gbm = t_days >= MIN_DAYS_GBM

    # ---- backtests
    windows = [t_days - h * w for w in range(MAX_WINDOWS, 0, -1)]
    windows = [o for o in windows if o >= FIRST_BACKTEST_ORIGIN]
    bt: list[dict[str, Any]] = []
    for o in windows:
        entry: dict[str, Any] = {
            "origin": o,
            "actual": panel.y[:, o : o + h],
            "mask": ~panel.stockout[:, o : o + h],
            "avg": seasonal_average(yc, cal, o, h),
            "naive": seasonal_naive(yc, o, h),
        }
        if can_gbm:
            model = _train(yc, panel.disc, panel.stockout, cal, o, h, yearly=yearly)
            if model is not None:
                entry["gbm"] = _predict_gbm(model, yc, panel.disc, cal, o, h, yearly=yearly)
        bt.append(entry)

    # ---- final model on all data
    final_gbm: Arr | None = None
    if can_gbm:
        model = _train(yc, panel.disc, panel.stockout, cal, t_days, h, yearly=yearly)
        if model is not None:
            final_gbm = _predict_gbm(model, yc, panel.disc, cal, t_days, h, yearly=yearly)
    final_avg = seasonal_average(yc, cal, t_days, h)
    gbm_ok = final_gbm is not None and all("gbm" in e for e in bt) and bool(bt)

    # ---- per-series model choice, intervals
    series: list[SeriesResult] = []
    chosen_bt = np.zeros((s, len(bt), h))
    chosen_fc = np.zeros((s, h))
    chosen_res: list[Arr | None] = []
    stats_model = {"lightgbm": 0, "seasonal_average": 0}
    w_model: dict[str, list[float]] = {"gbm": [], "avg": [], "naive": []}
    for i in range(s):
        pattern = str(classify(list(yc[i, -120:]))["pattern"])
        scores: dict[str, float | None] = {}
        for name in ("gbm", "avg", "naive"):
            if name == "gbm" and not gbm_ok:
                continue
            if not bt:
                continue
            a = np.concatenate([e["actual"][i] for e in bt])
            p = np.concatenate([e[name][i] for e in bt])
            m = np.concatenate([e["mask"][i] for e in bt])
            scores[name] = wape(a, p, m)
        use = "avg"
        gw, aw = scores.get("gbm"), scores.get("avg")
        if gbm_ok and gw is not None:
            steady = pattern in ("smooth", "erratic", "insufficient")
            if (steady and (aw is None or gw <= aw)) or (aw is not None and gw < aw * 0.9):
                use = "gbm"
        fc = final_gbm[i] if use == "gbm" and final_gbm is not None else final_avg[i]
        for k, e in enumerate(bt):
            chosen_bt[i, k] = e[use][i]
        chosen_fc[i] = fc
        stats_model["lightgbm" if use == "gbm" else "seasonal_average"] += 1
        res = (
            np.concatenate([(e["actual"][i] - e[use][i])[e["mask"][i]] for e in bt]) if bt else None
        )
        chosen_res.append(res)
        for name in w_model:
            if scores.get(name) is not None:
                w_model[name].append(float(scores[name] or 0.0))
        series.append(
            SeriesResult(
                sku=panel.skus[i],
                name=panel.names[i],
                category=panel.categories[i],
                model="lightgbm" if use == "gbm" else "seasonal_average",
                pattern=pattern,
                confidence="low",
                backtest_wape=scores.get(use),
                backtest_bias=None,
                units_last=float(panel.y[i, -h:].sum()),
                units_next=0.0,
                units_next_low=0.0,
                units_next_high=0.0,
                net_per_unit=float(panel.net_per_unit[i]),
                data={},
            )
        )

    # ---- accuracy (pooled over all series, stock-out days excluded)
    accuracy: dict[str, Any] = {"windows": len(bt)}
    interval_scale = 1.0
    if bt:
        act = np.concatenate([e["actual"] for e in bt], axis=1)
        msk = np.concatenate([e["mask"] for e in bt], axis=1)
        pred = chosen_bt.reshape(s, -1)
        naive = np.concatenate([e["naive"] for e in bt], axis=1)
        w_all, w_naive = wape(act, pred, msk), wape(act, naive, msk)
        accuracy.update(
            wape=w_all,
            bias=bias(act, pred, msk),
            wape_seasonal_naive=w_naive,
            fva=None if not w_naive or w_all is None else 1 - w_all / w_naive,
            gate_passed=bool(w_all is not None and w_naive is not None and w_all < w_naive),
        )
        beat = [
            sr.backtest_wape is not None
            and (nw := wape(act[i], naive[i], msk[i])) is not None
            and sr.backtest_wape < nw
            for i, sr in enumerate(series)
        ]
        accuracy["series_beating_naive"] = float(np.mean(beat)) if beat else None
        # Leave-one-window-out intervals, then one global widening factor so the 80 % range really
        # covers about 80 % of outcomes (raw conformal ranges from few windows run narrow).
        cases: list[tuple[Arr, Arr, Arr, Arr, Mask]] = []
        for k, e in enumerate(bt):
            for i in range(s):
                others = [
                    (bt[j]["actual"][i] - chosen_bt[i, j])[bt[j]["mask"][i]]
                    for j in range(len(bt))
                    if j != k
                ]
                res = np.concatenate(others) if others else None
                lo, hi = _interval(chosen_bt[i, k], res)
                cases.append((chosen_bt[i, k], lo, hi, e["actual"][i], e["mask"][i]))

        def covered(scale: float) -> float:
            inside = total = 0
            for p_, lo_, hi_, a_, m_ in cases:
                lo_s, hi_s = p_ - scale * (p_ - lo_), p_ + scale * (hi_ - p_)
                inside += int(((a_[m_] >= lo_s[m_]) & (a_[m_] <= hi_s[m_])).sum())
                total += int(m_.sum())
            return inside / total if total else 0.0

        raw = covered(1.0)
        interval_scale = 1.0
        while covered(interval_scale) < TARGET_COVERAGE and interval_scale < MAX_SCALE:
            interval_scale = round(interval_scale + 0.05, 2)
        accuracy["interval_coverage_80_raw"] = raw
        accuracy["interval_coverage_80"] = covered(interval_scale)
        accuracy["interval_scale"] = interval_scale
        for i, sr in enumerate(series):
            sr.backtest_bias = bias(act[i], pred[i], msk[i])

    # ---- final forecasts with intervals, confidence and stored series data
    last_date = panel.dates[-1]
    fdays = [last_date + timedelta(days=k + 1) for k in range(h)]
    p50_all = np.zeros((s, h))
    p10_all = np.zeros((s, h))
    p90_all = np.zeros((s, h))
    for i, sr in enumerate(series):
        lo, hi = _interval(chosen_fc[i], chosen_res[i])
        lo = np.clip(chosen_fc[i] - interval_scale * (chosen_fc[i] - lo), 0, None)
        hi = chosen_fc[i] + interval_scale * (hi - chosen_fc[i])
        p50_all[i], p10_all[i], p90_all[i] = chosen_fc[i], lo, hi
        sr.units_next = float(chosen_fc[i].sum())
        sr.units_next_low = float(lo.sum())
        sr.units_next_high = float(hi.sum())
        w = sr.backtest_wape
        if t_days >= 56 and w is not None and w <= 0.30 and sr.pattern in ("smooth", "erratic"):
            sr.confidence = "high"
        elif t_days >= 28 and w is not None and w <= 0.55:
            sr.confidence = "medium"
        n_hist = 90
        sr.data = {
            "hist_start": panel.dates[max(0, t_days - n_hist)].isoformat(),
            "hist": [round(float(v), 2) for v in panel.y[i, -n_hist:]],
            "fc_start": fdays[0].isoformat(),
            "p10": [round(float(v), 2) for v in lo],
            "p50": [round(float(v), 2) for v in chosen_fc[i]],
            "p90": [round(float(v), 2) for v in hi],
            "backtest": [
                {
                    "d": panel.dates[e["origin"] + k2].isoformat(),
                    "a": round(float(e["actual"][i][k2]), 2),
                    "p": round(float(chosen_bt[i, kk, k2]), 2),
                }
                for kk, e in enumerate(bt)
                for k2 in range(h)
            ],
        }

    # ---- totals: history, backtest and forecast with a relative-error interval
    tot_fc = p50_all.sum(axis=0)
    rel: Arr | None = None
    tot_bt: list[dict[str, Any]] = []
    if bt:
        a_tot = np.concatenate([e["actual"].sum(axis=0) for e in bt])
        p_tot = chosen_bt.sum(axis=0).reshape(-1)
        ok = p_tot > 0
        rel = (a_tot[ok] - p_tot[ok]) / p_tot[ok]
        tot_bt = [
            {
                "d": panel.dates[e["origin"] + k2].isoformat(),
                "a": round(float(a_tot[kk * h + k2]), 1),
                "p": round(float(p_tot[kk * h + k2]), 1),
            }
            for kk, e in enumerate(bt)
            for k2 in range(h)
        ]
    lo_r, hi_r = _quantiles(rel) if rel is not None and len(rel) >= 10 else (-0.15, 0.15)
    npu = np.array([sr.net_per_unit for sr in series])
    net_fc = (p50_all * npu[:, None]).sum(axis=0)
    hist_tot = panel.y.sum(axis=0)
    n_hist = min(t_days, 120)
    totals = {
        "history": [
            {
                "d": panel.dates[t_days - n_hist + k].isoformat(),
                "units": round(float(hist_tot[t_days - n_hist + k]), 1),
            }
            for k in range(n_hist)
        ],
        "forecast": [
            {
                "d": fdays[k].isoformat(),
                "p10": round(float(max(0.0, tot_fc[k] * (1 + min(lo_r, 0) * interval_scale))), 1),
                "p50": round(float(tot_fc[k]), 1),
                "p90": round(float(tot_fc[k] * (1 + max(hi_r, 0) * interval_scale)), 1),
                "net": round(float(net_fc[k]), 2),
            }
            for k in range(h)
        ],
        "backtest": tot_bt,
    }

    warnings: list[str] = []
    if t_days < MIN_DAYS_GBM:
        warnings.append(
            f"Only {t_days} days of history: forecasts use a simple recent-average method. "
            f"Machine-learning forecasts start at {MIN_DAYS_GBM} days."
        )
    elif t_days < 180:
        warnings.append("Under six months of history: expect wider ranges until more data arrives.")
    near_peak = [
        d for d in fdays if min(abs((d - p).days) for p in FESTIVE_PEAKS) <= PEAK_WARN_DAYS
    ]
    if near_peak and t_days < 365:
        warnings.append(
            "A festive season falls inside this forecast. With under a year of history the model "
            "has not seen one, so demand is likely to run above the forecast."
        )
    if accuracy.get("gate_passed") is False:
        warnings.append(
            "The model did not beat repeating last week in the backtest; treat it as a guide only."
        )
    if panel.stockout.any():
        warnings.append(
            f"{int(panel.stockout.any(axis=1).sum())} products had suspected stock-outs; "
            "those days were treated as missing demand, not zero demand."
        )

    summary = {
        "model_card": {
            "models": stats_model,
            "features": [
                "last 1-28 days of sales",
                "recent averages and variability",
                "same weekday last weeks",
                "weekday, day of month, month",
                "planned discount (assumed none in the future)",
                *(["day of year and distance to the festive season"] if yearly else []),
            ],
            "backtest_windows": len(bt),
            "horizon_days": h,
            "assumptions": [
                "No new promotions or price changes during the forecast period",
                "Suspected stock-out days are not counted as zero demand",
            ],
            "limits": [
                "Intervals come from past forecast errors and can be too narrow in unusual periods",
                "Forecasts are demand estimates, not stock-aware",
            ],
        },
        "accuracy": accuracy,
        "totals": totals,
        "warnings": warnings,
    }
    return RunResult(
        as_of=last_date,
        horizon=h,
        history_days=t_days,
        n_series=s,
        seconds=round(time.perf_counter() - t0, 2),
        series=series,
        summary=summary,
    )
