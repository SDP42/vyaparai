# 0007 · ML approach: many models, one protocol, a baseline to beat

- **Date:** 2026-11-08 · **Status:** Accepted

**Context.** The owner wants proper training, hyperparameter tuning and several forecasting models.
Retail evidence shows no single model wins everywhere, and tuning can leak the future if done carelessly.

**Decision.**
1. Run a **portfolio** (baselines, statistical, intermittent-demand, global gradient boosting, ensembles) through
   **one** evaluation protocol: rolling-origin backtests, a single-use final holdout, and shared metrics
   (WAPE headline, MASE, bias, interval coverage, forecast value added).
2. Tune with **Optuna inside the training period only**, time-aware folds, seeded and logged.
3. **Ship gate:** a model is exposed only if it beats seasonal naive on the holdout; otherwise the product shows the baseline and says so.
4. Intervals by **split-conformal** on backtest errors (model-agnostic) with measured coverage.
5. Every run stores seed, library versions, data hash, code commit, parameters and a model card.
6. Our own registry tables back the UI; MLflow (SQLite) is an optional development aid.

**Consequences.** More work than "fit one model" (≈ 12–14 days) but results are defensible and reproducible.
Small workspaces may only get baselines, and the UI must say so. Deep models stay optional until they earn their CPU cost.
Details: [research/PHASE-4-ML-PLAN.md](../research/PHASE-4-ML-PLAN.md).
