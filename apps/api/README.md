# apps/api: Vyapar AI backend

FastAPI modular monolith. See [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) and [docs/API.md](../../docs/API.md).

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py --port 8000   # http://localhost:8000/docs
uv run pytest                                 # tests
uv run ruff check . && uv run mypy app        # lint + types
```

```
app/
├── core/          settings, logging, errors, security, middleware
├── db/            declarative base, mixins, engine/session
├── models/        SQLAlchemy models
├── schemas/       Pydantic request/response contracts
├── repositories/  workspace-scoped data access
├── services/      domain logic + transactions + audit
└── api/           deps (auth, workspace RBAC) and v1 routers
```

## Local demo data

```bash
python ../../scripts/generate_demo_data.py   # writes data/sample/vyapar_demo_sales{,_messy}.csv
```

The web app's import wizard also has a **Try the sample file** button (`apps/web/public/samples/`).

A local-only test account was created in the dev SQLite database while building Phase 1:
`demo.owner@example.com` / `vyapar-demo-2026` (workspace "Kulkarni General Stores", sample data
imported). It exists only in your local `vyapar_dev.db`; delete that file to start fresh.
