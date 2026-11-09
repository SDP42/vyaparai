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

from app.services import events
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
TARGET_COVERAGE = 0.80
ENGINE_VERSION = "1.2"
TUNE_MAX_SECONDS = 60.0
TUNE_MIN_GAIN = 0.01  # tuned parameters must cut the inner-validation error by 1 % to be used
MAX_PEAK_UPLIFT = 50
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
        gap=events.gap_to_peak(dates),
    )


def _features(
    y: Arr,
    disc: Arr,
    cal: Calendar,
    origin: int,
    h: int,
    *,
    yearly: bool,
    exog: Arr | None = None,
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
        if exog is not None:  # daily covariates known for the forecast period, e.g. temperature
            cols += [np.full(s, exog[e, j]) for e in range(exog.shape[0])]
        blocks.append(np.column_stack([base_m, *cols]))
        ks.append(np.full(s, k))
        js.append(np.full(s, j))
    return np.vstack(blocks), np.concatenate(ks), np.concatenate(js)


def _train(
    yc: Arr,
    disc: Arr,
    stock: Mask,
    cal: Calendar,
    origin: int,
    h: int,
    *,
    yearly: bool,
    exog: Arr | None = None,
    gbm: dict[str, Any] | None = None,
) -> lgb.Booster | None:
    """Fit on windows whose targets all lie before ``origin``."""
    origins = list(range(28, origin - h + 1))
    if len(origins) < 7:
        return None
    step = max(1, math.ceil(len(origins) * yc.shape[0] * h / MAX_TRAIN_ROWS))
    xs, ys = [], []
    for o in origins[::step]:
        x, _k, j = _features(yc, disc, cal, o, h, yearly=yearly, exog=exog)
        s_idx = np.tile(np.arange(yc.shape[0]), h)
        target = yc[s_idx, j]
        ok = ~stock[s_idx, j]
        xs.append(x[ok])
        ys.append(target[ok])
    x_all, y_all = np.vstack(xs), np.concatenate(ys)
    if len(y_all) < 200:
        return None
    sku_col = 12  # position of the series id in the feature matrix
    g = {**GBM_PARAMS, **(gbm or {})}
    params = {
        "objective": "regression",
        "learning_rate": g["learning_rate"],
        "num_leaves": int(g["num_leaves"]),
        "min_data_in_leaf": int(g["min_child_samples"]),
        "feature_fraction": g["feature_fraction"],
        "bagging_fraction": g["bagging_fraction"],
        "bagging_freq": g["bagging_freq"],
        "lambda_l2": g["lambda_l2"],
        "seed": 0,
        "verbosity": -1,
        "num_threads": 4,
    }
    data = lgb.Dataset(x_all, y_all, categorical_feature=[sku_col], free_raw_data=False)
    model = lgb.train(params, data, num_boost_round=int(g["n_estimators"]))
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
    exog: Arr | None = None,
) -> Arr:
    x, _k, _j = _features(yc, disc, cal, origin, h, yearly=yearly, exog=exog)
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


def theta(yc: Arr, cal: Calendar, origin: int, h: int) -> Arr:
    """Theta-style forecast: weekday-adjusted level plus half the trend.

    Remove the weekday pattern, smooth the level with the alpha that fits the last 8 weeks best, add
    half of the fitted straight-line slope (the theta = 2 drift), then put the weekday pattern back.
    A compact, dependency-free stand-in for the ETS/Theta family that scored well in the benchmark.
    """
    hist = yc[:, max(0, origin - 112) : origin]
    n = hist.shape[1]
    dows = cal.dow[origin - n : origin].astype(int)
    overall = np.maximum(hist.mean(axis=1), 1e-9)
    idx = np.ones((hist.shape[0], 7))
    for d in range(7):
        sel = dows == d
        if sel.sum() >= 3:
            w = 0.85 if sel.sum() >= 8 else 0.5  # trust the weekday pattern once 8 weeks agree
            idx[:, d] = w * (hist[:, sel].mean(axis=1) / overall) + (1 - w)
    idx = np.maximum(idx, 0.2)
    des = hist / idx[:, dows]
    alphas = np.array([0.1, 0.2, 0.3, 0.5, 0.7, 0.9])
    level = np.tile(des[:, :1], (1, len(alphas)))  # (series, alphas)
    sse = np.zeros_like(level)
    for t in range(1, n):
        err = des[:, t : t + 1] - level
        sse += err**2
        level = level + alphas * err
    best = np.argmin(sse, axis=1)
    lvl = level[np.arange(level.shape[0]), best]
    x = np.arange(n, dtype=float)
    slope = ((x - x.mean()) * (des - des.mean(axis=1, keepdims=True))).sum(axis=1) / max(
        float(((x - x.mean()) ** 2).sum()), 1e-9
    )
    out = np.zeros((hist.shape[0], h))
    for k in range(h):
        out[:, k] = np.maximum(0.0, lvl + 0.5 * slope * (k + 1)) * idx[:, int(cal.dow[origin + k])]
    return out


def _sample_params(rng: np.random.Generator) -> dict[str, Any]:
    return {
        "n_estimators": int(rng.integers(2, 13)) * 50,
        "learning_rate": float(np.exp(rng.uniform(np.log(0.01), np.log(0.15)))),
        "num_leaves": int(rng.integers(8, 97)),
        "min_child_samples": int(rng.integers(5, 81)),
        "feature_fraction": float(rng.uniform(0.5, 1.0)),
        "bagging_fraction": float(rng.uniform(0.5, 1.0)),
        "lambda_l2": float(np.exp(rng.uniform(np.log(1e-3), np.log(10.0)))),
    }


def tune_gbm(
    yc: Arr, disc: Arr, stock: Mask, panel_y: Arr, cal: Calendar, first_window: int, h: int,
    *, yearly: bool, exog: Arr | None, trials: int, seed: int = 7,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:  # fmt: skip
    """Random search over LightGBM settings, scored only on data before the first backtest window.

    The search only sees data before the first backtest window, so it cannot leak. The defaults are
    trial 0, and the tuned set is used only if it improves the inner error by ``TUNE_MIN_GAIN``.
    """
    inner = [first_window - 2 * h, first_window - h]
    info: dict[str, Any] = {"trials": 0, "used": False, "default_wape": None, "best_wape": None}
    if inner[0] < FIRST_BACKTEST_ORIGIN or trials < 1:
        info["note"] = "Not enough history to tune safely."
        return None, info
    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()

    def score(params: dict[str, Any] | None) -> float | None:
        a_all, p_all = [], []
        for o in inner:
            model = _train(yc, disc, stock, cal, o, h, yearly=yearly, exog=exog, gbm=params)
            if model is None:
                return None
            p_all.append(_predict_gbm(model, yc, disc, cal, o, h, yearly=yearly, exog=exog))
            a_all.append(panel_y[:, o : o + h])
        a, p = np.concatenate(a_all, axis=1), np.concatenate(p_all, axis=1)
        return wape(a, p, np.ones_like(a, dtype=bool))

    base = score(None)
    info["default_wape"] = base
    if base is None:
        return None, info
    best_p, best_w = None, base
    for _ in range(trials):
        if time.perf_counter() - t0 > TUNE_MAX_SECONDS:
            info["note"] = "Stopped early at the time limit."
            break
        cand = _sample_params(rng)
        w = score(cand)
        info["trials"] += 1
        if w is not None and w < best_w:
            best_p, best_w = cand, w
    info["best_wape"] = best_w
    if best_p is not None and (base - best_w) / base >= TUNE_MIN_GAIN:
        info["used"] = True
        info["params"] = {
            k: (round(v, 4) if isinstance(v, float) else v) for k, v in best_p.items()
        }
        return best_p, info
    return None, info


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


def _run(
    panel: Panel,
    h: int,
    exog_m: Arr | None,
    exog_names: list[str],
    tune_trials: int = 0,
    peak_uplift_pct: int = 0,
    zones: frozenset[str] = frozenset(),
    state: str | None = None,
) -> RunResult | None:
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
    gbm_params: dict[str, Any] | None = None
    tuning: dict[str, Any] | None = None
    if tune_trials > 0 and can_gbm and windows:
        gbm_params, tuning = tune_gbm(
            yc, panel.disc, panel.stockout, panel.y, cal, windows[0], h,
            yearly=yearly, exog=exog_m, trials=tune_trials,
        )  # fmt: skip
    bt: list[dict[str, Any]] = []
    for o in windows:
        entry: dict[str, Any] = {
            "origin": o,
            "actual": panel.y[:, o : o + h],
            "mask": ~panel.stockout[:, o : o + h],
            "avg": seasonal_average(yc, cal, o, h),
            "theta": theta(yc, cal, o, h),
            "naive": seasonal_naive(yc, o, h),
        }
        if can_gbm:
            model = _train(
                yc,
                panel.disc,
                panel.stockout,
                cal,
                o,
                h,
                yearly=yearly,
                exog=exog_m,
                gbm=gbm_params,
            )
            if model is not None:
                entry["gbm"] = _predict_gbm(
                    model, yc, panel.disc, cal, o, h, yearly=yearly, exog=exog_m
                )
        bt.append(entry)

    # ---- final model on all data
    final_gbm: Arr | None = None
    if can_gbm:
        model = _train(
            yc,
            panel.disc,
            panel.stockout,
            cal,
            t_days,
            h,
            yearly=yearly,
            exog=exog_m,
            gbm=gbm_params,
        )
        if model is not None:
            final_gbm = _predict_gbm(
                model, yc, panel.disc, cal, t_days, h, yearly=yearly, exog=exog_m
            )
    final_avg = seasonal_average(yc, cal, t_days, h)
    final_theta = theta(yc, cal, t_days, h)
    gbm_ok = final_gbm is not None and all("gbm" in e for e in bt) and bool(bt)

    # ---- per-series model choice, intervals
    series: list[SeriesResult] = []
    chosen_bt = np.zeros((s, len(bt), h))
    chosen_fc = np.zeros((s, h))
    chosen_res: list[Arr | None] = []
    labels = {"gbm": "lightgbm", "theta": "theta", "avg": "seasonal_average"}
    stats_model = {"lightgbm": 0, "theta": 0, "seasonal_average": 0}
    w_model: dict[str, list[float]] = {"gbm": [], "theta": [], "avg": [], "naive": []}
    for i in range(s):
        pattern = str(classify(list(yc[i, -120:]))["pattern"])
        scores: dict[str, float | None] = {}
        for name in ("gbm", "theta", "avg", "naive"):
            if name == "gbm" and not gbm_ok:
                continue
            if not bt:
                continue
            a = np.concatenate([e["actual"][i] for e in bt])
            p = np.concatenate([e[name][i] for e in bt])
            m = np.concatenate([e["mask"][i] for e in bt])
            scores[name] = wape(a, p, m)
        # the best simple method first, then LightGBM only if it earns the place
        simple: dict[str, float] = {}
        for n in ("theta", "avg"):
            v = scores.get(n)
            if v is not None:
                simple[n] = v
        use = min(simple, key=lambda n: simple[n]) if simple else "avg"
        best_simple = simple.get(use)
        gw = scores.get("gbm")
        if gbm_ok and gw is not None:
            steady = pattern in ("smooth", "erratic", "insufficient")
            if best_simple is None or gw <= best_simple * (1.0 if steady else 0.9):
                use = "gbm"
        finals = {"gbm": final_gbm, "theta": final_theta, "avg": final_avg}
        fc_src = finals[use]
        fc = fc_src[i] if fc_src is not None else final_avg[i]
        for k, e in enumerate(bt):
            chosen_bt[i, k] = e[use][i]
        chosen_fc[i] = fc
        stats_model[labels[use]] += 1
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
                model=labels[use],
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
        cand: dict[str, float | None] = {"seasonal_naive": w_naive}
        for name, label in labels.items():
            if all(name in e for e in bt):
                cand[label] = wape(act, np.concatenate([e[name] for e in bt], axis=1), msk)
        cand["chosen_mix"] = w_all
        accuracy["candidates"] = cand
        accuracy["engine_version"] = ENGINE_VERSION
        if tuning is not None:
            accuracy["tuning"] = tuning
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
    peak_u = max(0, min(MAX_PEAK_UPLIFT, int(peak_uplift_pct)))
    peak_days = events.festival_peak_days(fdays, zones, state)
    mult = np.where(peak_days, 1 + peak_u / 100, 1.0)  # the owner's festive-season adjustment
    for i, sr in enumerate(series):
        lo, hi = _interval(chosen_fc[i], chosen_res[i])
        lo = np.clip(chosen_fc[i] - interval_scale * (chosen_fc[i] - lo), 0, None)
        hi = chosen_fc[i] + interval_scale * (hi - chosen_fc[i])
        fc_i, lo, hi = chosen_fc[i] * mult, lo * mult, hi * mult
        p50_all[i], p10_all[i], p90_all[i] = fc_i, lo, hi
        sr.units_next = float(fc_i.sum())
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
            "p50": [round(float(v), 2) for v in fc_i],
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
    peak_list = events.peak_names(fdays, zones, state)
    near_peak = bool(peak_list)
    names = ", ".join(peak_list[:3])
    if near_peak and t_days < 365:
        warnings.append(
            f"The festive season ({names}) falls inside this forecast. With under a year "
            "of history "
            "the model has not seen one, so demand is likely to run above it."
        )
    elif near_peak:
        warnings.append(
            f"The festive season ({names}) falls inside this forecast. The model has seen a past "
            "peak, but it may still under-forecast one, so check the range."
        )
    if near_peak and peak_u > 0:
        warnings.append(
            f"You added {peak_u}% to the days near the festive season. That is your adjustment, "
            "not something the model learned."
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
                *(
                    [f"Festive-season days are {peak_u}% higher than the model says (set by you)"]
                    if peak_u > 0 and near_peak
                    else []
                ),
            ],
            "limits": [
                "Intervals come from past forecast errors and can be too narrow in unusual periods",
                "Forecasts are demand estimates, not stock-aware",
            ],
        },
        "options": {"tune_trials": tune_trials, "peak_uplift_pct": peak_u},
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


MIN_EXOG_GAIN = 0.02  # a covariate must cut the pooled backtest error by 2 % (relative) to be kept


def _matrix(signals: dict[str, Arr], need: int) -> Arr:
    if any(len(v) != need for v in signals.values()):
        raise ValueError("each covariate needs one value per history day plus one per forecast day")
    return np.vstack([np.asarray(signals[n], dtype=float) for n in sorted(signals)])


def run(
    panel: Panel,
    h: int = H,
    exog: dict[str, Arr] | None = None,
    *,
    exog_groups: dict[str, dict[str, Arr]] | None = None,
    tune_trials: int = 0,
    peak_uplift_pct: int = 0,
    zones: frozenset[str] = frozenset(),
    state: str | None = None,
) -> RunResult | None:
    """Forecast every product.

    Outside signals are daily series covering the history *and* the forecast period (length
    ``panel.n_days + h``), in named groups (for example events, then weather). Each group is tried
    on top of what was already accepted and kept only if the pooled backtest error falls by at
    least ``MIN_EXOG_GAIN``; every decision goes in the model card. ``exog`` is one group called
    "signals".
    """
    groups = dict(exog_groups or {})
    if exog:
        groups["signals"] = exog
    chosen = _run(panel, h, None, [], tune_trials, peak_uplift_pct, zones, state)
    if chosen is None or not groups:
        return chosen
    need = panel.n_days + h
    selected: dict[str, Arr] = {}
    base_w = chosen.summary["accuracy"].get("wape")
    cur_w = base_w
    report: list[dict[str, Any]] = []
    for gname, arrays in groups.items():
        trial = {**selected, **arrays}
        res = _run(
            panel,
            h,
            _matrix(trial, need),
            sorted(trial),
            tune_trials,
            peak_uplift_pct,
            zones,
            state,
        )
        w = res.summary["accuracy"].get("wape") if res else None
        ok = bool(res and cur_w and w is not None and (cur_w - w) / cur_w >= MIN_EXOG_GAIN)
        report.append(
            {
                "group": gname,
                "names": sorted(arrays),
                "used": ok,
                "wape_before": cur_w,
                "wape_after": w,
            }
        )
        if ok and res is not None:
            selected, chosen, cur_w = trial, res, w
    chosen.summary["accuracy"]["covariates"] = {
        "names": sorted(selected),
        "used": bool(selected),
        "wape_without": base_w,
        "wape_with": cur_w if selected else report[-1]["wape_after"],
        "required_gain": MIN_EXOG_GAIN,
        "groups": report,
    }
    if selected:
        chosen.summary["model_card"]["features"].append(
            "outside signals: " + ", ".join(sorted(selected))
        )
    dropped = [g["group"] for g in report if not g["used"]]
    if dropped:
        chosen.summary["warnings"].append(
            "Outside signals ("
            + ", ".join(dropped)
            + ") did not improve the backtest, so they were left out."
        )
    return chosen
