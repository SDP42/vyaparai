# Model catalogue

Every model that ships in Vyapar AI has an entry here and a **model card** (template below).
Status: ✅ shipped · not shipped (benchmarked or judged, with reasons). Full method: [research/PHASE-4-ML-PLAN.md](research/PHASE-4-ML-PLAN.md).

## Forecasting (Phase 4)

What shipped follows the benchmark, not the original wish list: [research/PHASE-4-DECISIONS.md](research/PHASE-4-DECISIONS.md).

| Model | Family | Status | Used for |
|---|---|---|---|
| Naive, seasonal naive (7 d), moving average, drift | Baseline | ✅ | The yardstick every model must beat |
| Seasonal average | Baseline | ✅ | Fallback and cold start (needs a few weeks of history) |
| Theta (own 60-line implementation) | Statistical | ✅ | Smooth and erratic series, slow movers |
| LightGBM global model (with an optional random search) | Global ML | ✅ | Fast and mid movers; one model across SKUs with calendar, price and discount features |
| Conformal prediction intervals | Probabilistic | ✅ | Intervals whose coverage is measured and corrected to 80% (replaced quantile LightGBM) |
| AutoETS, AutoARIMA, Croston family, ensembles, Prophet, N-HiTS, Chronos-Bolt | Various | Not shipped | Benchmarked or judged; none beat the shipped mix on the data we had (reasons in the decisions file) |

Selection: per series the best of LightGBM, Theta and the recent average by backtest error; per run the pooled error is
compared with repeating last week and a failing version is saved as "not used"; any version can be made active again
and the choice is audited.

## Other models

| Model | Phase | Status | Task |
|---|---|---|---|
| RFM segments (rules) | 3 | ✅ | Customer groups |
| Basket affinity (support, confidence, lift) | 3 | ✅ | Bundles and cross-sell |
| Demand-pattern classifier (ADI / CV²) | 4 | ✅ | Route each SKU to the right family |
| Sales anomaly and alert rules (fixed rules, not learned) | 14 | ✅ | Unusual days, margin leaks, stock-out risk |
| Review sentiment and themes (lexicon plus a per-shop logistic regression in NumPy) | 6 | ✅ | English, Hindi and Hinglish; no multilingual transformer (CPU-only, free-only) |
| Document retrieval (multilingual MiniLM embeddings fused with BM25) | 7 | ✅ | Cited passages |
| Bill OCR (RapidOCR, Tesseract fallback, pypdf for text PDFs) | 15B | ✅ | Supplier bills, always checked by a person |
| Question understanding (keywords, phrases, spoken-Hindi skeleton matching, number parser, glossary and sound-class product matching) | 8, 20 | ✅ | Assistant routing in three languages; no language model |
| Speech to text (Whisper medium, int8, via faster-whisper) | 20 | ✅ | Spoken questions; MIT code and weights; see [VOICE](VOICE.md) |
| Investigation workflows (LangGraph graphs over existing services) | 9 | ✅ | "Why did sales change?"; no model in the loop |

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
