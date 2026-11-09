# Phase 4 model benchmark: what works, what needs tuning, what to ship

_2026-11-09 · code: `apps/api/experiments/forecasting/` · raw numbers: [phase4-benchmark-results.csv](phase4-benchmark-results.csv)_

## Question

Which forecasting models should the product use, does hyperparameter tuning pay off, and does a
pretrained model work without any training?

## Method (honest by construction)

- **Data:** synthetic but with *known* structure: 40 SKUs × 730 days, weekly cycle, yearly cycle, a
  festive-season peak, trend, promotions that lift demand, stock-out spells, and 1/3 slow movers with
  Poisson noise and occasional bulk buys. Known structure lets us judge models against a noise floor.
  **This is not real shop data**; see Limits.
- **Types:** 14 fast movers, 14 mid movers, 12 slow (intermittent / lumpy).
- **Horizon:** 14 days. **Backtest** = 6 rolling windows before the holdout (used to *choose*).
  **Holdout** = the last 28 days (two windows), scored once. Stock-out days are excluded from scoring.
- **Metric:** WAPE (lower is better), plus bias (negative = under-forecast) and forecast value added
  (FVA) versus the seasonal-naive baseline.
- **Models (21 runs):** naive, seasonal naive, seasonal average, historic average, AutoETS, AutoARIMA,
  AutoTheta, MSTL+ETS, Croston, Croston-SBA, TSB, ADIDA, IMAPA; **LightGBM** global model (default and
  Optuna-tuned, 24 trials, tuned only on data before the first backtest window); **Chronos-Bolt**
  pretrained (tiny and small, zero-shot, no training); ensembles; a router that picks per demand type.

## Results (holdout WAPE; backtest in the CSV)

| Model | Holdout WAPE | Bias | Fast | Mid | Slow | Gain vs seasonal naive |
|---|---|---|---|---|---|---|
| **LightGBM tuned** | **0.223** | −8.6 % | 0.182 | 0.299 | 0.755 | 28.8 % |
| **LightGBM default** | 0.225 | −8.9 % | 0.187 | 0.292 | 0.750 | 28.1 % |
| Ensemble LightGBM + Chronos | 0.239 | −11.0 % | 0.201 | 0.308 | 0.738 | 23.6 % |
| AutoTheta | 0.247 | −10.8 % | 0.208 | 0.316 | 0.782 | 21.1 % |
| AutoETS | 0.249 | −11.1 % | 0.211 | 0.315 | 0.775 | 20.5 % |
| Chronos-Bolt small (pretrained) | 0.262 | −13.1 % | 0.223 | 0.333 | 0.758 | 16.4 % |
| Chronos-Bolt tiny (pretrained) | 0.269 | −14.0 % | 0.231 | 0.337 | 0.764 | 14.2 % |
| AutoARIMA | 0.261 | −10.0 % | 0.222 | 0.332 | 0.770 | 16.6 % |
| Croston / SBA / TSB / ADIDA / IMAPA | 0.278–0.288 | −9 to −15 % | 0.240–0.251 | 0.347–0.355 | 0.773–0.796 | 8–11 % |
| Seasonal naive (baseline) | 0.313 | −11.5 % | 0.260 | 0.399 | 1.097 | 0 % |
| Naive | 0.350 | −18.7 % | 0.314 | 0.390 | 1.049 | −11.8 % |

Approximate noise floor (Poisson randomness nobody can forecast): fast ≈ 0.15, mid ≈ 0.27, slow ≈ 0.66.

## Findings

1. **LightGBM wins on fast and mid movers** (WAPE 0.18 and 0.29, close to the noise floors 0.15 and 0.27).
   It uses promotion, festive-calendar, lag and weekday features that the statistical models cannot see.
2. **Hyperparameter tuning is not needed for the default path.** 24 Optuna trials moved the backtest
   from 0.1834 to 0.1845 (no gain) and the holdout from 0.2251 to 0.2230 (1 % relative, inside noise). The
   worst trial was only 0.217 versus 0.184. The gain came from features and the global model, not from
   parameters. Keep tuning as an optional background job, not a requirement.
3. **A pretrained model works out of the box, but is not the best.** Chronos-Bolt small, with no training,
   beat seasonal naive by 16 % and was close to AutoETS, and took 3 seconds for all 40 series. It cannot use
   promotions or the festive calendar, so LightGBM beat it by 14 % relative. Averaging the two did **not**
   help here. Its place is **cold start**: new SKUs, new shops, or little history.
4. **Slow and intermittent SKUs are near the noise floor.** Best slow WAPE is 0.74–0.76 versus a floor of
   about 0.66, and the Croston family did no better than a plain average. Do not spend effort on these
   daily; forecast them at weekly level and show wide ranges.
5. **Every model under-forecasts the holdout (bias −9 to −22 %).** The holdout contains the festive peak
   (8 Nov 2026), which is harder than normal weeks. The product must warn about peak periods and
   calibrate bias around them (next step, below).
6. **Ensembles did not beat LightGBM**, so do not ship one by default. Routing by demand type chose
   LightGBM for fast and mid and a plain average for slow, giving the same 0.225 as LightGBM alone.
7. **Ship gate met:** LightGBM beats seasonal naive by 28 % and wins on 100 % of series.

## Selection by use case

| Use case | Model | Why |
|---|---|---|
| Fast and mid movers with 8+ weeks of history | **LightGBM global (defaults)** | Best accuracy, fast, uses promo and calendar |
| New SKU, new shop, or < 8 weeks of history | **Chronos-Bolt small** (pretrained), else seasonal average | Needs no training; 16 % better than seasonal naive |
| Few series or no GBM available | **AutoTheta / AutoETS** | Strong, simple, interpretable; 21 % better |
| Slow, intermittent, lumpy SKUs | **Weekly-level average or SBA**, wide range | At the noise floor; complexity buys nothing |
| Any series | Show **bias and an interval**, label confidence | Honest about uncertainty and peaks |
| Tuning | Optional, off by default | No measurable gain here |

## Limits (read before trusting)

- **Synthetic data.** Real shops have irregular promotions, price changes, supplier shortages and weather;
  rankings may change. Re-run this benchmark on each real workspace before trusting it.
- One dataset, one seed, 24 tuning trials, two pretrained sizes. Differences under about 2 % are noise.
- Holdout covers a festive peak, so its absolute error is higher than an ordinary month.
- Promotion plans were assumed known in advance for LightGBM (a shop usually knows its own offers).
- Stock-out days were taken as known flags; in real data they must be inferred (long zero runs, inventory).
- Chronos was tested zero-shot without covariates; later versions that accept covariates might do better.

## Decisions for Phase 4b onward

1. Build the product pipeline around **LightGBM global + AutoETS/Theta fallback + Chronos cold start**.
2. Add **festive-peak bias calibration** and conformal intervals; re-test on a held-out peak.
3. Make tuning an optional job; do not block the first release on it.
4. Re-run the benchmark automatically per workspace and store the result in the model card.
5. Dependency choice: the ML stack installs fine from conda-forge; PyPI was ~20× slower on the dev
   network. Decide at 4b whether the product image uses pip (uv group) or conda-forge.
