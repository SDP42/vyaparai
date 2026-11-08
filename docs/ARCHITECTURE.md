# Architecture

## System overview

```
┌──────────────┐  HTTPS/JSON   ┌───────────────────────────── apps/api (FastAPI) ─────────────────────────────┐
│  apps/web    │ ────────────▶ │ middleware: request-id · access log · CORS · error envelope                  │
│  Next.js     │               │ api/v1 routers ── thin: validate, authorize, call service, return schema      │
│  (landing,   │ ◀──────────── │ deps: get_db · get_current_user · WorkspaceContext · require_role(min)        │
│   app)       │               │ services: auth · workspaces · audit · (ingestion, metrics, forecast … later)   │
└──────────────┘               │ repositories: WorkspaceScopedRepository ── always filters by workspace_id      │
                               │ models (SQLAlchemy 2.0) ── migrations (Alembic)                               │
                               └───────────────┬───────────────────────────────────────────────────────────────┘
                                               │
                          SQLite (dev) / PostgreSQL (prod)      ml/ · rag/ · agents/ (later phases)
```

## Layers (apps/api/app)

| Layer | Folder | Rule |
|---|---|---|
| Config & cross-cutting | `core/` | Settings, logging, errors, security, middleware. No business logic. |
| Persistence | `db/`, `models/` | Declarative models, UUID keys, `workspace_id` on tenant tables. |
| Data access | `repositories/` | The only place that builds queries for tenant data. Always workspace-scoped. |
| Domain logic | `services/` | Owns transactions (`commit`) and audit entries. No HTTP types. |
| Contracts | `schemas/` | Pydantic request/response models. Never expose ORM internals. |
| HTTP | `api/` | Routers + dependencies. Thin. |

## Request flow (example: `GET /api/v1/workspaces/{id}/datasets`)

1. `request_context_middleware` assigns/propagates `X-Request-ID` and logs the request.
2. `get_current_user` decodes the bearer JWT and loads an active user → otherwise **401**.
3. `get_workspace_context` loads the caller's membership → non-members get **404** (no probing).
4. `require_role(VIEWER)` checks the role hierarchy owner > admin > analyst > viewer → **403**.
5. `DatasetRepository(db, workspace_id).list()` runs a query that is already tenant-filtered.
6. A typed `Page[DatasetRead]` is returned. Errors use `{"error": {code, message, details, request_id}}`.

## Tenancy

See [ADR-0003](adr/0003-workspace-tenancy.md). Authorization is enforced in application code;
PostgreSQL row-level security may be added later as defence in depth.

## Background work (Phase 1+)

A `jobs` table records long-running work (imports, training, embeddings) with status and progress.
The MVP runs jobs in-process; a Redis-backed queue can replace the runner without API changes,
because clients only see `GET /jobs/{id}`.

## Ingestion pipeline (Phase 1)

```
upload ─▶ detect type (extension + signature) ─▶ stream to disk (hash, size cap)
       ─▶ inspect (headers, types, samples, mapping suggestions) ─▶ Dataset(status=uploaded)
mapping ─▶ validate_mapping ─▶ Dataset(status=mapped)
validate ─▶ per-row checks, order consistency ─▶ summary + errors ─▶ Dataset(status=validated)
import  ─▶ Job(queued) ─▶ background task: re-validate ─▶ one transaction:
           products, customers, orders, order_items ─▶ Dataset(imported), Job(succeeded)
```

Code: `services/ingestion/{fields,reader,parsing,pipeline}.py` and `services/datasets.py`.
Validation is the single source of truth: the import re-runs it, so a changed mapping or file can
never import unchecked rows.

## Metric layer (Phase 2)

All analytics read through one engine in `services/analytics/` so the dashboard, API and (later)
Copilot cannot disagree. Metric definitions live in a versioned registry (`metrics.py`); the engine
aggregates order lines once per query; comparisons, drivers and drill-through reuse the same filters.
See [METRICS.md](METRICS.md) and [research/PHASE-2-RESEARCH.md](research/PHASE-2-RESEARCH.md).

## Frontend (`apps/web`)

- Routes: `/` (opening + landing), `/login`, `/app` (command center for accounts; demo dashboard for personas),
  and `/app/sales`, `/app/data` for accounts.
- **Marketing:** Lenis smooth scroll → GSAP ScrollTrigger (pinned/scrubbed scenes) → React Three Fiber
  for the opening (`components/opening/`). Motion handles UI transitions. Each element is animated by one system.
- **App:** a client-side shell with a workspace context; `lib/api.ts` wraps `fetch` with the bearer token,
  the error envelope and download helpers; types mirror `apps/api/app/schemas`.
- Design tokens live in `apps/web/app/globals.css`. See [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).
