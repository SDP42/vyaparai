<div align="center">

# ◆ Vyapar AI

**Business intelligence and decision support for Indian small and mid-sized retailers.**

Upload your sales, then see what happened, why it happened, what may happen next, and which action is worth approving.

[![CI](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml/badge.svg)](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![Status](https://img.shields.io/badge/status-Phase%200%20%2B%20F1-E9A426)

</div>

---

## Why

Small retailers have the data (billing exports, spreadsheets, stock lists) but not the time to
turn it into decisions. Vyapar AI converts that data into **trusted metrics**, **honest forecasts**,
**explanations** and **human-approved actions**. Every number traces back to a reproducible
calculation, and the AI never invents figures.

## What works today

| Area | Status |
|---|---|
| FastAPI backend: auth, workspaces (tenants), RBAC, audit log, health probes | ✅ |
| Commerce data model (products, customers, orders, line items), Alembic migrations | ✅ |
| 29 backend tests including tenant-isolation and migration-drift checks | ✅ |
| Landing page: 3D "VYAPAR → data core" shatter, scroll story, zoom reveal | ✅ |
| Persona sign-in → persona-aware demo dashboard | ✅ (demo data) |
| CSV/XLSX ingestion, metric layer, forecasting, RAG, Copilot | ⬜ see [roadmap](docs/ROADMAP.md) |

## Repository layout

```
vyaparai/
├── apps/
│   ├── api/          FastAPI modular monolith (routers → services → repositories → models)
│   └── web/          Next.js + TypeScript + Tailwind landing page and app
├── ml/               forecasting / churn / NLP pipelines           (Phase 4+)
├── rag/              document parsing, chunking, embeddings, FAISS  (Phase 7)
├── agents/           LangGraph workflows and typed tools            (Phase 9)
├── scripts/          demo-data generation and utilities
├── infra/            deployment notes and configs                   (Phase 11)
└── docs/             product, architecture, metrics, ADRs, roadmap
```

## Quick start

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# Backend: http://localhost:8000/docs
cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --port 8000
```

```bash
# Frontend: http://localhost:3000
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Or from the repo root, use `make api`, `make web`, `make test` and `make lint`.

## Documentation

| Doc | What's inside |
|---|---|
| [PHASES](docs/PHASES.md) | Every delivery phase, its scope and exit criteria |
| [ROADMAP](docs/ROADMAP.md) | Live status: what's done, what's next, open decisions |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | System design, layers, request flow, tenancy |
| [API](docs/API.md) | Endpoint reference and conventions |
| [DATA_DICTIONARY](docs/DATA_DICTIONARY.md) | Tables, columns and import format |
| [METRICS](docs/METRICS.md) | Canonical metric definitions |
| [DESIGN_SYSTEM](docs/DESIGN_SYSTEM.md) | Palette, type, motion and the landing-page concept |
| [THREAT_MODEL](docs/THREAT_MODEL.md) | Security risks and mitigations |
| [RESEARCH](docs/RESEARCH.md) | Blueprint gaps, India-specific features, datasets, tech choices |
| [ADRs](docs/adr/) | Architecture decision records |
| [DEVLOG](docs/DEVLOG.md) · [CHANGELOG](CHANGELOG.md) | Day-by-day progress and release notes |

## Engineering principles

1. **SQL metrics over LLM arithmetic.** One metric registry feeds the dashboards, the API and the Copilot.
2. **Workspace isolation from day one.** Every tenant-owned row has `workspace_id`, and access is enforced server-side.
3. **Human approval over autonomy.** Agents read and suggest; they never purchase, write or change permissions.
4. **Baselines before models.** A model ships only if it beats a naive baseline on a time-aware backtest.
5. **Modular monolith over microservices.** Small domain modules, one deployable unit.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit style (Conventional Commits) and the definition of done.
