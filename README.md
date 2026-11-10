<div align="center">

# ◆ Vyapar AI

**Decision support for Indian small and mid-sized retailers.**
Bring your sales in, see what happened and why, what is likely next, and which action is worth taking.

[![CI](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml/badge.svg)](https://github.com/SDP42/vyaparai/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![Tests](https://img.shields.io/badge/backend%20tests-400%2B-2E7D32)
![Status](https://img.shields.io/badge/status-MVP%20journey%20complete-E9A426)

</div>

---

## Overview

Small retailers already have the data: billing exports, spreadsheets, stock lists. What they lack is the time
to turn it into decisions. Vyapar AI converts that data into **trusted metrics**, **honest forecasts**,
**plain-language explanations** and **suggestions a person approves**. Every number traces back to a
reproducible calculation, and nothing in the product invents figures.

It is built for Indian retail: day-first dates and lakh formatting, festivals and regional calendars, Hindi and
Hinglish text, WhatsApp-style messages, and tools that run on a laptop for free.

## What it does today

| Area | Capabilities |
|---|---|
| **Data in** | CSV and Excel upload, header detection, remembered column mappings, row-level validation with a downloadable error file, idempotent import, connected Google Sheet or shared-file links with scheduled re-imports |
| **Trusted numbers** | One versioned metric registry; period comparisons; price-volume-mix drivers that sum exactly; drill-through to transactions |
| **Customers and products** | RFM segments, cohorts, ABC classes, margin and discount analysis, portfolio quadrants, basket pairs |
| **Forecasting** | Statistical, intermittent-demand and gradient-boosted models; per-series model selection; honest rolling backtests; conformal prediction ranges; ship gate and rollback; festival, regional and weather signals tested before use |
| **Stock** | Days of cover from the forecast, order-now advice by safety level, dead stock, cash tied up, downloadable order list |
| **Margins** | Cost history from every sale, leaks where cost rose faster than price, with a suggested price |
| **Alerts and digest** | Fixed-rule alerts (sales drop, margin leak, stock-out risk, falling-away regulars, rising complaints); a daily or weekly three-numbers-and-one-action digest by email |
| **Campaigns** | Segment audiences, margin-guarded offers, message drafts, holdout design (nothing is sent automatically) |
| **Festivals** | 320 dated events with region matching, forecast signals and "stock before" warnings |
| **Reviews** | Import reviews; language, sentiment and themes for English, Hindi and Hinglish with the phrase behind each claim |
| **Teams and security** | Workspaces with owner, admin, analyst and viewer roles; invitation links; HttpOnly cookie sessions with rotation and reuse detection; throttled sign-in; audit log |

The end-to-end journey (sign up → import → numbers → forecast → alerts → digest → stock advice → invite a teammate)
is covered by an automated test: [`test_mvp_journey.py`](apps/api/tests/test_mvp_journey.py). See the
[MVP checklist](docs/MVP.md) for what is ready and what is not.

## Architecture

```
 Browser (Next.js, TypeScript, Tailwind)
        │  HTTPS · bearer access token (memory) · HttpOnly refresh cookie
        ▼
 FastAPI  /api/v1
   routers ─► services ─► repositories ─► SQLAlchemy models ─► SQLite (dev) / PostgreSQL (prod)
      │           │
      │           ├─ analytics: metric registry, drivers, customers, products
      │           ├─ forecasting: engine, backtests, registry, signals (festivals, weather)
      │           ├─ ingestion, connectors, costs, inventory, alerts, digest, campaigns, reviews
      │           └─ background runners (imports, forecasts, digests)
      ▼
 Every tenant-owned row carries workspace_id; membership is checked on every request
```

A modular monolith: small domain modules, one deployable unit. Design notes are in
[ARCHITECTURE](docs/ARCHITECTURE.md) and the [ADRs](docs/adr/).

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
# 2. Web: http://localhost:3000   (second terminal)
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

From the repository root: `make api`, `make web`, `make test`, `make lint`.

### Try it with sample data

1. Open <http://localhost:3000> and choose **Sign in → Create account**.
2. Name your business, then **Import sales data → Try the sample file** and follow the wizard.
3. Explore the command center, customers, products, forecasts, alerts and stock.
4. Sample files live in [`data/sample/`](data/sample/) and are regenerated with `python scripts/generate_demo_data.py`.

## Quality

- **Tests:** 400+ backend tests, including tenancy isolation, session security, the full user journey and a licence audit.
- **Static checks:** strict `mypy`, `ruff`, and `tsc --noEmit` run clean.
- **Forecast honesty:** a model ships only if it beats a naive baseline on a time-aware backtest; intervals are calibrated and their coverage is reported.
- **Plain limits:** [REVIEWS](docs/REVIEWS.md) and [MODELS](docs/MODELS.md) state what is measured and what is not. Review-sentiment accuracy on unseen reviews, for example, is not yet measured.

## Security and privacy

Server-side workspace isolation, Argon2id password hashing, 15-minute access tokens kept in memory, rotating
HttpOnly refresh cookies with reuse detection, CSRF guards, throttling, SSRF-safe link fetching, and an audit
trail. See the [threat model](docs/THREAT_MODEL.md). Customer data stays minimal (an external key and coarse
location); marketing consent is explicit.

## Licences

Only free software and data with permissive licences are used (MIT, BSD, Apache-2.0, ISC and similar). The audit,
the reviewed exceptions and the data and asset licences are in [LICENSES](docs/LICENSES.md), and a test fails if a
disallowed licence enters the dependency tree. A project licence has not been chosen yet.

## Documentation

| Doc | What it covers |
|---|---|
| [ROADMAP](docs/ROADMAP.md) · [PHASES](docs/PHASES.md) | **Start here.** Status, what is next, checklists per phase |
| [MVP](docs/MVP.md) | Release checklist and known gaps |
| [ARCHITECTURE](docs/ARCHITECTURE.md) · [API](docs/API.md) · [DATA_DICTIONARY](docs/DATA_DICTIONARY.md) | How it is built and how to call it |
| [METRICS](docs/METRICS.md) | Canonical metric definitions |
| [MODELS](docs/MODELS.md) · [EVENTS](docs/EVENTS.md) · [REVIEWS](docs/REVIEWS.md) | Forecasting, festival signals and review intelligence |
| [THREAT_MODEL](docs/THREAT_MODEL.md) · [LICENSES](docs/LICENSES.md) | Security and licensing |
| [DESIGN_SYSTEM](docs/DESIGN_SYSTEM.md) | Palette, type and motion |
| [research/](docs/research/) | Method research, including [what makes the product different](docs/research/DIFFERENTIATION.md) |
| [DEVLOG](docs/DEVLOG.md) · [CHANGELOG](CHANGELOG.md) | Dated progress and release notes |

## Roadmap

Next: purchase-bill capture (photo or PDF to cost history), a WhatsApp-first Hindi and Hinglish assistant that
answers only from the metric layer, and credit (udhaar) and supplier-price intelligence. Later phases are in the
[roadmap](docs/ROADMAP.md).

## Engineering principles

1. **SQL metrics over model arithmetic.** One metric registry feeds dashboards, the API and any assistant.
2. **Workspace isolation from day one.** Access is enforced server-side on every request.
3. **Never silently accept bad data.** Rejected rows are counted and downloadable.
4. **Human approval over autonomy.** The product suggests; people decide and send.
5. **Baselines before models.** Complexity must earn its place on a backtest.
6. **Say what is not known.** Limits are written down next to the feature.

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md): Conventional Commits, small focused commits, and the definition of done.
