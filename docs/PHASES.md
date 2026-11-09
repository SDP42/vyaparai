# Delivery phases

Vyapar AI is built in small, demonstrable phases. Each phase ends with a working vertical
slice, tests and updated docs. A phase is **done** only when it meets the
[definition of done](#definition-of-done) — a polished screen backed by mocked data is not a
finished feature.

Live status (✅ / 🟡 / ⬜) is tracked in [ROADMAP.md](ROADMAP.md). This file describes *what*
each phase contains and its exit criteria.

| Phase | Name | Blueprint weeks | Priority | Status |
|---|---|---|---|---|
| 0 | Foundation & discovery | 1, 3 | P0 | ✅ (3 small items open) |
| M | Marketing site: opening + landing page | 2 | P0 | ✅ (recorded audio open) |
| 1 | Data ingestion & quality | 4 | P0 | ✅ |
| 2 | Metric layer & sales analytics (command center) | 5 | P0 | ✅ |
| 3 | Customer & product intelligence | 6 | P0 | ✅ |
| 3B | Campaigns & retention automation (**C1 done**: audiences, margin-guarded offers, messages, holdout, CSV; C2–C4 consent, sending, measurement still to do; [plan](research/CAMPAIGNS-PLAN.md)) | 9 | P1 | 🟡 |
| 4 | Forecasting & predictive MVP | 7 | P0 | ⬜ |
| F2 | App shell wired to real APIs | 2–7 | P0 | ⬜ |
| — | **MVP release (end-to-end journey works)** | — | — | — |
| 5 | Inventory & decision support | 8 | P1 | ⬜ |
| 6 | NLP review intelligence | 9 | P1 | ⬜ |
| 7 | Document intelligence & RAG | 10 | P1 | ⬜ |
| 8 | Vyapar Copilot & safe tool use | 11 | P1 | ⬜ |
| 9 | Agent workflows (LangGraph) | 12 | P1 | ⬜ |
| 10 | Recommendations & reporting | 13 | P2 | ⬜ |
| 11 | Hardening, deployment & launch | 14–16 | P0 for launch | ⬜ |
| 12 | Daily and weekly digest (email now; WhatsApp copy-paste; [notes](research/DIGEST.md)) | - | P1 | ✅ |
| 13 | Cash and credit (udhaar) intelligence | - | P1 | ⬜ |
| 14 | Alerts and anomalies (rules, lifecycle, sidebar badge, digest link; [notes](research/ALERTS.md)) | - | P1 | ✅ |
| 15 | Connectors and scheduled imports | - | P1 | ⬜ |
| 15B | Cost history and margin-leak tracking (**done** from per-sale costs, with price suggestions; purchase-bill import still to do; [plan](research/COST-TRACKING.md)) | - | P1 | ✅ |
| 16 | Pricing and promotion advisor | - | P2 | ⬜ |
| 17 | Multi-store and staff | - | P2 | ⬜ |
| 18 | Mobile-first (PWA) and Hinglish/Hindi | - | P1 | ⬜ |
| 19 | Benchmarks and goals | - | P2 | ⬜ |

**MVP journey (blueprint §03):** create workspace → upload retail dataset → map columns →
review validation → command center → sales investigation → forecast → grounded question.

---

## Phase 0 — Foundation & discovery

**Goal:** a reliable, tenant-safe API skeleton and a precise product contract.

- [x] Monorepo layout (`apps/api`, `apps/web`, `ml`, `rag`, `agents`, `docs`, `scripts`, `infra`)
- [x] FastAPI app factory, versioned `/api/v1`, typed settings, `.env.example`
- [x] SQLAlchemy 2.0 models: users, workspaces, memberships, datasets, jobs, audit logs
- [x] Commerce core models: products, customers, orders, order_items (line-item grain)
- [x] Alembic migrations + test proving models and migrations never drift
- [x] Auth: Argon2id hashing, short-lived JWT, timing-safe login
- [x] Workspace context dependency + role hierarchy (owner > admin > analyst > viewer)
- [x] Non-members get 404 (no workspace probing); audit log for sensitive actions
- [x] Request IDs, structured JSON logs, uniform error envelope, health/readiness probes
- [x] Tests for health, auth, tenancy boundaries, security and migrations
- [x] CI (lint, format, type-check, tests), PR/issue templates
- [ ] Decide on a public benchmark dataset + licence (see [RESEARCH.md](RESEARCH.md#3-starter-datasets)); synthetic data is already in use
- [ ] Wireframes for the command center and sales explorer (done in code during Phase 2)
- [ ] Decide product name/trademark question (see [RESEARCH.md](RESEARCH.md#naming-risk))

**Exit:** migrations run cleanly; protected-API tests prove tenant boundaries. ✅

## Phase M — Marketing site: cinematic opening + landing page

Driven by the two-page master prompt; detailed plan in [frontend/PHASE-1-REPORT.md](frontend/PHASE-1-REPORT.md).

- [x] Phase 1: repository inspection and visual direction report
- [x] Landing page in the yellow "Bahi-Khata" design (owner's choice): simple hero, story scroll,
      zoom reveal, features, principles, CTA
- [x] One token source; Bricolage + Instrument Serif typography
- [x] Responsive at desktop, tablet and mobile; reduced-motion paths; production build passes
- [x] Key-and-lock opening with HDRI + CC0 PBR textures, slatted shutter, brass padlock, cut key, sound, skip
- [x] Religious motifs removed
- [x] Realism polish: depth of field, bloom, vignette, film grain, detailed interior goods
- [x] Scroll-scrubbed, reversible unlock (0–20–45–60–75–100 %)
- [x] Shop interior (labelled goods, jars, sacks, counter) and ambience; sounds synced to scroll
- [ ] Recorded (not synthesized) audio
- [x] Shop → Vyapar.ai hand-off (captions, cream fade, brand reveal, hero)
- [ ] Short-viewport polish for pinned sections; full visitor-journey test

## Phase 1 — Data ingestion & quality ✅

- [x] `POST /workspaces/{id}/datasets` upload (CSV/XLSX), 25 MB / 200k-row limits, encoding fallback, file-signature check
- [x] SHA-256 file hash → duplicate detection per workspace (409 with a link to the existing upload)
- [x] Inspection: headers (blank/duplicate-safe), sample rows, inferred types, missingness
- [x] Column mapping with synonym-based suggestions (billing-tool headers like "Bill No", "Rate", "Qty")
- [x] Row-level validation (dates, numbers, ₹/lakh commas, statuses, cross-row order consistency);
      accepted/rejected counts reconcile; downloadable error CSV
- [x] Transactional normalisation into products / customers / orders / order_items; re-imports skip
      orders that already exist (idempotent)
- [x] Background import job with status on `GET /jobs/{id}`; failures roll back and are recorded
- [x] Synthetic demo dataset generator with fixed seed (`scripts/generate_demo_data.py`)
- [x] Frontend: create account → create workspace → 4-step import wizard → data summary + upload history
- [x] 25 ingestion tests (54 total); end-to-end check on the 8,188-row sample in the browser

**Exit:** met. The sample file imports reproducibly (8,025 valid / 163 rejected; net sales reconcile).

**Known limits:** returns (negative quantities) are rejected for now; a rejected line inside a
multi-line order leaves the rest of that order imported; job progress jumps 10 → 100 (one transaction).

## Phase 2 — Metric layer & sales analytics ✅

Design is justified in [research/PHASE-2-RESEARCH.md](research/PHASE-2-RESEARCH.md); definitions in [METRICS.md](METRICS.md).

**Backend**
- [x] Business-date column on orders (workspace-timezone day) + migration with backfill
- [x] Versioned metric registry: key, label, unit, formula text, inclusions/exclusions, version
- [x] One aggregation engine for all metrics (net sales, gross, discounts, units, orders, AOV, units per order,
      discount rate, gross profit, margin with cost coverage, active/new/repeat customers)
- [x] Date range, comparison (previous period · same weekdays last year · none), filters (category, channel, region, product)
- [x] Trend (day/week/month, gap-filled), category / channel / region / weekday mix, top and bottom products
- [x] Driver analysis: volume, price, mix, new/discontinued products and discounts that **sum exactly** to the change
- [x] Contribution by product / category / channel; rule-based insights with evidence references
- [x] Drill-through to supporting order lines (paginated, workspace-scoped)
- [x] Every response carries period, currency, filters, metric version and data freshness; coverage warnings
- [x] Tests on fixtures with hand-computed answers, tenancy tests, reconciliation tests

**Frontend**
- [x] App shell for accounts: sidebar (Command center · Sales · Data), workspace context, role-aware actions
- [x] Command center: KPI cards with comparison, trend with comparison overlay, category mix, top products, insights
- [x] Sales explorer: filters, drivers waterfall, contribution tables, drill-through transactions
- [x] Loading, empty, error states; responsive tables; keyboard and screen-reader labels

**Exit: met.** Values match hand-computed answers on a fixture; drivers, trend, category, channel and region sums reconcile to net sales on the 8,188-row sample (28 analytics tests).

**Known limits:** returns are excluded (no `returns` table yet, decision D6); customer metrics ignore walk-in orders; `/app` ships Recharts (276 kB first load); changing a workspace timezone does not yet recompute business dates.

## Phase 3 — Customer & product intelligence ✅

- [x] Customer activity + RFM features; interpretable segment rules (8 named segments, tie-fair percentile scoring)
- [x] New / repeat / lapsed definitions; cohort retention by first-order month
- [x] Product & category contribution, margin and discount analysis; ABC classes; portfolio quadrants
- [x] Basket pair analysis (support, confidence, lift)
- [x] CSV export of customers and products
- [x] `/app/customers` and `/app/products` pages

**Exit: met.** Scores, segments, cohort counts, margins, ABC and basket statistics match hand-computed fixtures; on the 8,188-row sample segments, statuses, the R×F grid, cohorts, product and category sums all reconcile (170 tests).

## Phase 4 — Forecasting & the ML platform ⬜

Full plan and justification: [research/PHASE-4-ML-PLAN.md](research/PHASE-4-ML-PLAN.md). Catalogue: [MODELS.md](MODELS.md).

**4a · Foundations** (2 d) — ✅ metrics, baselines, backtester, demand classes (12 tests); synthetic 730-day dataset and a 21-model benchmark done ([results](research/PHASE-4-BENCHMARK.md)); product modelling panel moves to 4b
- [ ] Generator `--days 730` mode with a known weekly cycle, trend, month-end and festive effects, promotions, stock-outs, intermittent SKUs
- [ ] Modelling panel (SKU × day, zero-filled, stock-out suspicion flags) and demand-pattern classification (ADI/CV²)
- [ ] Metrics module (MAE, RMSE, WAPE, sMAPE, MASE, bias, pinball, coverage, forecast value added), unit-tested on known series
- [ ] Rolling-origin backtester with a single-use holdout; baselines (naive, seasonal naive, moving average, drift)

**4b · Statistical and intermittent models** (2–3 d)
- [ ] AutoETS, AutoARIMA, Theta, MSTL, Holt-Winters (statsforecast)
- [ ] Croston, Croston-SBA, TSB, ADIDA/IMAPA for sparse demand
- [ ] Per-series model selection from backtest error; leaderboard report

**4c · Global machine-learning models** (2–3 d)
- [ ] Feature builder (lags, rolling stats, calendar, festive-season table, price/discount, category context), leak-free
- [ ] LightGBM recursive and direct, ridge on lags, random forest reference
- [ ] LightGBM quantile models (p10/p50/p90)

**4d · Tuning, ensembles, intervals** (3 d)
- [ ] Optuna (TPE + median pruning) inside rolling-origin folds, seeded, configurable trial budget, every trial logged
- [ ] Mean/median, weighted and stacked ensembles
- [ ] Split-conformal intervals with measured coverage
- [ ] Holdout evaluation and the **ship gate** (must beat seasonal naive)
- [ ] Optional: Prophet and N-HiTS as candidates (kept only if they win)

**4e · Registry, API and UI** (3 d)
- [ ] Tables: `model_runs`, `model_versions`, `forecasts`; model card generation
- [ ] `forecast_training` background job with progress by fold and trial; `POST /forecasts`, `GET /forecasts/{id}`, `GET /models`
- [ ] Forecast UI: horizon picker (7/14/30), interval band, leaderboard, per-series model, low-confidence flags, model card view
- [ ] Anomaly detection on daily sales and a demand-pattern view

**Exit:** a reproducible tuned run with a model card; the shipped model beats seasonal naive on the holdout (or the product shows the baseline); interval coverage near nominal; forecast visible in the app.

## Phase F2 — App shell hardening

- [ ] HttpOnly, SameSite cookie session with refresh-token rotation; CSRF protection; logout everywhere
- [ ] Typed API client generated from OpenAPI (`openapi-typescript`) replacing the hand-written types
- [ ] Workspace switcher and member invites (owner/admin)
- [ ] Remove the persona demo once real data is the default (decision F-C)
- [ ] Consistent empty / loading / error states; mobile layouts for every table
- [ ] Accessibility pass (keyboard, focus, screen-reader labels, contrast) and Lighthouse check

## Phase 5 — Inventory & decision support

- [ ] Stock-on-hand, lead time, MOQ import; reorder point = demand over lead time + safety stock
- [ ] Fast/slow movers, stock-out risk, excess stock; scenario sliders
- [ ] Draft purchase orders only — a human must approve

## Phase 6 — NLP review intelligence

- [ ] Review schema + normalisation; language detection (English / Hindi / Hinglish)
- [ ] TF-IDF + logistic regression baseline vs a multilingual transformer; macro-F1 reported
- [ ] Aspect themes (delivery, quality, price, packaging, support) with evidence snippets

## Phase 7 — Document intelligence & RAG

- [ ] PDF/DOCX/TXT ingestion with page/section metadata
- [ ] Versioned Sentence-Transformers embeddings + FAISS; permission filter *before* retrieval
- [ ] Citations to document/page/section; abstain when evidence is insufficient
- [ ] Evaluation set: Recall@K, MRR, citation correctness; prompt-injection test documents

## Phase 8 — Vyapar Copilot

- [ ] Intent routing: metric, comparison, forecast, customer, inventory, document, unsupported
- [ ] Typed tools (`get_sales_summary`, `compare_periods`, `top_products`, `forecast_demand`, `search_documents`)
- [ ] Numbers only from the metric layer — the LLM never does arithmetic
- [ ] Streaming UI with tool activity + evidence panel; fixed evaluation question set

## Phase 9 — Agent workflows

- [ ] LangGraph analyst workflow: plan → call approved tools → inspect → summarise
- [ ] Typed state, bounded retries, timeouts, full run trace
- [ ] No arbitrary SQL, secrets, permission changes or purchases

## Phase 10 — Recommendations & reporting

- [ ] Recommendation objects: rationale, evidence refs, impact range, confidence, assumptions
- [ ] Status lifecycle: proposed → approved/dismissed → completed → outcome-measured
- [ ] PDF/CSV reports with metric definitions; saved analyses

## Phase 11 — Hardening, deployment & launch

- [ ] Rate limits, upload fuzzing, SQL-safety and prompt-injection tests, dependency audit
- [ ] PostgreSQL deploy, migrations on release, backups, runbook
- [ ] Architecture diagrams, model cards, demo video, interview walkthrough

---

## Definition of done

A change is done when it is **implemented, tested, documented and demonstrable**:

- **Functional** — success, empty, partial, invalid and failure states handled.
- **Data** — metric definitions, lineage and reconciliation checks exist.
- **AI** — baseline + evaluation set; limitations and failure behaviour documented.
- **Security** — authorization, input validation and audit behaviour tested.
- **UX** — responsive, accessible focus, loading feedback, reduced-motion support.
- **Docs** — setup, configuration, assumptions and known limitations are current.
