"""Zero-shot pretrained forecaster (Chronos-Bolt) on the same windows as the benchmark.

No training or tuning: the model sees only each series' history and predicts the next H days.
Run:  python -m experiments.forecasting.pretrained  [model id, default amazon/chronos-bolt-tiny]
"""

import pickle
import sys
import time

import numpy as np
import pandas as pd
import torch
from chronos import BaseChronosPipeline

from .common import H, OUT, clean, load, score, window_origins


def main(model_id: str = "amazon/chronos-bolt-tiny") -> None:
    panel = load()
    pipe = BaseChronosPipeline.from_pretrained(
        model_id, device_map="cpu", torch_dtype=torch.float32
    )
    origins = window_origins(panel.T)
    cleaned = {s: clean(panel.y[s], panel.so[s]) for s in panel.skus}
    res: dict[str, pd.DataFrame] = {}
    t0 = time.time()
    for part in ("backtest", "holdout"):
        frames = []
        for o in origins[part]:
            ctx = [torch.tensor(cleaned[s][:o], dtype=torch.float32) for s in panel.skus]
            _, mean = pipe.predict_quantiles(
                ctx, prediction_length=H, quantile_levels=[0.1, 0.5, 0.9]
            )
            # median ("0.5") is the point forecast; use the mean forecast too
            q = _.numpy()[:, :, 1]
            for i, s in enumerate(panel.skus):
                frames.append(pd.DataFrame({"sku": s, "t": np.arange(o, o + H), "yhat": q[i]}))
        res[part] = pd.concat(frames)
    name = "chronos_" + model_id.split("-")[-1]
    print(
        name,
        f"{time.time() - t0:.0f}s",
        {
            k: round(v, 3)
            for k, v in score(res["holdout"], panel).items()
            if v is not None and "all" in k
        },
    )
    with (OUT / f"pretrained_{name}.pkl").open("wb") as f:
        pickle.dump({name: res}, f)


if __name__ == "__main__":
    main(*(sys.argv[1:2]))
