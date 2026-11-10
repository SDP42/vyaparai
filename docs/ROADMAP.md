# Roadmap & status

_Last updated: 2026-11-08_

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ blocked / needs a decision

Checklists and exit criteria for every phase: [PHASES.md](PHASES.md).

## 1. Status at a glance

| # | Phase | Status | What it delivers |
|---|---|---|---|
| 0 | Foundation & discovery | ✅ | API skeleton, auth, workspaces/RBAC, audit log, migrations, CI |
| M | Marketing site (opening + landing) | ✅ | Key-and-lock opening, scroll-driven unlock, landing page |
| 1 | Data ingestion & quality | ✅ | Upload → inspect → map → validate → import; wizard UI |
| 2 | Metric layer & sales analytics | ✅ | Versioned metric registry, comparisons, price-volume-mix drivers, command center, sales explorer |
| 3 | Customer & product intelligence | ✅ | RFM, cohorts, margin and discount analysis, ABC, portfolio quadrants, basket pairs |
| **4** | **Forecasting & ML platform** | ✅ | Many models (statistical, intermittent, LightGBM, ensembles), Optuna tuning, backtests, conformal intervals, registry, UI |
| 3B | Campaigns and retention automation | ✅ | Consent and opt-outs, a person-sent outbox, holdout-measured uplift with intervals ([CAMPAIGN-RUNS](CAMPAIGN-RUNS.md)) |
| F2 | App shell polish | 🟡 | Cookie sessions and team invites done; generated API types and accessibility pass open |
| 5 | Inventory & decision support | ✅ | Stock cover, order advice, dead stock, cash tied up |
| 5B | Festivals, regions and cricket | ✅ | 320 dated events, region matching, forecast signals, alerts, Festivals page |
| 6 | NLP review intelligence | ✅ | Sentiment and themes in English, Hindi and Hinglish, with evidence |
| 7 | Document intelligence (RAG) | ✅ | Multilingual search over your own documents with citations ([DOCUMENTS](DOCUMENTS.md)) |
| 8 | Vyapar Copilot | ✅ | Ask page: English, Hindi, Hinglish; follow-ups, product questions, evidence panel, streamed steps ([ASSISTANT](ASSISTANT.md)) |
| 9 | Agent workflows | ✅ | Bounded, traced, read-only LangGraph investigations ([AGENTS](AGENTS.md)) |
| 10 | Recommendations & reports | ✅ | Ranked actions with impact ranges and approvals; PDF/CSV reports ([RECOMMENDATIONS](RECOMMENDATIONS.md)) |
| 11 | Hardening, deployment, launch | ✅ code | Shared rate limits, security headers, size limits, PostgreSQL timeouts, Docker stack, backups, runbook; not yet rehearsed on a server ([RUNBOOK](RUNBOOK.md)) |
| 12 | Daily and weekly digest (push) | ✅ | Three numbers and one action, by WhatsApp or email |
| 13 | Cash and credit (udhaar) intelligence | ✅ | Dues by age, who to chase, drafted reminders in three languages ([UDHAAR](UDHAAR.md)) |
| 14 | Alerts and anomalies | ✅ | Sales drop, margin leak, stock-out risk |
| 15 | Connectors and scheduled imports | ✅ | Remembered column mappings, connected Google Sheet or shared-file links, scheduled and deduplicated |
| 15B | Cost history and margin-leak tracking | ✅ | Cost history from every sale, margin leaks with a suggested price; purchase-bill photo/PDF import done ([BILLS](BILLS.md), [plan](research/COST-TRACKING.md)) |
| 16 | Pricing and promotion advisor | ✅ | Which discounts paid off (vs the same weekday, profit after discount), small safe price trials ([PRICING](PRICING.md)) |
| 17 | Multi-store and staff | ✅ stores | Side-by-side comparison, needs-attention flags, add a shop; per-staff attribution not possible without a cashier column ([STORES](STORES.md)) |
| 18 | Mobile-first and Hinglish/Hindi | ⬜ | Installable PWA, language, offline read |
| 19 | Benchmarks and goals | ⬜ | Targets and peer ranges |

**MVP boundary:** phases 0–4 + F2 (upload → trusted metrics → forecast in a usable app).
Phases 5–10 are P1/P2 and follow the MVP.

## 2. What is done

### Backend (`apps/api`): 116 tests, strict mypy, ruff clean
- FastAPI app factory, `/api/v1`, uniform error envelope, request IDs, JSON logs, health probes
- Auth (Argon2id + JWT), workspaces with owner/admin/analyst/viewer roles, audit log
- 404-on-non-member tenancy, tested; production settings guards
- Models for users, workspaces, memberships, datasets, jobs, audit logs, products, customers,
  orders, order items; Alembic migrations with a drift test
- **Analytics (Phase 2):** versioned metric registry (16 metrics), period comparison (previous period or same weekdays last year), trend (gap-filled), category/channel/region mixes, top/bottom products, price-volume-mix drivers that sum exactly, contribution tables, drill-through to transactions, rule-based insights, coverage warnings; 61 new tests
- **Ingestion:** CSV/XLSX upload (size, rows, encoding, signature checks), SHA-256 duplicate
  detection, header inspection and mapping suggestions, Indian-format parsing (₹, lakh commas,
  day-first dates), row validation with error CSV, idempotent transactional import job

### Frontend (`apps/web`)
- **Marketing:** scroll-driven key-and-lock opening (HDRI + PBR textures, depth of field, bloom,
  synced sound, hand-off), then the landing page (simple hero, story scroll, zoom reveal, features,
  principles, CTA); responsive; reduced-motion and no-WebGL fallbacks
- **App:** real accounts get an app shell with a **Command center** (KPIs with comparison, trend, insights, mixes, top/bottom products, metric definitions on every KPI), a **Sales explorer** (drivers waterfall, contribution tables with drill-down, movers, filterable transactions) and a **Data** page (import wizard, upload history); the persona demo dashboard remains

### Repo & docs
- README, ROADMAP, PHASES, ARCHITECTURE, API, DATA_DICTIONARY, METRICS, DESIGN_SYSTEM, THREAT_MODEL,
  RESEARCH, ADRs, CONTRIBUTING, CHANGELOG, DEVLOG; GitHub Actions CI; demo-data generator

## 3. What is left (everything, in order)

Effort is in focused working days for one developer and is an estimate, not a promise.

| Phase | Remaining work | Effort | Depends on |
|---|---|---|---|
| 3B | Campaigns and retention automation | ✅ | Consent and opt-outs, a person-sent outbox, holdout-measured uplift with intervals ([CAMPAIGN-RUNS](CAMPAIGN-RUNS.md)) |
| 4 | **4a** data, metrics, backtester, baselines (2 d) · **4b** ETS/ARIMA/Theta + Croston/SBA/TSB (2–3 d) · **4c** features + LightGBM + quantiles (2–3 d) · **4d** Optuna tuning, ensembles, conformal intervals, ship gate (3 d) · **4e** registry, job, API, forecast UI (3 d). See [ML plan](research/PHASE-4-ML-PLAN.md) | 12–14 | Phase 2 |
| F2 | HttpOnly cookie + refresh tokens · CSRF · generated TypeScript API client · invite members UI · loading/empty/error states · accessibility pass | 3 | Phases 2–4 |
| 5 | Stock snapshots import · stock cover and reorder point · slow movers · scenario sliders · draft purchase orders needing approval | 4 | Phase 4 |
| 6 | Review import · normalisation · TF-IDF baseline vs multilingual transformer · aspect themes · review explorer | 4–5 | Phase 1 |
| 7 | PDF/DOCX/TXT ingestion · chunking · embeddings + FAISS · permission-filtered retrieval · citations · evaluation set | 5 | Phase 1 |
| 8 | Typed tools over the metric layer · intent router · streaming UI · evidence panel · evaluation questions | 4–5 | Phases 2, 4, 7 |
| 9 | LangGraph analyst workflow · bounded retries · trace storage and viewer | 3–4 | Phase 8 |
| 10 | Recommendation schema and ranking · approval states · PDF/CSV reports · saved analyses | 4 | Phases 2–9 |
| 11 | Hardening, deployment, launch | ✅ code | Shared rate limits, security headers, size limits, PostgreSQL timeouts, Docker stack, backups, runbook; not yet rehearsed on a server ([RUNBOOK](RUNBOOK.md)) |
| M | Recorded (not synthesized) opening audio · short-viewport polish · Lighthouse/accessibility pass | 1–2 | Decision F-A |

**Total remaining to MVP (phases 4, F2):** about 15–18 working days.
**Total remaining to full blueprint:** about 49 working days.

## 4. Next up (this session)

1. **Phases 2 and 3 are done** (research: [PHASE-2](research/PHASE-2-RESEARCH.md), [PHASE-3](research/PHASE-3-RESEARCH.md)).
2. **Next: Phase 4 (forecasting and the ML platform)**, starting with 4a (longer synthetic data, metrics, backtester, baselines), the largest and riskiest phase.
   The ML plan, tuning protocol and model catalogue are written: [ML plan](research/PHASE-4-ML-PLAN.md), [MODELS.md](MODELS.md).

## 5. Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| F-A | Opening audio | You download CC0 clips · I source Pixabay CC0 · keep synthesized | Recorded CC0 clips |
| F-C | Demo persona routes | Keep the persona demo dashboard · remove it once real data is in | Keep until Phase 2 ships, then remove |
| D1 | Starter dataset for tests and demos | Synthetic only · add UCI Online Retail II (CC BY 4.0) | Synthetic plus one public dataset for forecasting benchmarks |
| D2 | Product name | Keep "Vyapar AI" · rename | Check trademark: "Vyapar" is an existing billing app |
| D3 | LLM provider for the Copilot | Ollama local · hosted API · both behind an interface | Provider-agnostic interface; Ollama for local dev |
| D4 | Background jobs | Keep in-process tasks · RQ/arq + Redis | In-process until Phase 4 training needs a queue |
| D5 | Hosting | Render/Railway/Fly + Neon/Supabase; Vercel for web | Decide in Phase 11 |
| D7 | ML compute | Laptop CPU only · add a GPU/cloud worker later | CPU only; deep models stay optional |
| D6 | Returns handling | Add a `returns` table in Phase 3 · keep rejecting negative quantities | Add `returns` (net sales needs it) |

## 6. Known limitations

- Returns (negative quantities) are rejected at import; `returned` orders are excluded from net sales.
- A rejected line inside a multi-line order leaves the rest of that order imported.
- Changing a workspace timezone does not yet recompute stored business dates.
- `/app` ships Recharts (276 kB first load); lazy-loading charts is a Phase F2 item.
- Import progress jumps 10 → 100 because the import is one transaction.
- Opening audio is synthesized in the browser; the 3D opening needs a visible browser tab.
- Rate-limit counters are shared through Redis when `REDIS_URL` is set; without it they are per process.
- SQLite is the development default; production requires PostgreSQL.
- The persona dashboard shows illustrative data, not API data.
