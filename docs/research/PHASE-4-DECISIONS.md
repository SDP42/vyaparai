# Phase 4: what shipped, what did not, and why

The benchmark ([PHASE-4-BENCHMARK.md](PHASE-4-BENCHMARK.md)) compared 21 model variants on two years of
synthetic data. The product follows its evidence, not the original wish list.

| Planned | Decision | Evidence and reason |
|---|---|---|
| LightGBM global model | **Shipped** | Best on fast and mid movers (error 0.18 and 0.29 vs 0.26 and 0.40 for repeating last week) |
| Theta / ETS family | **Theta shipped**, ETS and ARIMA not | Theta scored 0.241 in the product against 0.247 for statsforecast's AutoTheta, so a 60-line version loses nothing. AutoETS/ARIMA gave no gain over it and statsforecast pulls in numba and a large install |
| Seasonal average | Shipped as the fallback and cold-start | Needs only a few weeks; ties Theta on slow movers |
| Croston, SBA, TSB, ADIDA, IMAPA | Not shipped | Error 0.278 to 0.288 vs 0.241 for Theta; they did no better than a plain average on slow movers |
| Ensembles | Not shipped | Averaging with other models did not beat LightGBM alone (0.229 to 0.241 vs 0.225) |
| Hyperparameter tuning (Optuna) | **Shipped as an optional random search** | 24 Optuna trials changed the holdout error by about 1 % (noise), and 12 random trials on the 2-year data found nothing better than the defaults. So it is off by default and only adopted if it helps by 1 % on data before the backtests. Random search avoids an extra dependency |
| Pretrained model (Chronos-Bolt) | **Not shipped** | Zero-shot error 0.262 (small) is worse than the shipped Theta (0.241) and needs PyTorch plus a model download; its licence must be confirmed first |
| Quantile LightGBM intervals | Replaced by conformal intervals | One calibration method works for every model; coverage is measured and corrected to 80 % |
| Model registry (MLflow) | Own tables instead | Versions, status, accuracy, options, rollback and a ship gate live in the product database; no extra service to run |
| Festive-peak correction | Warning plus owner-set uplift | Every model under-forecast the peak in the benchmark. A fixed uplift copied from industry claims would be a guess, so the owner chooses it and it is labelled as theirs |
| Prophet, N-HiTS | Not added | Only worth adding if they beat the shipped mix on the holdout; nothing in the benchmark suggested they would, and they are heavy |

## How shipping is controlled

1. **Per series**, the best of LightGBM, Theta and the recent average is chosen by backtest error (LightGBM must beat the best simple method by 10 % on sparse products).
2. **Per run**, the pooled error is compared with repeating last week. A new version that fails this while the active one passed is saved as *not used*.
3. **Per owner**, any version can be made active again; the choice is audited.

## What to revisit

- Re-run the benchmark on real shop data. Rankings can change, and the synthetic data has no real price or weather effects.
- A shop with two or more years of history is the case where yearly features and the festive peak matter most; add a peak-bias check from the shop's own past peaks.
- If Chronos or ETS ever beat Theta on real data, add them as further candidates behind the same selection and gate.
