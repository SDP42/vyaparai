<div align="center">

# ◆ Vyapar AI

**Business intelligence and decision support for Indian small and mid-sized retailers.**

Upload your sales, then see what happened, why it happened, what may happen next, and which action is worth approving.

[![CI](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml/badge.svg)](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![Status](https://img.shields.io/badge/status-Phase%202%20complete%20·%20Phase%204%20next-E9A426)

</div>

---

## Why

Small retailers have the data (billing exports, spreadsheets, stock lists) but not the time to
turn it into decisions. Vyapar AI converts that data into **trusted metrics**, **honest forecasts**,
**explanations** and **human-approved actions**. Every number traces back to a reproducible
calculation, and the AI never invents figures.

## Where the project is

| Area | Status |
|---|---|
| FastAPI backend: auth, workspaces (tenants), RBAC, audit log, health probes | ✅ |
| Data model: products, customers, orders, line items; Alembic migrations | ✅ |
| **Phase 1 · data ingestion**: upload CSV/XLSX → inspect → map columns → validate → import | ✅ |
| Marketing site: cinematic key-and-lock opening → landing page | ✅ (audio is synthesized; recorded audio pending) |
| Web app: account → workspace → import wizard → command center → sales explorer | ✅ |
| **Phase 2 · metric layer, sales analytics, command center, sales explorer** | ✅ |
| **Phase 4 · forecasting and ML platform** (many models, Optuna tuning, backtests, intervals): plan written | 📝 [ML plan](docs/research/PHASE-4-ML-PLAN.md) · [model catalogue](docs/MODELS.md) |
| **Phase 3 · customer and product intelligence**: RFM segments, cohorts, ABC, portfolio quadrants, basket pairs, CSV export | ✅ |
| Inventory, reviews, RAG, Copilot, agents, recommendations | ⬜ see the [roadmap](docs/ROADMAP.md) |

**Numbers:** 170 backend tests · strict mypy · ruff clean · 8,188-row sample imports with
reconciled counts (8,025 valid / 163 rejected).

## Repository layout

```
vyaparai/
├── apps/
│   ├── api/          FastAPI modular monolith (routers → services → repositories → models)
│   └── web/          Next.js + TypeScript + Tailwind: marketing site and the product app
├── data/sample/      Generated demo exports (clean and deliberately messy)
├── scripts/          demo-data generator and utilities
├── ml/               forecasting / churn / NLP pipelines           (Phase 4+)
├── rag/              document parsing, chunking, embeddings, FAISS  (Phase 7)
├── agents/           LangGraph workflows and typed tools            (Phase 9)
├── infra/            deployment notes and configs                   (Phase 11)
└── docs/             roadmap, phases, architecture, metrics, ADRs, research
```

## Quick start

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# 1. API: http://localhost:8000/docs
cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --port 8000
```

```bash
# 2. Web: http://localhost:3000   (in a second terminal)
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Or from the repo root: `make api`, `make web`, `make test`, `make lint`.

### Try it with sample data

1. Open http://localhost:3000, click through the opening (or **Skip intro**), then **Sign in**.
2. Choose **Use your own data → Create account**, then name your business.
3. Click **Import sales data → Try the sample file** and follow the 4-step wizard.

Regenerate the sample files with `python scripts/generate_demo_data.py`.

## Documentation

| Doc | What's inside |
|---|---|
| [ROADMAP](docs/ROADMAP.md) | **Start here.** What's done, what's next, what's left, open decisions |
| [PHASES](docs/PHASES.md) | Every delivery phase with checklists and exit criteria |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Layers, request flow, tenancy, frontend structure |
| [API](docs/API.md) | Endpoint reference and conventions |
| [DATA_DICTIONARY](docs/DATA_DICTIONARY.md) | Tables, columns and the import file format |
| [METRICS](docs/METRICS.md) | Canonical metric definitions (the single source of truth) |
| [DESIGN_SYSTEM](docs/DESIGN_SYSTEM.md) | Palette, type, motion, the opening and landing page |
| [THREAT_MODEL](docs/THREAT_MODEL.md) | Security risks and what is mitigated |
| [MODELS](docs/MODELS.md) | Model catalogue, evaluation scorecard and model-card template |
| [RESEARCH](docs/RESEARCH.md) · [Phase 2](docs/research/PHASE-2-RESEARCH.md) · [ML plan](docs/research/PHASE-4-ML-PLAN.md) | Gaps in the blueprint, India-specific features, method research |
| [ADRs](docs/adr/) | Architecture decision records |
| [DEVLOG](docs/DEVLOG.md) · [CHANGELOG](CHANGELOG.md) | Day-by-day progress and release notes |

## Engineering principles

1. **SQL metrics over LLM arithmetic.** One metric registry feeds the dashboards, the API and the Copilot.
2. **Workspace isolation from day one.** Every tenant-owned row has `workspace_id`; access is enforced server-side.
3. **Never silently accept bad data.** Every import row is validated; rejected rows are counted and downloadable.
4. **Human approval over autonomy.** Agents read and suggest; they never purchase, write or change permissions.
5. **Baselines before models.** A model ships only if it beats a naive baseline on a time-aware backtest.
6. **Modular monolith over microservices.** Small domain modules, one deployable unit.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, small focused commits, and the definition of done.
