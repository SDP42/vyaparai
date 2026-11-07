# API reference

Interactive docs: `http://localhost:8000/docs` · OpenAPI: `/api/v1/openapi.json`

## Conventions

- **Versioned** under `/api/v1`.
- **Auth:** `Authorization: Bearer <access_token>` from `POST /auth/login`.
- **Tenant scope in the path:** `/workspaces/{workspace_id}/…`. Non-members receive `404`.
- **IDs** are UUIDs. Sequential database IDs are never exposed.
- **Pagination:** `?limit=` (1–200, default 50) and `&offset=`; response `{items, total, limit, offset}`.
- **Errors** always have this shape:
  ```json
  {"error": {"code": "not_found", "message": "Workspace not found", "details": null, "request_id": "…"}}
  ```
  Codes: `bad_request`, `unauthenticated`, `forbidden`, `not_found`, `conflict`, `validation_error`, `internal_error`.
- **Tracing:** send `X-Request-ID` (8–64 chars `[A-Za-z0-9._-]`) or one is generated; it's echoed on every response.

## Endpoints (implemented)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/health/live` | — | Liveness |
| GET | `/health/ready` | — | Readiness (DB check, 503 if down) |
| POST | `/auth/register` | — | Create account (`email`, `full_name`, `password` ≥ 10 chars) |
| POST | `/auth/login` | — | OAuth2 form (`username`=email, `password`) → `{access_token, expires_in}` |
| GET | `/auth/me` | user | Current user |
| POST | `/workspaces` | user | Create workspace; caller becomes **owner** |
| GET | `/workspaces` | user | Workspaces the caller belongs to, with role |
| GET | `/workspaces/{id}` | viewer | Workspace detail + caller role |
| PATCH | `/workspaces/{id}` | admin | Update name / currency / timezone |
| GET | `/workspaces/{id}/members` | viewer | List members |
| POST | `/workspaces/{id}/members` | admin | Add an existing user (only owners can grant owner) |
| GET | `/workspaces/{id}/audit-logs` | admin | Paginated audit trail |
| GET | `/workspaces/{id}/datasets` | viewer | Paginated datasets |
| GET | `/workspaces/{id}/datasets/{dataset_id}` | viewer | Dataset detail |
| GET | `/workspaces/{id}/jobs/{job_id}` | viewer | Job status / progress |

## Planned

| Phase | Endpoint |
|---|---|
| 1 | `POST /workspaces/{id}/datasets` (upload) · `POST …/datasets/{id}/mapping` · `POST …/datasets/{id}/import` · `GET …/datasets/{id}/errors.csv` |
| 2 | `GET /workspaces/{id}/analytics/sales` · `GET …/metrics` (registry) · `GET …/analytics/drivers` |
| 4 | `POST /workspaces/{id}/forecasts` · `GET …/forecasts/{id}` |
| 7 | `GET /workspaces/{id}/documents/search` |
| 8 | `POST /workspaces/{id}/copilot/runs` · `GET …/copilot/runs/{id}` |
