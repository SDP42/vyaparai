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
| **2** | **Metric layer & sales analytics** | 🟡 **in progress** | Versioned metric registry, comparisons, drivers, command center |
| 3 | Customer & product intelligence | ⬜ | RFM, cohorts, margin and discount analysis |
| 4 | Forecasting & ML platform | ⬜ | Many models (statistical, intermittent, LightGBM, ensembles), Optuna tuning, backtests, conformal intervals, registry, UI |
| F2 | App shell polish | ⬜ | Cookie sessions, generated API types, empty/error states |
| 5 | Inventory & decision support | ⬜ | Stock cover, reorder simulation (P1) |
| 6 | NLP review intelligence | ⬜ | Sentiment and themes, Hinglish (P1) |
| 7 | Document intelligence (RAG) | ⬜ | Cited answers over documents (P1) |
| 8 | Vyapar Copilot | ⬜ | Plain-language questions over the metric layer (P1) |
| 9 | Agent workflows | ⬜ | Bounded, traced, read-only investigations (P1) |
| 10 | Recommendations & reports | ⬜ | Approvable actions, PDF/CSV reports (P2) |
| 11 | Hardening, deployment, launch | ⬜ | Rate limits, Postgres deploy, runbook, demo video |

**MVP boundary:** phases 0–4 + F2 (upload → trusted metrics → forecast in a usable app).
Phases 5–10 are P1/P2 and follow the MVP.

## 2. What is done

### Backend (`apps/api`): 54 tests, strict mypy, ruff clean
- FastAPI app factory, `/api/v1`, uniform error envelope, request IDs, JSON logs, health probes
- Auth (Argon2id + JWT), workspaces with owner/admin/analyst/viewer roles, audit log
- 404-on-non-member tenancy, tested; production settings guards
- Models for users, workspaces, memberships, datasets, jobs, audit logs, products, customers,
  orders, order items; Alembic migrations with a drift test
- **Ingestion:** CSV/XLSX upload (size, rows, encoding, signature checks), SHA-256 duplicate
  detection, header inspection and mapping suggestions, Indian-format parsing (₹, lakh commas,
  day-first dates), row validation with error CSV, idempotent transactional import job

### Frontend (`apps/web`)
- **Marketing:** scroll-driven key-and-lock opening (HDRI + PBR textures, depth of field, bloom,
  synced sound, hand-off), then the landing page (simple hero, story scroll, zoom reveal, features,
  principles, CTA); responsive; reduced-motion and no-WebGL fallbacks
- **App:** persona demo dashboard; real account sign-up/sign-in, workspace creation, 4-step import
  wizard, data summary and upload history

### Repo & docs
- README, ROADMAP, PHASES, ARCHITECTURE, API, DATA_DICTIONARY, METRICS, DESIGN_SYSTEM, THREAT_MODEL,
  RESEARCH, ADRs, CONTRIBUTING, CHANGELOG, DEVLOG; GitHub Actions CI; demo-data generator

## 3. What is left (everything, in order)

Effort is in focused working days for one developer and is an estimate, not a promise.

| Phase | Remaining work | Effort | Depends on |
|---|---|---|---|
| **2** | Metric registry · analytics queries · period comparison · price-volume-mix drivers · breakdowns · drill-through · filters · command-center UI · sales explorer UI · tests | 4–5 | Phase 1 |
| 3 | Customer activity and RFM features · segment rules · cohort retention · product/category margin and discount analysis · exports · UI | 4 | Phase 2 |
| 4 | **4a** data, metrics, backtester, baselines (2 d) · **4b** ETS/ARIMA/Theta + Croston/SBA/TSB (2–3 d) · **4c** features + LightGBM + quantiles (2–3 d) · **4d** Optuna tuning, ensembles, conformal intervals, ship gate (3 d) · **4e** registry, job, API, forecast UI (3 d). See [ML plan](research/PHASE-4-ML-PLAN.md) | 12–14 | Phase 2 |
| F2 | HttpOnly cookie + refresh tokens · CSRF · generated TypeScript API client · invite members UI · loading/empty/error states · accessibility pass | 3 | Phases 2–4 |
| 5 | Stock snapshots import · stock cover and reorder point · slow movers · scenario sliders · draft purchase orders needing approval | 4 | Phase 4 |
| 6 | Review import · normalisation · TF-IDF baseline vs multilingual transformer · aspect themes · review explorer | 4–5 | Phase 1 |
| 7 | PDF/DOCX/TXT ingestion · chunking · embeddings + FAISS · permission-filtered retrieval · citations · evaluation set | 5 | Phase 1 |
| 8 | Typed tools over the metric layer · intent router · streaming UI · evidence panel · evaluation questions | 4–5 | Phases 2, 4, 7 |
| 9 | LangGraph analyst workflow · bounded retries · trace storage and viewer | 3–4 | Phase 8 |
| 10 | Recommendation schema and ranking · approval states · PDF/CSV reports · saved analyses | 4 | Phases 2–9 |
| 11 | Rate limiting · upload fuzzing · dependency audit · Postgres deployment · backups · runbook · model cards · demo video | 5 | All |
| M | Recorded (not synthesized) opening audio · short-viewport polish · Lighthouse/accessibility pass | 1–2 | Decision F-A |

**Total remaining to MVP (phases 2, 3, 4, F2):** about 24–27 working days (forecasting grew from 5–6 to 12–14).
**Total remaining to full blueprint:** about 58 working days.

## 4. Next up (this session)

1. **Phase 2:** research ✅ → [docs/research/PHASE-2-RESEARCH.md](research/PHASE-2-RESEARCH.md);
   then backend metric layer and endpoints, then the command center and sales explorer.
2. After Phase 2: **Phase 4 (forecasting and the ML platform)**, which is the largest and riskiest phase, then Phase 3.
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
- Import progress jumps 10 → 100 because the import is one transaction.
- Opening audio is synthesized in the browser; the 3D opening needs a visible browser tab.
- Access tokens are 30-minute bearer JWTs in `localStorage`, with no refresh or revocation yet (F2).
- SQLite is the development default; production requires PostgreSQL.
- The persona dashboard shows illustrative data, not API data.
