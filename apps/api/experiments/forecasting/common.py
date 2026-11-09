"""Shared loading, cleaning and scoring for the forecasting experiments."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
H = 14  # forecast horizon (days)
HOLDOUT = 28  # last days, scored once at the end (two 14-day windows)
FOLDS = 6  # backtest windows before the holdout, used for model selection


@dataclass
class Panel:
    df: pd.DataFrame  # sku, kind, date, units, price, discount_rate, stockout
    skus: list[str]
    kind: dict[str, str]
    y: dict[str, np.ndarray]  # raw units
    so: dict[str, np.ndarray]  # stock-out flag (bool)
    disc: dict[str, np.ndarray]
    dates: pd.DatetimeIndex
    T: int


def load() -> Panel:
    df = pd.read_csv(OUT / "panel.csv", parse_dates=["date"])
    skus = sorted(df["sku"].unique())
    g = {s: df[df["sku"] == s].sort_values("date") for s in skus}
    dates = pd.DatetimeIndex(g[skus[0]]["date"])
    return Panel(
        df=df,
        skus=skus,
        kind={s: g[s]["kind"].iloc[0] for s in skus},
        y={s: g[s]["units"].to_numpy(float) for s in skus},
        so={s: g[s]["stockout"].to_numpy(bool) for s in skus},
        disc={s: g[s]["discount_rate"].to_numpy(float) for s in skus},
        dates=dates,
        T=len(dates),
    )


def clean(y: np.ndarray, so: np.ndarray) -> np.ndarray:
    """Replace stock-out days (zeros that are not real demand) with the recent same-weekday level."""
    out = y.copy()
    for t in np.flatnonzero(so):
        prev = [out[t - 7 * k] for k in range(1, 5) if t - 7 * k >= 0 and not so[t - 7 * k]]
        out[t] = float(np.mean(prev)) if prev else float(np.mean(y[max(0, t - 28) : t][~so[max(0, t - 28) : t]]) if t else 0.0)
    return out


def window_origins(T: int) -> dict[str, list[int]]:
    """Origins (index of first forecast day) for backtest folds and for the holdout."""
    cut = T - HOLDOUT
    return {
        "backtest": [cut - H * k for k in range(FOLDS, 0, -1)],
        "holdout": [cut, cut + H],
    }


def score(preds: pd.DataFrame, panel: Panel) -> dict[str, float | None]:
    """preds columns: sku, t (day index), yhat. Stock-out days are excluded from scoring."""
    rows = []
    for s, grp in preds.groupby("sku"):
        t = grp["t"].to_numpy(int)
        keep = ~panel.so[s][t]
        rows.append(
            pd.DataFrame(
                {"sku": s, "kind": panel.kind[s], "y": panel.y[s][t][keep], "yhat": np.clip(grp["yhat"].to_numpy(float)[keep], 0, None)}
            )
        )
    d = pd.concat(rows)
    out: dict[str, float | None] = {}
    for name, part in [("all", d)] + [(k, d[d["kind"] == k]) for k in sorted(d["kind"].unique())]:
        tot = part["y"].sum()
        out[f"wape_{name}"] = float((part["yhat"] - part["y"]).abs().sum() / tot) if tot else None
        out[f"bias_{name}"] = float((part["yhat"].sum() - tot) / tot) if tot else None
    return out


def per_series_wape(preds: pd.DataFrame, panel: Panel) -> dict[str, float]:
    res = {}
    for s, grp in preds.groupby("sku"):
        t = grp["t"].to_numpy(int)
        keep = ~panel.so[s][t]
        y = panel.y[s][t][keep]
        yh = np.clip(grp["yhat"].to_numpy(float)[keep], 0, None)
        if y.sum() > 0:
            res[s] = float(np.abs(yh - y).sum() / y.sum())
    return res
