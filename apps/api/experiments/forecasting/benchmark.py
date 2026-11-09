"""Benchmark: baselines, statistical, intermittent and LightGBM (default vs tuned).

Selection uses the backtest windows; the holdout windows are scored once at the end.
Run:  uv run --group ml python -m experiments.forecasting.benchmark
"""

import json
import pickle
import time

import numpy as np
import optuna
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import (
    ADIDA, IMAPA, MSTL, AutoARIMA, AutoETS, AutoTheta, CrostonClassic, CrostonSBA, HistoricAverage,
    Naive, SeasonalNaive, SeasonalWindowAverage, TSB,
)  # fmt: skip

from . import gbm
from .common import FOLDS, H, HOLDOUT, OUT, load, clean, per_series_wape, score, window_origins

optuna.logging.set_verbosity(optuna.logging.WARNING)


def stats_models() -> list:
    return [
        Naive(alias="naive"),
        SeasonalNaive(season_length=7, alias="seasonal_naive"),
        SeasonalWindowAverage(season_length=7, window_size=4, alias="seasonal_avg4"),
        HistoricAverage(alias="hist_avg"),
        AutoETS(season_length=7, alias="auto_ets"),
        AutoARIMA(season_length=7, alias="auto_arima"),
        AutoTheta(season_length=7, alias="auto_theta"),
        MSTL(season_length=[7], trend_forecaster=AutoETS(model="ZZN"), alias="mstl_ets"),
        CrostonClassic(alias="croston"),
        CrostonSBA(alias="croston_sba"),
        TSB(alpha_d=0.2, alpha_p=0.2, alias="tsb"),
        ADIDA(alias="adida"),
        IMAPA(alias="imapa"),
    ]


def run_stats(panel) -> dict[str, dict[str, pd.DataFrame]]:
    """Returns {model: {"backtest": preds, "holdout": preds}} with columns sku, t, yhat."""
    cleaned = {s: clean(panel.y[s], panel.so[s]) for s in panel.skus}
    long = pd.concat(
        [pd.DataFrame({"unique_id": s, "ds": panel.dates, "y": cleaned[s]}) for s in panel.skus]
    )
    cut = panel.T - HOLDOUT
    out: dict[str, dict[str, pd.DataFrame]] = {}
    for part, frame, windows in [
        ("backtest", long[long["ds"] < panel.dates[cut]], FOLDS),
        ("holdout", long, 2),
    ]:
        sf = StatsForecast(models=stats_models(), freq="D", n_jobs=-1)
        cv = sf.cross_validation(df=frame, h=H, step_size=H, n_windows=windows)
        idx = {d: i for i, d in enumerate(panel.dates)}
        cv["t"] = cv["ds"].map(idx)
        for m in [c for c in cv.columns if c not in ("unique_id", "ds", "cutoff", "y", "t")]:
            out.setdefault(m, {})[part] = cv.rename(columns={"unique_id": "sku", m: "yhat"})[
                ["sku", "t", "yhat"]
            ]
    return out


def gbm_windows(panel, params, label, seed=0, objective="regression") -> dict[str, pd.DataFrame]:
    origins = window_origins(panel.T)
    res = {}
    for part in ("backtest", "holdout"):
        res[part] = pd.concat(
            [
                gbm.train_predict(panel, o, params, seed=seed, objective=objective)
                for o in origins[part]
            ]
        )
    return res


def tune(panel, trials: int) -> tuple[dict, list[dict]]:
    """Optuna on data strictly before the first backtest window; two inner validation windows."""
    first = window_origins(panel.T)["backtest"][0]
    inner = [first - 2 * H, first - H]
    log: list[dict] = []

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 8, 96),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 80),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 1e-3, 10.0, log=True),
        }
        preds = pd.concat([gbm.train_predict(panel, o, params, seed=0) for o in inner])
        w = score(preds, panel)["wape_all"]
        log.append({"trial": trial.number, "wape": w, **params})
        return float(w)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=7))
    study.optimize(objective, n_trials=trials)
    return study.best_params, log


def main(trials: int = 24) -> None:
    t0 = time.time()
    panel = load()
    results: dict[str, dict[str, pd.DataFrame]] = run_stats(panel)
    print(f"stats done {time.time() - t0:.0f}s", flush=True)

    results["lgbm_default"] = gbm_windows(panel, gbm.DEFAULT, "default")
    print(f"lgbm default done {time.time() - t0:.0f}s", flush=True)
    best, log = tune(panel, trials)
    print(f"tuned params {best} {time.time() - t0:.0f}s", flush=True)
    results["lgbm_tuned"] = gbm_windows(panel, {**gbm.DEFAULT, **best}, "tuned")
    print(f"lgbm tuned done {time.time() - t0:.0f}s", flush=True)

    with (OUT / "results.pkl").open("wb") as f:
        pickle.dump({"results": results, "best": best, "tuning_log": log}, f)
    summarise(panel, results, best, log)


def mean_of(results, names, part):
    frames = [results[n][part].set_index(["sku", "t"])["yhat"] for n in names]
    m = pd.concat(frames, axis=1).mean(axis=1).rename("yhat").reset_index()
    return m


def summarise(panel, results, best, log) -> None:
    rows = []
    for name, parts in results.items():
        bt, ho = score(parts["backtest"], panel), score(parts["holdout"], panel)
        rows.append(
            {
                "model": name,
                **{f"bt_{k}": v for k, v in bt.items()},
                **{f"ho_{k}": v for k, v in ho.items()},
            }
        )
    df = pd.DataFrame(rows).sort_values("bt_wape_all")
    # simple ensembles chosen on the BACKTEST ranking only
    top3 = list(df["model"].head(3))
    ens = {"ensemble_top3_mean": {p: mean_of(results, top3, p) for p in ("backtest", "holdout")}}
    results.update(ens)
    bt, ho = (
        score(ens["ensemble_top3_mean"]["backtest"], panel),
        score(ens["ensemble_top3_mean"]["holdout"], panel),
    )
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "model": "ensemble_top3_mean",
                        **{f"bt_{k}": v for k, v in bt.items()},
                        **{f"ho_{k}": v for k, v in ho.items()},
                    }
                ]
            ),
        ]
    )
    df.to_csv(OUT / "summary.csv", index=False)
    ref = per_series_wape(results["seasonal_naive"]["holdout"], panel)
    wins = {}
    for name, parts in results.items():
        w = per_series_wape(parts["holdout"], panel)
        wins[name] = float(np.mean([w[s] < ref[s] for s in w if s in ref]))
    json.dump(
        {"best_params": best, "top3_by_backtest": top3, "holdout_win_rate_vs_seasonal_naive": wins},
        (OUT / "extra.json").open("w"),
        indent=2,
    )
    pd.set_option("display.width", 250, "display.max_columns", 30)
    cols = [
        "model",
        "bt_wape_all",
        "ho_wape_all",
        "ho_bias_all",
        "ho_wape_fast",
        "ho_wape_mid",
        "ho_wape_slow",
    ]
    print(df[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
