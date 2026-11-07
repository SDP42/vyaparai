# Delivery phases

Vyapar AI is built in small, demonstrable phases. Each phase ends with a working vertical
slice, tests and updated docs. A phase is **done** only when it meets the
[definition of done](#definition-of-done) — a polished screen backed by mocked data is not a
finished feature.

Live status (✅ / 🟡 / ⬜) is tracked in [ROADMAP.md](ROADMAP.md). This file describes *what*
each phase contains and its exit criteria.

| Phase | Name | Blueprint weeks | Priority |
|---|---|---|---|
| 0 | Foundation & discovery | 1, 3 | P0 |
| F1 | Frontend: brand, landing page & persona auth | 2 | P0 |
| 1 | Data ingestion & quality | 4 | P0 |
| 2 | Metric layer & sales analytics (command center) | 5 | P0 |
| 3 | Customer & product intelligence | 6 | P0 |
| 4 | Forecasting & predictive MVP | 7 | P0 |
| F2 | Frontend: app shell wired to real APIs | 2–7 | P0 |
| — | **MVP release (end-to-end journey works)** | — | — |
| 5 | Inventory & decision support | 8 | P1 |
| 6 | NLP review intelligence | 9 | P1 |
| 7 | Document intelligence & RAG | 10 | P1 |
| 8 | Vyapar Copilot & safe tool use | 11 | P1 |
| 9 | Agent workflows (LangGraph) | 12 | P1 |
| 10 | Recommendations & reporting | 13 | P2 |
| 11 | Hardening, deployment & launch | 14–16 | P0 for launch |

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
- [ ] Confirm starter dataset + licence (see [RESEARCH.md](RESEARCH.md#starter-datasets))
- [ ] Low-fidelity wireframes for onboarding, dashboard, sales detail
- [ ] Decide product name/trademark question (see [RESEARCH.md](RESEARCH.md#naming-risk))

**Exit:** migrations run cleanly; protected-API tests prove tenant boundaries. ✅

## Phase F1 — Marketing site: cinematic opening + landing page

Driven by the two-page master prompt; detailed plan in [frontend/PHASE-1-REPORT.md](frontend/PHASE-1-REPORT.md).

- [x] Phase 1: repository inspection and visual direction report
- [x] Landing page in the yellow "Bahi-Khata" design (owner's choice): simple hero, story scroll,
      zoom reveal, features, principles, CTA
- [x] One token source; Bricolage + Instrument Serif typography
- [x] Responsive at desktop, tablet and mobile; reduced-motion paths; production build passes
- [x] Key-and-lock opening with HDRI + CC0 PBR textures, slatted shutter, brass padlock, cut key, sound, skip
- [x] Religious motifs removed
- [ ] Realism polish: depth of field, bloom, detailed interior goods
- [ ] Scroll-scrubbed, reversible unlock (0–20–45–60–75–100 %)
- [ ] Realistic recorded audio, shop interior, ambience
- [ ] Shop → Vyapar.ai digital transition
- [ ] Short-viewport polish for pinned sections; full visitor-journey test

## Phase 1 — Data ingestion & quality

- [ ] `POST /workspaces/{id}/datasets` upload (CSV/XLSX), size/row/encoding limits, signature check
- [ ] SHA-256 file hash → duplicate detection per workspace
- [ ] Inspection: headers, sample rows, inferred types, date formats, missingness
- [ ] Column mapping (order date, product, quantity, price, customer, status) with suggestions
- [ ] Row-level validation; accepted/rejected counts; downloadable error CSV
- [ ] Staging → transactional normalisation into products/customers/orders/order_items
- [ ] Background job runner with progress on `GET /jobs/{id}`
- [ ] Synthetic demo dataset generator with known answers (`scripts/generate_demo_data.py`)

**Exit:** the sample file imports reproducibly; rejected rows + counts reconcile.

## Phase 2 — Metric layer & sales analytics

- [ ] Metric registry (single source of truth, see [METRICS.md](METRICS.md)) with versioned definitions
- [ ] Net sales, gross profit, margin, orders, AOV, units, discount rate — unit-tested on fixtures
- [ ] Date range, comparison period, filters (region, channel, category, segment)
- [ ] Trend, category mix, top/bottom products, driver analysis (volume / price / mix / discount)
- [ ] Drill-through to transactions; data-freshness labels on every response

**Exit:** dashboard values match independent SQL checks on the fixture dataset.

## Phase 3 — Customer & product intelligence

- [ ] Customer activity + RFM features; interpretable segment rules
- [ ] New / repeat / lapsed definitions; cohort retention summary
- [ ] Product & category contribution, margin and discount analysis
- [ ] CSV export of segments and product tables

## Phase 4 — Forecasting & predictive MVP

- [ ] Naive, seasonal-naive and moving-average baselines
- [ ] Rolling-origin backtests; MAE, RMSE, WAPE vs baseline
- [ ] One candidate model (statsforecast ETS/AutoARIMA or LightGBM) must beat baseline to ship
- [ ] Festival calendar features (Diwali, Navratri, Eid, wedding season) — see RESEARCH.md
- [ ] Model metadata + forecast API (7/14/30-day horizons) with intervals and low-confidence flags

## Phase F2 — App shell wired to real APIs

- [ ] Typed API client generated from OpenAPI (`openapi-typescript`)
- [ ] Workspace switcher, onboarding/upload wizard, command center, sales & forecast pages
- [ ] Empty / loading / error states; responsive tables → stacked summaries on mobile

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
