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
  Codes: `bad_request`, `unauthenticated`, `forbidden`, `not_found`, `conflict`, `validation_error`, `invalid_mapping`, `invalid_state`, `unsupported_file`, `payload_too_large`, `internal_error`.
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
| POST | `/workspaces/{id}/datasets` | analyst | Upload CSV/XLSX (multipart `file`, optional `name`) → inspection + suggested mapping. 409 if the same file was already uploaded, 413 too large, 415 unsupported |
| GET | `/workspaces/{id}/datasets` | viewer | Paginated datasets |
| GET | `/workspaces/{id}/datasets/{dataset_id}` | viewer | Dataset detail incl. `inspection` and `validation` |
| PUT | `/workspaces/{id}/datasets/{dataset_id}/mapping` | analyst | `{"fields": {canonical: column}, "date_order": "dmy"\|"mdy"\|"ymd"}`; 422 `invalid_mapping` if a required field is missing |
| POST | `/workspaces/{id}/datasets/{dataset_id}/validate` | analyst | Validate every row → counts, errors by field, sample errors, preview (orders, products, customers, period, net sales) |
| GET | `/workspaces/{id}/datasets/{dataset_id}/errors.csv` | viewer | Download all rejected rows with reasons |
| POST | `/workspaces/{id}/datasets/{dataset_id}/import` | analyst | 202 + job; runs in the background in one transaction |
| GET | `/workspaces/{id}/jobs/{job_id}` | viewer | Job status, counts and result |
| GET | `/workspaces/{id}/data-summary` | viewer | Orders, line items, products, customers, period, net sales in the workspace |
| GET | `/workspaces/{id}/metrics` | viewer | The metric registry: key, label, unit, version, definition, includes, excludes, plus eligibility and assumptions |
| GET | `/workspaces/{id}/analytics/filters` | viewer | Category / channel / region options, first and last order date, default period |
| GET | `/workspaces/{id}/analytics/overview` | viewer | KPIs with comparison, trend (gap-filled, comparison overlay), category/channel/region mix, weekday pattern, top and bottom products, insights, warnings |
| GET | `/workspaces/{id}/analytics/drivers` | viewer | Volume / mix / price / new-discontinued / discount effects that sum to the net sales change, contribution table (`by=category\|product\|channel\|region`), biggest movers |
| GET | `/workspaces/{id}/analytics/transactions` | viewer | Drill-through: paginated order lines with total lines and net for the same filters; `search` matches bill, SKU or product |
| GET | `/workspaces/{id}/analytics/customers/summary` | viewer | Customer count, repeat rate, revenue per customer, top-10 % share, 8 segments, Active/Cooling/Lapsed counts, 5×5 R×F grid, warnings. Params: `as_of`, `lookback_days`, `new_days`, `active_days`, `lapse_days` (`lapse_days` must exceed `active_days`, else `422 invalid_params`) |
| GET | `/workspaces/{id}/analytics/customers/list` | viewer | Paged customers with R/F/M, segment, status; filters `segment`, `status`, `search`; `sort` = `net`, `orders`, `recency`, `last_order`, `name`; `descending`, `limit`, `offset` |
| GET | `/workspaces/{id}/analytics/customers/cohorts` | viewer | Retention matrix by first-order month (`months` 2–36) |
| GET | `/workspaces/{id}/analytics/customers/export.csv` | viewer | The filtered customer list as CSV |
| GET | `/workspaces/{id}/analytics/products` | viewer | Per product: net, share, ABC, margin, discount rate, change vs comparison, quadrant, flags; category table; portfolio summary |
| GET | `/workspaces/{id}/analytics/products/export.csv` | viewer | Product table as CSV |
| GET | `/workspaces/{id}/analytics/basket` | viewer | Product pairs with orders, support, confidence both ways and lift; `min_orders` (default 5), `limit` |

### Analytics query parameters

`from`, `to` (inclusive business dates, default: 30 days ending at the latest order) · `compare` =
`previous_period` \| `previous_year` (same weekdays, 364 days earlier) \| `none` · `granularity` = `day` \| `week` \| `month`
(auto by range) · repeatable filters `category`, `channel`, `region` (`Unspecified` = missing), `sku`.
Money values are strings with 2 decimals. Every response carries `meta`: period, comparison range,
currency, timezone, filters, metric versions, data freshness and coverage (days with data, cost
coverage, excluded orders by status). Invalid ranges return `422 invalid_range`.

## Planned

| Phase | Endpoint |
|---|---|
| 3 | `GET …/analytics/customers` (RFM, cohorts) · `GET …/analytics/products` (margin, discount) |
| 4 | `POST /workspaces/{id}/forecasts` · `GET …/forecasts/{id}` |
| 7 | `GET /workspaces/{id}/documents/search` |
| 8 | `POST /workspaces/{id}/copilot/runs` · `GET …/copilot/runs/{id}` |
