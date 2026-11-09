"""Combine benchmark + pretrained results; test ensembles, per-type routing and tuning value."""

import json
import pickle

import numpy as np
import pandas as pd

from .common import OUT, load, per_series_wape, score


def mean_of(res, names, part):
    fr = [res[n][part].set_index(["sku", "t"])["yhat"] for n in names]
    return pd.concat(fr, axis=1).mean(axis=1).rename("yhat").reset_index()


def main() -> None:
    panel = load()
    blob = pickle.load((OUT / "results.pkl").open("rb"))
    res = blob["results"]
    for n in ("tiny", "small"):
        res.update(pickle.load((OUT / f"pretrained_chronos_{n}.pkl").open("rb")))
    res["ens_lgbm_ets_chronos"] = {
        p: mean_of(res, ["lgbm_default", "auto_ets", "chronos_small"], p)
        for p in ("backtest", "holdout")
    }
    res["ens_lgbm_chronos"] = {
        p: mean_of(res, ["lgbm_default", "chronos_small"], p) for p in ("backtest", "holdout")
    }

    # routing: for each demand type pick the model with the best BACKTEST wape for that type
    kinds = sorted(set(panel.kind.values()))
    cand = [m for m in res if not m.startswith("ens_")]
    chosen = {}
    for k in kinds:
        chosen[k] = min(cand, key=lambda m: score(res[m]["backtest"], panel)[f"wape_{k}"])
    routed = {}
    for p in ("backtest", "holdout"):
        parts = [res[chosen[k]][p][res[chosen[k]][p]["sku"].map(panel.kind) == k] for k in kinds]
        routed[p] = pd.concat(parts)
    res["routed_by_type"] = routed

    ref = per_series_wape(res["seasonal_naive"]["holdout"], panel)
    rows = []
    for name, parts in res.items():
        bt, ho = score(parts["backtest"], panel), score(parts["holdout"], panel)
        w = per_series_wape(parts["holdout"], panel)
        rows.append(
            {
                "model": name,
                "bt_wape": bt["wape_all"],
                "ho_wape": ho["wape_all"],
                "ho_bias": ho["bias_all"],
                "ho_fast": ho.get("wape_fast"),
                "ho_mid": ho.get("wape_mid"),
                "ho_slow": ho.get("wape_slow"),
                "fva_vs_snaive": 1
                - ho["wape_all"] / score(res["seasonal_naive"]["holdout"], panel)["wape_all"],
                "series_win_rate": float(np.mean([w[s] < ref[s] for s in w if s in ref])),
            }
        )
    df = pd.DataFrame(rows).sort_values("bt_wape")
    df.to_csv(OUT / "final_summary.csv", index=False)

    log = pd.DataFrame(blob["tuning_log"])
    tuning = {
        "trials": len(log),
        "inner_wape_best": float(log["wape"].min()),
        "inner_wape_worst": float(log["wape"].max()),
        "inner_wape_median": float(log["wape"].median()),
        "default_ho": float(df.set_index("model").loc["lgbm_default", "ho_wape"]),
        "tuned_ho": float(df.set_index("model").loc["lgbm_tuned", "ho_wape"]),
        "default_bt": float(df.set_index("model").loc["lgbm_default", "bt_wape"]),
        "tuned_bt": float(df.set_index("model").loc["lgbm_tuned", "bt_wape"]),
    }
    json.dump(
        {"routing": chosen, "tuning": tuning, "best_params": blob["best"]},
        (OUT / "final.json").open("w"),
        indent=2,
    )

    # noise floor: Poisson noise puts a hard limit on slow-mover accuracy
    floors = {}
    for k in kinds:
        ys = np.concatenate([panel.y[s][~panel.so[s]] for s in panel.skus if panel.kind[s] == k])
        floors[k] = (
            float(np.mean(np.sqrt(ys.mean() * 2 / np.pi)) / ys.mean()) if ys.mean() else None
        )
    print("noise-floor WAPE (approx, Poisson):", {k: round(v, 3) for k, v in floors.items()})
    pd.set_option("display.width", 250)
    print(df.round(3).to_string(index=False))
    print(json.dumps({"routing": chosen, "tuning": tuning}, indent=1))


if __name__ == "__main__":
    main()
