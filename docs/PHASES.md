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
| 3B | Campaigns and retention automation ([plan](research/CAMPAIGNS-PLAN.md), [consent, sending and measuring](CAMPAIGN-RUNS.md)) | 9-10 | P1 | ✅ |
| 4 | Forecasting & predictive MVP | 7 | P0 | ✅ |
| F2 | App shell wired to real APIs | 2–7 | P0 | ✅ all items; real screen-reader test open |
| — | **MVP release (end-to-end journey works)** ([checklist](MVP.md)) | — | — | ✅ |
| 5 | Inventory & decision support | 8 | P1 | ✅ |
| 5B | Festivals, regions and cricket | - | P1 | ✅ |
| 6 | NLP review intelligence | 9 | P1 | ✅ |
| 7 | Document intelligence & RAG | 5 | P1 | ✅ |
| 8 | Vyapar Copilot (plain-language questions) ([notes](ASSISTANT.md)) | 4 | P1 | ✅ |
| 9 | Agent workflows (LangGraph) ([notes](AGENTS.md)) | 12 | P1 | ✅ |
| 10 | Recommendations & reporting ([notes](RECOMMENDATIONS.md)) | 13 | P2 | ✅ |
| 11 | Hardening, deployment, launch ([runbook](RUNBOOK.md)) | 14 | P0 | ✅ code, ⬜ rehearsal |
| 12 | Daily and weekly digest (email now; WhatsApp copy-paste; [notes](research/DIGEST.md)) | - | P1 | ✅ |
| 13 | Cash and credit (udhaar) intelligence ([notes](UDHAAR.md)) | - | P1 | ✅ |
| 14 | Alerts and anomalies (rules, lifecycle, sidebar badge, digest link; [notes](research/ALERTS.md)) | - | P1 | ✅ |
| 15 | Connectors and scheduled imports (remembered mappings, connected links, safe fetch, scheduled runner; [notes](research/CONNECTORS.md)) | - | P1 | ✅ |
| 15B | Cost history and margin-leak tracking (**done** from per-sale costs, with price suggestions; purchase-bill import **done**, see [BILLS](BILLS.md); [plan](research/COST-TRACKING.md)) | - | P1 | ✅ |
| 16 | Pricing and promotion advisor ([notes](PRICING.md)) | - | P2 | ✅ |
| 17 | Multi-store and staff ([notes](STORES.md)) | - | P2 | ✅ stores compared; ⬜ staff attribution |
| 18 | Mobile-first (PWA) and Hinglish/Hindi ([notes](MOBILE.md)) | - | P1 | ✅ app; 🟡 translation covers 4 areas |
| 19 | Benchmarks and goals ([notes](GOALS.md)) | - | P2 | ✅ goals; own-history benchmarks only, no peer data |

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
- [x] Benchmark data decided: synthetic only in the repo, a permissive public set only for outside runs ([ADR 0008](adr/0008-benchmark-data.md))
- [x] Command center and sales explorer designed directly in code during Phase 2 (no separate wireframes)
- [ ] Product name/trademark: **owner decision**, see [RESEARCH.md](RESEARCH.md#naming-risk). "Vyapar" is an existing Indian billing app; fine privately, check before going public

**Exit:** migrations run cleanly; protected-API tests prove tenant boundaries. ✅

## Phase M — Marketing site: cinematic opening + landing page

Driven by the two-page master prompt; detailed plan in [frontend/PHASE-1-REPORT.md](frontend/PHASE-1-REPORT.md).

- [x] Phase 1: repository inspection and visual direction report
- [x] Landing page in the yellow "Bahi-Khata" design (owner's choice): simple hero, story scroll,
      zoom reveal, features, principles, CTA
- [x] One token source; Bricolage + Instrument Serif typography
- [x] Responsive at desktop, tablet and mobile; reduced-motion paths; production build passes
- [x] Opening (replaced 2026-11-11): the shop is closed under a woven cloth tied with a satin ribbon and bow; drag the scissors to the dotted line (or tap them, or press Enter) and the ribbon is snipped, the bow and tag fall and the cloth drops from the middle outward, then the page scrolls. Drawn in code, once per visit, Esc/Skip, none under reduced motion. (The earlier 3D key-and-lock scene was removed.)
- [x] Religious motifs removed
- [x] Hero text waits for the cloth to drop, then animates in
- [x] Opening checked at a short landscape phone size (700x360), a phone and a laptop: caption and cut line no longer collide; the cut, the cloth drop, the unlocked scroll and the hero entrance were walked through by hand. An automated visitor-journey test (Playwright) is not written

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

## Phase 4 — Forecasting & the ML platform ✅

Full plan: [research/PHASE-4-ML-PLAN.md](research/PHASE-4-ML-PLAN.md). Benchmark and choices: [research/PHASE-4-BENCHMARK.md](research/PHASE-4-BENCHMARK.md), [research/PHASE-4-DECISIONS.md](research/PHASE-4-DECISIONS.md). Catalogue: [MODELS.md](MODELS.md).

**4a · Foundations** ✅
- [x] 730-day synthetic dataset with known weekly, yearly and festive structure, promotions, stock-outs and intermittent products
- [x] Modelling panel (product × day, zero-filled, stock-out suspicion) and demand-pattern classes (ADI/CV²)
- [x] Metrics (MAE, RMSE, WAPE, sMAPE, MASE, bias, pinball, coverage, forecast value added) tested on known series
- [x] Rolling-origin backtester with a single-use holdout; baselines

**4b · Statistical and intermittent models** ✅ (benchmarked; Theta shipped)
- [x] AutoETS, AutoARIMA, Theta, MSTL, Croston, SBA, TSB, ADIDA, IMAPA all benchmarked on the same windows
- [x] **Theta** (weekday-adjusted level plus half the trend) built into the product as a dependency-free candidate
- [x] Per-series model choice from backtest error; per-shop method comparison shown in the app
- Decision: ETS, ARIMA and the Croston family are not shipped. The benchmark showed no gain over Theta and the average, and statsforecast needs heavy dependencies (see decisions doc)

**4c · Global machine-learning models** ✅
- [x] Leak-free feature builder (lags, rolling stats, calendar, festive table, discount, optional weather)
- [x] LightGBM direct multi-horizon model; intervals by conformal calibration instead of quantile models (measured coverage about 80 %)

**4d · Tuning, ensembles, intervals, ship gate** ✅
- [x] Hyperparameter search (random search, seeded) inside the training period only, defaults as trial 0, used only if it improves by 1 %; optional per run; every trial counted and reported
- [x] Conformal intervals with measured leave-one-window-out coverage, widened until coverage reaches 80 %
- [x] **Ship gate:** a new version that fails to beat "repeat last week" while the active one passed is kept as *not used*
- [x] Festive-peak handling: warning plus an owner-set uplift, labelled as the owner's assumption
- Decision: no ensembles (they did not beat LightGBM in the benchmark); Optuna replaced by dependency-free random search; Prophet and N-HiTS not added

**4e · Registry, API and UI** ✅
- [x] Versioned runs per workspace with status (in use, older, not used), notes, options and accuracy; rollback to any version; migration backfills history
- [x] Background job with progress; `POST /forecasts/run` (options `tune`, `peak_uplift_pct`), `GET /forecasts/runs`, `POST /forecasts/runs/{id}/activate`
- [x] Scheduled rebuild: `python -m app.forecast_runner` refreshes workspaces whose sales moved past the active forecast, at most every 20 hours, keeping the owner's festive adjustment
- [x] Forecast UI: fan chart, per-product table with ranges and confidence, trust panel with method comparison, version history with rollback, run options, product drawer, CSV
- Not built: pretrained model (Chronos) in the product; see decisions

**Exit: met.** A reproducible run with a model card, accuracy and coverage; shipped models beat repeating last week (28 % on the benchmark data, with the gate enforced); intervals near nominal coverage; forecasts visible in the app. 268 backend tests.

## Phase F2 — App shell hardening

- [x] HttpOnly, SameSite cookie session with refresh-token rotation; CSRF protection; logout everywhere
- [x] Types generated from the API's OpenAPI description (`make gen-api`; `apps/api/openapi.json` is checked by a test so it cannot go stale). Shared shapes (workspace, jobs, data summary) now come from it; older page-specific types are replaced as pages are touched
- [x] Workspace switcher and member invites (owner/admin)
- [x] Remove the persona demo: the sign-in page now signs in as real sample accounts (Phase 20)
- [x] Every data page has loading, empty and error states from the shared parts (the Data page was the last without them); wide tables scroll inside their own box on phones and no page scrolls sideways (checked at 390 px)
- [x] Accessibility audit of the landing, sign-in and all 23 app pages with fixes ([ACCESSIBILITY](ACCESSIBILITY.md)); a real screen-reader test and Lighthouse run are still to do

## Phase 5 — Inventory & decision support ✅ ([notes](research/INVENTORY.md))

- [x] Stock counts by CSV or by hand (dated snapshots), delivery time and pack size per product; stock today = last count minus sales since
- [x] Days of cover from the forecast, order now / order soon / too much / not selling, order quantity at a lean, balanced or cautious level, whole packs
- [x] Cash tied up, excess cash and dead stock; downloadable order list (a suggestion a human approves; nothing is ordered automatically)
- [x] Alerts for stock-out risk, products to order, dead stock; the digest's "Do this" picks up a stock-out
- Not built: orders already on the way, supplier minimum order values, per-supplier lead times, scenario sliders (the three safety levels are the first step)

## Phase 5B — Festivals, regions and cricket ✅ ([how it works](EVENTS.md))

- [x] Agent-researched, cross-checked table of 320 events 2024-2028 with sources and confidence
- [x] Region matching (core and zone), a state setting, multi-zone states
- [x] Festivals page: upcoming events by region, matching products, stock risk, past effects measured on the shop's own sales
- [x] Forecast: event and cricket signals tested as a group, festival distance feature, warnings that name the festival, owner festive boost
- [x] Alerts for festivals about to start whose products may run out

## Phase 6 — NLP review intelligence ✅ ([how it works](REVIEWS.md), [research](research/REVIEWS-NLP.md))

- [x] Review import (CSV, header synonyms, dedupe by content), language detection (English / Hindi / Hinglish)
- [x] Sentiment from our own word lists with negation, intensifiers and "but" handling; a per-shop model learned from star ratings (numpy, no downloads) used only when it beats guessing on held-out reviews
- [x] Seven themes (delivery, quality, price, packaging, service, freshness, availability) with the phrase each came from
- [x] Reviews page, per-product view, try-it box, alert when a complaint theme is common and rising
- Changed from plan: no multilingual transformer (CPU-only, free-only, and no permissively licensed Hinglish training data was found); accuracy is reported honestly on small self-written sets

## Phase 7 — Document intelligence & RAG ✅ ([how it works](DOCUMENTS.md))

- [x] PDF/DOCX/TXT/Markdown ingestion with page and heading metadata (scanned PDFs are refused with a message)
- [x] Multilingual embeddings (fastembed, MiniLM) stored with each passage, fused with BM25; permission filter *before* scoring. Changed from plan: no FAISS, since a shop's passages fit in memory (index capped at 20,000)
- [x] Citations to document, page and section; "none" returns nothing and "possible" is labelled (refusal is imperfect, see DOCUMENTS.md)
- [x] Evaluation set: Recall@3 and MRR on 57 labelled questions plus 6 out-of-scope; a prompt-injection document test. Small and self-written: optimistic

## Phase 8 — Vyapar Copilot ✅ ([how it works](ASSISTANT.md))

- [x] Intent routing (23 intents incl. documents and unsupported) in three languages; 79-question set, a development set
- [x] Typed read-only tools over the existing services (sales, drivers, top products, stock, forecast, document search and more; names differ from the plan)
- [x] Numbers only from the metric layer; there is no language model in the loop at all
- [x] Streaming steps and an evidence list on every answer; fixed question set in `tests/test_assistant.py`

## Phase 9 — Agent workflows

- [x] LangGraph analyst workflows: four built (`investigate_sales`, `weekly_review`, `customer_health`, `stock_risk`). The graph is fixed (scope, compare, drivers, checks, conclude), not planned by a model
- [x] Typed state, bounded retries (one retry), step budget, full run trace stored and viewable
- [x] Timeouts: 20 s total budget and a per-step slow flag (8 s). A running step cannot be interrupted safely (shared database session); production adds a database statement timeout (Phase 11)
- [x] No arbitrary SQL, secrets, permission changes or purchases (read-only; a test enforces it)

## Phase 10 — Recommendations & reporting

- [x] Recommendation objects: rationale, evidence refs, impact range, confidence, assumptions
- [x] Status lifecycle: proposed → approved/dismissed → done (audited)
- [x] Outcome measured: a baseline number is saved when an item is marked done and read again after 14 days (improved, no change, worse, or not measurable), with the caveat that this is not proof of cause
- [x] PDF/CSV reports; saved reports (snapshots) and saved investigation runs
- [x] Metric definitions printed inside the PDF

## Phase 11 — Hardening, deployment & launch

- [x] Rate limits (per address, shared via Redis), hostile-upload and injection-string tests, ORM-only queries; dependency audit run 2026-11-11: `pip-audit` finds no known vulnerabilities in the production Python set; `npm audit` reports PostCSS inside Next 15 (build-time only, accepted until Next 16)
- [x] PostgreSQL settings and guards, migrations on release, backup and restore scripts, runbook, Docker stack. **Not yet rehearsed on a real server** (see RUNBOOK)
- [x] Architecture diagram ([ARCHITECTURE](ARCHITECTURE.md)) and model cards ([MODELS](MODELS.md))
- [ ] Demo video and interview walkthrough (people-made, not code)

---

## Phase 20 — Personas and voice ✅ first version ([personas](PERSONAS.md), [voice](VOICE.md), [research](research/PERSONAS-VOICE.md))
- [x] Five personas stored on membership and invitation, validated against the role, chosen on the Team page
- [x] Assistant answers only the persona's questions, in the asker's language; every intent is classified for every persona (tested)
- [x] Sensitive routes guarded by capability; navigation and redirects follow the persona; `GET /workspaces/{id}/me`
- [x] One-tap sample sign-ins as real persona accounts (development only); the old static demo dashboard removed
- [x] Voice: faster-whisper + Whisper medium on the server, audio never stored, silence and hallucination guards, confirm-the-words step, read-aloud with the device voice
- [x] Speech-tolerant Hindi keyword matching
- [x] Spoken-number parsing (Hindi, Hinglish, English; lakh/crore/डेढ़/सवा/साढ़े) and product-name matching from Hindi speech (glossary + sound classes, "did you mean")
- [x] Staff attribution: optional Cashier/Staff column on import, sales by person (bills, average bill, items per bill, discount, margin), counter staff see only their own, linked by name on the Team page
- [ ] Test with real shopkeepers and recorded shop audio; Marathi/Gujarati/Tamil/Bengali speech (needs IndicWhisper or similar, see VOICE.md)
- [x] Per-field masking of cost and margin for personas without the margin capability; customer routes need the customers capability
- [ ] Confirm persona definitions with real shop owners

## Phase 21 — Daily routines and automation agents ✅ first version ([daily](DAILY.md), [agents](AGENTS.md), [research](research/DAILY-USE-FEATURES.md))
- [x] Today page: last day's sales, udhaar to call, orders, expiry, galla status, urgent alerts; one-line udhaar and expense entry read back before saving (Hinglish and Hindi)
- [x] Galla: day-end cash count with expected against counted, typed sales against the file, rough day profit; expenses by category and payment mode
- [x] Expiry watch list; supplier order lists to copy or share
- [x] Six automation agents (morning brief, reorder planner, udhaar collector, day-end check, expiry clearance, price watch) that run on demand or on a daily schedule, read-only, with drafts for a person to send
- [ ] Payment mode on udhaar entries (the galla assumes cash); batches read from bills into the expiry list
- [ ] Test the routines with real shopkeepers

## Definition of done

A change is done when it is **implemented, tested, documented and demonstrable**:

- **Functional** — success, empty, partial, invalid and failure states handled.
- **Data** — metric definitions, lineage and reconciliation checks exist.
- **AI** — baseline + evaluation set; limitations and failure behaviour documented.
- **Security** — authorization, input validation and audit behaviour tested.
- **UX** — responsive, accessible focus, loading feedback, reduced-motion support.
- **Docs** — setup, configuration, assumptions and known limitations are current.
