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

## Frontend

- App Router routes: `/` (landing), `/login` (persona chooser + email form), `/app` (dashboard).
- Landing motion stack: Lenis (smooth scroll) → GSAP ScrollTrigger (pinned/scrubbed scenes) →
  React Three Fiber (one `THREE.Points` draw call with a custom shader). Motion (Framer) is used
  for UI transitions on `/login` and `/app`. Each element is animated by one system only.
- Design tokens live in `apps/web/app/globals.css` (`@theme`). See [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).
