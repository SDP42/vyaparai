# Model catalogue

Every model that ships in Vyapar AI has an entry here and a **model card** (template below).
Status: ⬜ planned · 🟡 in progress · ✅ shipped. Full method: [research/PHASE-4-ML-PLAN.md](research/PHASE-4-ML-PLAN.md).

## Forecasting (Phase 4)

| Model | Family | Status | Used for |
|---|---|---|---|
| Naive, seasonal naive (7 d), moving average, drift | Baseline | ⬜ | The yardstick every model must beat |
| AutoETS, AutoARIMA, Theta, MSTL, Holt-Winters | Statistical | ⬜ | Smooth and erratic series with ≥ 2 cycles |
| Croston, Croston-SBA, TSB, ADIDA/IMAPA | Intermittent | ⬜ | Sparse and lumpy products |
| LightGBM (recursive + direct), ridge on lags, random forest | Global ML | ⬜ | One model across all SKUs with calendar, price, discount features |
| LightGBM quantile (p10/p50/p90), conformal intervals | Probabilistic | ⬜ | Prediction intervals with checked coverage |
| Mean/median ensemble, weighted and stacked ensembles | Ensemble | ⬜ | Usually the best single forecast |
| Prophet, N-HiTS / N-BEATS | Optional (P2) | ⬜ | Only if they beat the ensemble on the holdout |

## Other models

| Model | Phase | Status | Task |
|---|---|---|---|
| RFM segments (k-means + rules) | 3 | ⬜ | Customer groups |
| Churn / lapse propensity (LightGBM, logistic baseline) | 3–4 | ⬜ | Which regulars may stop buying |
| Sales anomaly detection (STL residuals, Isolation Forest) | 4 | ⬜ | Unusual days |
| Demand-pattern classifier (ADI / CV²) | 4 | ⬜ | Route each SKU to the right model family |
| Basket affinity (association rules) | 3 | ⬜ | Bundles and cross-sell |
| Review sentiment and aspects | 6 | ⬜ | TF-IDF baseline vs multilingual transformer |
| Document retrieval and reranking | 7 | ⬜ | Cited answers |

## Evaluation scorecard (blueprint §46)

| Task | Headline metrics | Must beat |
|---|---|---|
| Forecast | WAPE (headline), MAE, RMSE, MASE, bias, interval coverage, forecast value added | Seasonal-naive baseline on the holdout |
| Churn | PR-AUC, recall at chosen precision, calibration; time-based split | Recency rule |
| Sentiment | Macro-F1, per-class precision/recall, per-language errors | TF-IDF + logistic regression |
| Retrieval | Recall@K, MRR, citation correctness, faithfulness, abstention | BM25 |

## Model card template

```
# <Model name> · version <n> · workspace <id>
Purpose / decision supported:
Training data: window, rows, series count, data hash, source datasets
Method: algorithm, features, hyperparameters (tuned: yes/no, trials, search space)
Evaluation: protocol (rolling origin, horizons), folds, holdout window
Results: metrics vs baseline (table), per-series win rate, bias, interval coverage
Calibration / failure modes: where it is worse than baseline; low-confidence rules
Known limitations and assumptions:
Reproducibility: seed, library versions, code commit, run id
Ship decision: shipped / baseline shown instead, and why
```
