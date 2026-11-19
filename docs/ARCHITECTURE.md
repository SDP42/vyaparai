# Architecture

A modular monolith: one FastAPI service, one Next.js app, one relational database. Small domain modules keep
the code understandable; one deployable unit keeps it operable by one person.

## System overview

```
 Browser (Next.js 15)                                      background runners (in-process)
   landing · opening · /app/* (24 pages)                     imports · forecasts · digests · agents
        │  HTTPS / JSON · bearer access token (memory)               ▲
        │  HttpOnly refresh cookie · CSRF header                     │
        ▼                                                            │
 ┌──────────────────────────── apps/api (FastAPI, /api/v1) ──────────┴───────────────────────────┐
 │ middleware   hardening (headers, size limits, rate limits) · request id · access log · CORS     │
 │ routers      thin: validate, authorise, call a service, return a schema (route_class: masking)  │
 │ deps         get_db · get_current_user · WorkspaceContext(role, persona, staff name) · capability│
 │ services     one module or package per area (see below); own transactions and audit entries      │
 │ repositories workspace-scoped queries · models (SQLAlchemy 2) · Alembic migrations              │
 └───────────────┬────────────────────────────────────────────────────────────────────────────────┘
                 │
     SQLite (dev) / PostgreSQL (prod)    Redis (optional: shared rate limits)    local model files
                                         (fastembed MiniLM, Whisper medium, RapidOCR)
```

## Service map (`apps/api/app/services`)

| Area | Modules | Notes |
|---|---|---|
| Identity and teams | `auth`, `sessions`, `workspaces`, `team`, `personas`, `demo`, `audit` | roles, personas, invitations, staff-name link, one-tap sample sign-in (dev only) |
| Data in | `ingestion/`, `datasets`, `sources`, `safe_fetch`, `mapping_profiles` | upload, inspect, map, validate, import; connected links with scheduled re-imports |
| Numbers | `analytics/` | metric registry, drivers, customers, products, staff, breakdowns, drill-through |
| Forecasting | `forecasting/`, `events`, `events_insight`, `weather` | models, backtests, registry and ship gate, festival and weather signals |
| Decisions | `inventory`, `costs`, `alerts`, `digest`, `digest_delivery`, `pricing`, `goals`, `stores`, `recommend/` | stock advice, margin leaks, alerts, goals, ranked next steps |
| Money | `credit` (udhaar), `bills/` (OCR), `campaigns`, `campaign_runs`, `uplift` | ledger and ageing, supplier bills, consent-aware campaigns, holdout uplift |
| Language | `reviews/`, `docs/`, `assistant/`, `voice` | review NLP, document retrieval, the assistant, speech to text |
| Workflows and output | `agents/`, `reports/` | LangGraph investigations with stored traces; PDF and CSV reports |

## Layers

| Layer | Folder | Rule |
|---|---|---|
| Config and cross-cutting | `core/` | Settings, logging, errors, security, hardening, rate limits. No business logic. |
| Persistence | `db/`, `models/` | Declarative models, UUID keys, `workspace_id` on tenant tables. |
| Data access | `repositories/` | Where tenant queries are built. Always workspace-scoped. |
| Domain logic | `services/` | Owns transactions (`commit`) and audit entries. No HTTP types. |
| Contracts | `schemas/` | Pydantic request/response models. Never expose ORM internals. `openapi.json` is generated from them and checked by a test. |
| HTTP | `api/` | Routers and dependencies. `api/masking.py` hides cost and margin per field for personas without the capability. |

## Request flow (example: `GET /api/v1/workspaces/{id}/datasets`)

1. `request_context_middleware` assigns/propagates `X-Request-ID` and logs the request.
2. `get_current_user` decodes the bearer JWT and loads an active user → otherwise **401**.
3. `get_workspace_context` loads the caller's membership → non-members get **404** (no probing).
4. `require_role(VIEWER)` checks the role hierarchy owner > admin > analyst > viewer → **403**; routers for
   sensitive data add `require_capability(...)` for the member's persona → **403**.
5. `DatasetRepository(db, workspace_id).list()` runs a query that is already tenant-filtered.
6. A typed `Page[DatasetRead]` is returned. Errors use `{"error": {code, message, details, request_id}}`.
7. For routes using `MaskedRoute`, the response is scrubbed of cost and margin fields when the persona lacks the
   margin capability.

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

## Assistant and voice

```
spoken question ─▶ /assistant/voice ─▶ faster-whisper (in memory, discarded) ─▶ text ─▶ person confirms
typed or confirmed text ─▶ nlu.route (keywords + phrases + spoken-Hindi skeleton matching, numbers.py)
   ─▶ persona gate (refuse out-of-remit questions) ─▶ tools (typed, read-only, existing services)
   ─▶ replies (en · hinglish · hi) + evidence list ─▶ answer, optional read-aloud in the browser
```

No language model writes answers. The assistant picks a tool, the tool returns numbers and rows, and the reply
quotes them with links to where they can be checked. See [ASSISTANT](ASSISTANT.md), [VOICE](VOICE.md) and
[PERSONAS](PERSONAS.md).

## Hardening (`core/hardening.py`)

Security headers on every response; request-size caps (1 MB JSON, 20 MB multipart, about 1 MB for a voice clip);
a per-address limit on all requests and a lower one on "heavy" routes (uploads, search, questions, voice,
investigations, reports); limits are shared through Redis when configured and fail open if Redis is down. Production
settings are validated at start-up (secret length, PostgreSQL, https origins, demo login off).

## Frontend (`apps/web`)

- Routes: `/` (opening and landing), `/login`, `/join`, `/offline`, and `/app/*`: the command center and 23 pages
  (sales, customers, products, staff, pricing, reviews, campaigns, stock, forecasts, festivals, bills, costs,
  udhaar, documents, investigate, digest, reports, stores, data, team, goals, next steps, ask).
- **Marketing:** Lenis smooth scroll and GSAP ScrollTrigger for the pinned and scrubbed scenes. The opening
  (`components/opening/ShopOpening.tsx`) runs a three.js Verlet cloth (`ClothScene.ts`) tied with a ribbon that is
  cut with draggable scissors; `ClothOpening.tsx` (SVG and CSS with GSAP) is the fallback without WebGL. No images
  or sounds; textures are generated in code.
- **App shell:** a client-side shell (`AppShell`) with a workspace context and a persona context. It shows a
  pinned, scrollable, grouped sidebar on desktop, an icon rail on tablets and a bottom bar plus a "More" sheet on
  phones, filtered to the pages of the member's persona.
- **Data:** `lib/api.ts` wraps `fetch` with the bearer token, the error envelope and downloads; shared types come
  from `lib/api-types.ts`, generated from the API's OpenAPI description (`make gen-api`).
- **Languages:** `lib/i18n.tsx` holds English, Hinglish and Hindi dictionaries typed so every key must exist in all
  three.
- **Voice:** `VoiceInput` records, `lib/wav.ts` makes 16 kHz WAV and detects the end of speech, `lib/speak.ts` reads
  answers aloud with the device voice.
- **PWA:** manifest, icons and a service worker (tested by simulation in Node) that caches reads for offline use and
  clears them on sign-out.
- Design tokens live in `apps/web/app/globals.css`. See [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).
