# Roadmap & status

_Last updated: 2026-11-07_

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ blocked / decision needed

Detailed scope and checklists for each phase live in [PHASES.md](PHASES.md).

## At a glance

| Phase | Status | Notes |
|---|---|---|
| 0 · Foundation & discovery | ✅ code · ⏸ decisions | Backend skeleton, auth, tenancy, migrations, CI done. Dataset + naming decisions open. |
| F1 · Marketing site: landing page ✅ · cinematic opening 🟡 (interim, photoreal pending) | 🟡 | 3D shatter hero, scroll story, persona login, demo dashboard, responsive (phone/tablet/desktop). Real-API login pending. |
| 1 · Data ingestion & quality | ⬜ | **Next up.** |
| 2 · Metric layer & sales analytics | ⬜ | |
| 3 · Customer & product intelligence | ⬜ | |
| 4 · Forecasting | ⬜ | |
| F2 · App shell on real APIs | ⬜ | |
| 5 · Inventory & decisions | ⬜ | P1 |
| 6 · NLP reviews | ⬜ | P1 |
| 7 · RAG | ⬜ | P1 |
| 8 · Copilot | ⬜ | P1 |
| 9 · Agents | ⬜ | P1 |
| 10 · Recommendations & reports | ⬜ | P2 |
| 11 · Hardening & launch | ⬜ | |

## Done

### Backend (`apps/api`)
- FastAPI app factory, `/api/v1` versioning, OpenAPI at `/docs`
- Typed settings with production guards (refuses dev JWT secret or SQLite in production)
- Models: `users`, `workspaces`, `memberships`, `datasets`, `jobs`, `audit_logs`,
  `products`, `customers`, `orders`, `order_items` — UUID keys, `workspace_id` on tenant tables
- Alembic initial migration; test ensures models ↔ migrations never drift
- Auth: register, login (OAuth2 password form → JWT), `me`
- Workspaces: create, list, get, update, members list/add, audit-log listing
- Datasets/jobs read endpoints (workspace-scoped) ready for Phase 1
- Request-ID middleware, JSON logs, single error envelope, liveness/readiness probes
- Test suite: health, auth, tenancy isolation, RBAC, security, migrations

### Frontend (`apps/web`)
- Next.js + TypeScript + Tailwind with central design tokens
- Landing page: shattering-word 3D hero (React Three Fiber), Lenis smooth scroll,
  GSAP ScrollTrigger pinned story, zoom-through product reveal, bento features
- Persona sign-in page → demo session → persona-aware dashboard
- Responsive at 375 px / 768 px / desktop: stacked hero word on portrait screens, static-to-particle
  cross-fade, vertical story on phones, 1/2/6-column bento, mobile app nav, stacked product list
- Landing first-load JS cut from 401 kB to 169 kB by lazy-loading three.js

### Repo & docs
- README, PHASES, ROADMAP, ARCHITECTURE, RESEARCH, METRICS, DATA_DICTIONARY, API,
  THREAT_MODEL, DESIGN_SYSTEM, ADRs, CONTRIBUTING, CHANGELOG, DEVLOG
- GitHub Actions CI; issue & PR templates

## Left to do (next 3 up)

1. **Phase 1 – ingestion:** upload endpoint, inspection, column mapping, validation report,
   transactional import, job progress. Demo data generator.
2. **Phase 2 – metric layer:** metric registry + sales analytics endpoints with fixture tests.
3. **Phase F2:** connect the dashboard to real metrics; upload wizard UI.

## Open decisions (need owner input)

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Starter dataset | UCI Online Retail II · Olist · synthetic only | Synthetic (known answers) + Online Retail II (CC BY 4.0) |
| D2 | Product name | Keep "Vyapar AI" · rename | Check trademark — "Vyapar" is an existing Indian billing app |
| D3 | LLM provider | Ollama local · hosted API · both | Provider-agnostic interface; Ollama for local dev |
| D4 | Background jobs | In-process worker · RQ/arq + Redis · Celery | DB-backed job table + in-process worker for MVP |
| D5 | Hosting | Render / Railway / Fly + Neon/Supabase Postgres; Vercel for web | Decide in Phase 11 |

## Known limitations

- SQLite is the default for local development; production requires PostgreSQL.
- Access tokens are bearer JWTs with no refresh/revocation yet (planned with the web cookie session).
- The web dashboard currently shows **demo data**, not API data.
