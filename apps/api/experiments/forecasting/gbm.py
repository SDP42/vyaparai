"""Global LightGBM forecaster (direct multi-horizon: the step ahead is a feature)."""

import math
from datetime import date

import lightgbm as lgb
import numpy as np
import pandas as pd

from .common import H, Panel, clean

PEAKS = [date(2024, 11, 1), date(2025, 10, 20), date(2026, 11, 8)]
DEFAULT = {
    "n_estimators": 300, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 20,
    "feature_fraction": 0.9, "bagging_fraction": 0.9, "lambda_l2": 0.0,
}  # fmt: skip


def festive_gap(d: pd.Timestamp) -> float:
    return float(min(abs((d.date() - p).days) for p in PEAKS))


def build(
    panel: Panel, origins: list[int], cleaned: dict[str, np.ndarray], *, targets: bool, skus=None
):
    rows, ys = [], []
    for si, s in enumerate(skus or panel.skus):
        y = cleaned[s]
        for o in origins:
            if o < 56:
                continue
            hist = y[:o]
            base = {
                **{f"lag{i}": hist[-i] for i in (1, 2, 3, 7, 14, 21, 28)},
                "m7": hist[-7:].mean(), "m14": hist[-14:].mean(), "m28": hist[-28:].mean(), "m56": hist[-56:].mean(),
                "sd28": hist[-28:].std(), "sku": si,
            }  # fmt: skip
            for k in range(1, H + 1):
                j = o + k - 1
                if j >= len(y):
                    break
                m = math.ceil(k / 7)
                d = panel.dates[j]
                r = {
                    **base, "k": k, "dow": d.dayofweek, "dom": d.day, "doy": d.dayofyear, "month": d.month,
                    "festive_gap": festive_gap(d), "disc": panel.disc[s][j],
                    "sw1": y[j - 7 * m], "sw2": y[j - 7 * (m + 1)], "t": j, "o": o, "name": s,
                }  # fmt: skip
                rows.append(r)
                ys.append(y[j] if targets else np.nan)
    X = pd.DataFrame(rows)
    return X, np.array(ys)


def feature_cols(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if c not in ("t", "o", "name")]


def train_predict(
    panel: Panel,
    origin: int,
    params: dict,
    *,
    train_step: int = 3,
    seed: int = 0,
    objective: str = "regression",
) -> pd.DataFrame:
    """Train on windows whose targets all lie before ``origin``; forecast the next H days."""
    cleaned = {s: clean(panel.y[s], panel.so[s]) for s in panel.skus}
    train_origins = list(range(56, origin - H + 1, train_step))
    Xtr, ytr = build(panel, train_origins, cleaned, targets=True)
    keep = ~np.array([panel.so[n][t] for n, t in zip(Xtr["name"], Xtr["t"], strict=True)])
    cols = feature_cols(Xtr)
    model = lgb.LGBMRegressor(
        objective=objective, random_state=seed, verbose=-1, n_jobs=4, **params
    )
    model.fit(Xtr[cols][keep], ytr[keep], categorical_feature=["sku"])
    # forecast uses history strictly before origin (targets unused)
    pred_panel_y = {s: np.concatenate([cleaned[s][:origin], np.zeros(H)]) for s in panel.skus}
    Xte, _ = build(panel, [origin], pred_panel_y, targets=False)
    yhat = model.predict(Xte[cols])
    return pd.DataFrame({"sku": Xte["name"], "t": Xte["t"], "yhat": np.clip(yhat, 0, None)})
