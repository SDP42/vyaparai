# ML plan: forecasting and the model portfolio

_Date: 2026-11-08 · Blueprint sections: §16 Forecasting, §17 NLP, §46 Evaluation scorecard_

The owner asked for **proper training, hyperparameter tuning and many forecasting models**. This plan
turns that into a pipeline that is honest (no leakage, a baseline to beat), reproducible (every run
is recorded) and affordable (runs on a laptop CPU).

## 1. What the research says

| Finding | Source | Consequence for the plan |
|---|---|---|
| In one M5 retail comparison, ARIMA and LightGBM were close (RMSE ≈ 1.10 vs 1.19) and Prophet far worse; LightGBM was much faster; the authors say tuning would help | [Hasan et al. 2022](https://arxiv.org/pdf/2203.06848) | No single winner: **compare many models per series**; keep Prophet only as an optional candidate |
| Validation folds must be later in time than training data | [Towards Data Science: CV for time series](https://towardsdatascience.com/how-to-correctly-perform-cross-validation-for-time-series-b083b869e42c/) | Rolling-origin (expanding window) CV only; never shuffled K-fold |
| Hyperparameter search can itself leak the future; use time-aware folds and keep an untouched test split | [Yohou-Optuna concepts](https://yohou-optuna.readthedocs.io/en/latest/pages/explanation/concepts/), [AutoML tuning guide](https://www.typingmind.com/skills/mindrally-automl-hyperparameter-optimization) | Tune **inside the training period**; a final holdout is touched once |
| Lagged features can leak across groups; fit scalers/lags per fold | [Purged group time-series split](https://arxiv.org/pdf/2310.04536) | Build features with `shift()` only; recompute inside each fold |
| LightGBM + `TimeSeriesSplit` + Optuna (hundreds of trials) is a common, workable recipe | [LightGBM forecasting paper](https://arxiv.org/pdf/2501.07580) | Optuna TPE with a trial budget and pruning |
| No consensus between Croston, SBA and TSB; results depend on data. MASE can favour under-forecasting on sparse demand; pair it with a bias measure | [Doszyn 2020 via UM](https://www.um.edu.mt/library/oar/bitstream/123456789/75926/1/Accuracy_of_intermittent_demand_forecasting_systems_in_the_enterprise.pdf), [Switch-Hurdle 2026](https://arxiv.org/pdf/2602.22685) | Include **all three** as candidates; always report **bias** next to WAPE/MASE |
| MLflow can use a single SQLite file for tracking and the model registry | [MLflow configuration docs](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.config.html) | Optional MLflow (SQLite) for experiments; product metadata lives in our own tables |

Not confirmed by my searches (from my own knowledge, verify before citing): top M5 entries were mostly
LightGBM-based global models with calendar and price features, and M5 was scored with a scaled metric (WRMSSE).
The search found nothing on conformal prediction intervals, so §4.4 is a design choice, not a cited result.

## 2. The model portfolio

### 2.1 Forecasting models (Phase 4)

| Family | Models | When it is used | Library |
|---|---|---|---|
| **Baselines (must be beaten)** | Naive · seasonal naive (7 d) · moving average · drift | Always run; the yardstick for "forecast value added" | own / statsforecast |
| **Classical statistical** | AutoETS · AutoARIMA · Theta / DOTM · MSTL (+ETS) · Holt-Winters | Series with ≥ 2 seasonal cycles | statsforecast |
| **Intermittent demand** | Croston · Croston-SBA · TSB · ADIDA / IMAPA | Sparse or lumpy products (see §3.2) | statsforecast |
| **Global machine-learning** | LightGBM (recursive and direct) · regularised linear model on lags · random forest (reference) | One model across all SKUs with lag, calendar, price and discount features | lightgbm, scikit-learn |
| **Probabilistic** | LightGBM quantile objective (p10/p50/p90) · conformal intervals around any model | Intervals for every forecast | lightgbm, own |
| **Ensembles** | Mean/median of top-k models · weights from backtest error · stacking by a ridge meta-model | Usually beats the best single model | own |
| **Optional (P2)** | Prophet (holidays) · N-HiTS / N-BEATS via neuralforecast | Only if it beats the ensemble on the holdout; CPU cost must stay reasonable | prophet, neuralforecast |

### 2.2 Other ML models in the product (later phases)

| Model | Phase | Task | Metric | Baseline |
|---|---|---|---|---|
| Customer segments (RFM + k-means) | 3 | Interpretable groups | Segment stability, silhouette | Rule-based RFM bands |
| **Churn / lapse propensity** | 3–4 | Will a regular stop buying in the next N days | PR-AUC, recall at chosen precision, calibration; **time-based split** | Recency rule |
| **Anomaly detection** | 4 | Unusual days (STL residual z-score, Isolation Forest) | Precision on injected anomalies | Fixed threshold |
| Demand-pattern classifier (ADI/CV²) | 4 | Route a SKU to the right model family | Routing accuracy vs best backtest model | Single model |
| Basket affinity (association rules) | 3 | "Bought together" for bundles | Lift, support | None |
| Review sentiment and aspects | 6 | See blueprint §17 | Macro-F1, per-class P/R | TF-IDF + logistic regression |
| Document retrieval | 7 | See blueprint §18 | Recall@K, MRR | BM25 |

## 3. Data and features

### 3.1 The modelling panel
One row per **(SKU, day)** in the workspace business-date, zero-filled, with: units, net sales, orders,
average discount rate, price, and flags. **Stock-out days are censored, not zero demand**: a zero while
stock was zero is excluded from error metrics (needs inventory snapshots; until then a long run of zeros
for a normally fast mover is flagged as *possible stock-out*).

### 3.2 Demand pattern routing (Syntetos–Boylan classes)
Compute the average demand interval (ADI) and squared coefficient of variation of non-zero demand (CV²) per SKU:
**smooth** → ETS/ARIMA/LightGBM · **erratic** → LightGBM/ETS · **intermittent** → Croston/SBA/TSB · **lumpy** → TSB/aggregate to weekly.
Cut-offs (ADI 1.32, CV² 0.49) are the published defaults; they are a **starting point**, and the backtest has the final say.

### 3.3 Feature set for global models
- **Lags** (1, 2, 3, 7, 14, 21, 28) and **rolling** mean/std/min/max over 7/14/28 days, all via `shift()` so no leakage
- **Calendar:** day of week, day of month, month-end/start, week of year, pay-day windows (1st and 7th)
- **Festive and wedding seasons:** a dated holiday table (dates move each year), with days-to/since features
- **Price and discount:** list price, discount rate, price change vs 28-day median
- **Product:** SKU and category as categorical features; days since first sale; days since last sale
- **Hierarchy:** category-level lagged demand as a feature for sparse SKUs
- **Exogenous (optional):** weather and local events are out of scope for the MVP

## 4. Training, tuning and evaluation protocol

### 4.1 Splits (never shuffled)
```
|──────────── train + tuning period ────────────|── holdout (last 28–30 d) ──|
 expanding window, step 7 d, horizon h ∈ {7,14,30}        touched once at the end
```
- **Rolling-origin backtest:** initial window ≥ 8 weeks (more if seasonal), step 7 days, forecast h days ahead per fold.
- **Hyperparameter search runs only on the train + tuning period.** The holdout scores the *final* chosen model once.
- Series with < 8 weeks of history get only baselines and a **low-confidence** label.

### 4.2 Hyperparameter tuning (Optuna)
| Model | Tuned | Search |
|---|---|---|
| LightGBM | `num_leaves`, `learning_rate`, `n_estimators` (with early stopping inside the fold), `min_child_samples`, `feature_fraction`, `bagging_fraction`, `lambda_l1/l2`, lag set | TPE sampler, median pruner, 50–200 trials (budget configurable) |
| ETS / ARIMA / Theta | Auto-selection by AICc; seasonality length; damped trend | Library auto-fit; small grid on season length |
| Croston family | Smoothing α (and β for TSB) | Grid 0.05–0.5 |
| Ensemble | Top-k, weighting scheme | Chosen on backtest folds |

Objective = mean **WAPE** (and pinball loss for quantile models) across folds; ties broken by **bias**.
Every trial is logged. Searches are seeded so a run reproduces.

### 4.3 Metrics
MAE · RMSE · **WAPE** (headline) · sMAPE (reported with a caveat: unstable near zero) · **MASE** (vs seasonal naive) ·
**Bias %** (mean error ÷ mean actual) · pinball loss and **interval coverage** for probabilistic models ·
**Forecast Value Added** = (baseline error − model error) ÷ baseline error · per-series **win rate** vs baseline.
For intermittent SKUs, MASE alone can reward under-forecasting, so the report always includes bias and a stock-cover check.

### 4.4 Prediction intervals
Split-conformal: take the empirical quantiles of absolute backtest errors **per horizon step**, apply them
around any point forecast (model-agnostic), and verify **coverage** (target 80 % nominal; reported actual coverage on the holdout).
Quantile LightGBM provides a second opinion.

### 4.5 Ship gate
A model is exposed in the product only if, on the **holdout**, it beats the seasonal-naive baseline on WAPE for
the workspace overall *and* wins on a majority of high-volume series. Otherwise the product shows the baseline
and says so. Per-series selection uses backtest error, never holdout error.

## 5. Platform: pipeline, registry, jobs

```
ml/
  data/        panel builder, demand classification, holiday calendar
  features/    lag/rolling/calendar/price features
  models/      baselines.py statistical.py intermittent.py gbm.py ensemble.py
  tuning/      optuna studies, search spaces
  evaluation/  backtest.py metrics.py intervals.py reports.py
  registry/    save/load, model cards, versions
  train.py     CLI: python -m ml.train --workspace <id> --horizon 14 --trials 100
```
- **Reproducibility:** seed, library versions, **data hash**, code git SHA and parameters are stored with every run.
- **Registry (own tables):** `model_runs` (config, metrics per fold, status), `model_versions` (artifact path, params,
  holdout metrics, ship decision), `forecasts` (series, horizon, point, p10/p50/p90, model version). The UI reads these.
- **Experiment tracking:** optional MLflow with a local SQLite store for comparing trials during development.
- **Execution:** a `forecast_training` job on the existing jobs table; progress by fold/trial; results are a **model card**
  (data window, metrics vs baseline, calibration, known limitations). Heavy runs use a worker process, not the web request.
- **Compute budget:** laptop CPU; statsforecast (Numba) for statistical models; LightGBM with `n_jobs`; global models train once
  per workspace, not per SKU.

## 6. Data needed to make this meaningful
The current demo file is 18 SKUs × 92 days, too short for seasonality or tuning. The generator gets a
`--days 730` mode that adds a weekly pattern, a trend, month-end and festive-season effects, price/discount
promotions, stock-outs and a few intermittent SKUs, **with a known data-generating process** so a backtest can be sanity-checked
(a model that cannot find a built-in weekly cycle is broken). A public dataset (decision D1) can be added for external benchmarking.

## 7. Work breakdown (Phase 4 → 4a–4e)

| Step | Scope | Effort | Exit |
|---|---|---|---|
| 4a | Longer synthetic data · panel builder · demand classification · metrics module · rolling-origin backtester · baselines | 2 d | Baselines backtested; metrics unit-tested on known series |
| 4b | statsforecast models (ETS, ARIMA, Theta, MSTL) · intermittent family (Croston, SBA, TSB, IMAPA) · per-series selection | 2–3 d | Leaderboard across model families |
| 4c | Features · LightGBM global model (recursive and direct) · quantile models · linear and RF references | 2–3 d | Global model compared with statistical models |
| 4d | Optuna tuning with pruning · ensembles/stacking · conformal intervals · holdout evaluation · ship gate | 3 d | Reproducible tuned run; coverage near nominal |
| 4e | Registry tables · training job · forecast API · model card · forecast UI (horizon picker, interval band, leaderboard, low-confidence flags) | 3 d | Forecast visible in the product with its model card |

**Total ≈ 12–14 days** (replaces the earlier 5–6 day estimate for Phase 4).

## 8. Risks and honest limits
- **Small data:** a small shop has few SKUs and short history; many series will only support baselines. The product must say so.
- **Overfitting by tuning:** mitigated by tuning inside folds and a single-use holdout.
- **Stock-outs hide demand:** without inventory snapshots, demand is under-estimated; flagged, fixed properly in Phase 5.
- **Festive dates move:** the holiday table is data, updated yearly; models are not told "it will be big" without a dated reason.
- **CPU cost:** deep models are P2 and gated on a measurable win.

## 9. Sources
- [Hasan et al., "A Comparative Study on Forecasting of Retail Sales" (2022)](https://arxiv.org/pdf/2203.06848)
- [How to correctly perform cross-validation for time series](https://towardsdatascience.com/how-to-correctly-perform-cross-validation-for-time-series-b083b869e42c/)
- [Yohou-Optuna: OptunaSearchCV concepts](https://yohou-optuna.readthedocs.io/en/latest/pages/explanation/concepts/)
- [AutoML hyperparameter optimization guide](https://www.typingmind.com/skills/mindrally-automl-hyperparameter-optimization)
- [Purged group time-series split for financial regimes](https://arxiv.org/pdf/2310.04536)
- [Assets forecasting with feature engineering for LightGBM](https://arxiv.org/pdf/2501.07580)
- [Accuracy of intermittent demand forecasting systems in the enterprise](https://www.um.edu.mt/library/oar/bitstream/123456789/75926/1/Accuracy_of_intermittent_demand_forecasting_systems_in_the_enterprise.pdf)
- [Switch-Hurdle: intermittent demand forecasting](https://arxiv.org/pdf/2602.22685)
- [MLflow configuration (tracking and registry URIs)](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.config.html)
