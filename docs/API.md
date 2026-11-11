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
| POST | `/auth/login` | — | OAuth2 form (`username`=email, `password`) → `{access_token, expires_in}` and sets the HttpOnly `vyapar_refresh` cookie; 429 `too_many_attempts` after repeated failures |
| POST | `/auth/refresh` | cookie + `X-Requested-With: vyapar` | Rotate the refresh cookie, return a new `{access_token, expires_in}` |
| POST | `/auth/logout` | cookie + header | Revoke this sign-in; clears the cookie (204) |
| POST | `/auth/logout-all` | user + header | Revoke every sign-in of this user (204) |
| GET | `/auth/me` | user | Current user |

Purchase bills (`/workspaces/{id}/bills`, see [BILLS](BILLS.md)) and reviews (`/workspaces/{id}/reviews`, see [REVIEWS](REVIEWS.md)) have their own endpoint lists in those documents.
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
| GET | `/workspaces/{id}/forecasts/latest` | viewer | Totals with range, accuracy, model card, movers, confidence counts, warnings, `signals` (weather status and whether it helped) |
| POST | `/workspaces/{id}/forecasts/run` | analyst | Start a forecast job (202); a job older than 15 minutes that never finished is replaced |
| GET | `/workspaces/{id}/forecasts/products` | viewer | Per-product forecasts; filters `search`, `confidence`, `model`, `pattern`; `sort` = `units_next\|change\|wape\|name` |
| GET | `/workspaces/{id}/forecasts/products/{sku}` | viewer | History, forecast with p10/p50/p90 and backtest for one product |
| GET | `/workspaces/{id}/forecasts/export.csv` | viewer | Every product and day as CSV |
| GET | `/workspaces/{id}/weather/cities` | viewer | Cities with coordinates (static list, no external call) |
| GET | `/workspaces/{id}/weather/status` | viewer | Whether weather is allowed, free tier or paid, shop location, attribution |
| PUT | `/workspaces/{id}/weather/location` | admin | Set the shop's city (from the list) or latitude/longitude |
| GET | `/workspaces/{id}/campaigns/playbook` | viewer | Per segment: goal, idea, kind, customer count, default discount ceiling, assumed redemption |
| GET | `/workspaces/{id}/campaigns/plan` | viewer | For one `segment`: audience (contact vs holdout), margin-safe offers, step ladder, projection (assumptions labelled), message rows; params `max_discount`, `margin_floor`, `holdout_pct`, `language` (`en`\|`hinglish`), `valid_days`, paging |
| GET | `/workspaces/{id}/campaigns/export.csv` | analyst | Full contact list with groups and messages for manual sending; each export is audited |
| GET | `/workspaces/{id}/digests/preview` | viewer | Build a digest now (`kind=daily\|weekly`, optional `as_of`): three numbers, one action, text and HTML; nothing stored |
| GET / PUT | `/workspaces/{id}/digests/settings` | viewer / admin | Delivery: enabled, frequency, local hour, weekday, up to 5 recipients; reports whether email is configured |
| POST | `/workspaces/{id}/digests/send-now` | admin | Store and email the digest to the recipients; status is `sent`, `not_configured`, `failed` or `stored` |
| GET | `/workspaces/{id}/digests/history` | viewer | Digests already generated |
| GET | `/workspaces/{id}/costs/overview` | viewer | Per product: cost and price now vs the window before, margin, status (`margin_leak`, `passed_on`, `cost_down`, `stable`, `no_cost`, `new`, `too_few`), margin lost and the price that restores it; summary |
| GET | `/workspaces/{id}/costs/{sku}/history` | viewer | Weekly cost and net price per unit for one product |
| GET | `/workspaces/{id}/alerts` | viewer | Recompute and list alerts (`status=open\|dismissed\|resolved\|all`, optional `as_of`) with counts by severity |
| GET | `/workspaces/{id}/alerts/summary` | viewer | Open alert counts by severity, without recomputing (used by the sidebar badge) |
| POST | `/workspaces/{id}/alerts/{alert_id}/dismiss` \| `/reopen` | analyst | Hide or bring back one alert |
| POST | `/workspaces/{id}/forecasts/run?tune=&peak_uplift_pct=` | analyst | Start a forecast; `tune` also searches for better model settings, `peak_uplift_pct` (0–50) adds demand near the festive season (labelled as the owner's assumption) |
| GET | `/workspaces/{id}/forecasts/runs` | viewer | Every version: status (`active`, `superseded`, `rejected`), accuracy, ship-gate result, methods used, options, tuning, note |
| POST | `/workspaces/{id}/forecasts/runs/{run_id}/activate` | admin | Make a version the one the app shows (rollback); audited |
| GET | `/workspaces/{id}/inventory/overview` | viewer | Per product: stock today, days of cover, run-out date, status, order quantity and cost, cash tied up; summary. `service` (0–1) and `review_days` shape the advice |
| POST | `/workspaces/{id}/inventory/import` | analyst | Upload a stock CSV (SKU, stock, optional date, lead time, pack size); reports unmatched and rejected rows |
| PUT | `/workspaces/{id}/inventory/items/{sku}` | analyst | Set stock, delivery days, pack size, safety days |
| GET | `/workspaces/{id}/inventory/template.csv` \| `order-list.csv` | viewer \| analyst | Starter file with your products; the suggested purchase list (audited) |
| GET | `/workspaces/{id}/events/upcoming` | viewer | Events in the next N days for the shop's region, with matching products, stock cover and risk, and what the event did last time |
| GET | `/workspaces/{id}/events/calendar` | viewer | Events in a date range (`tier_max`, `include_cricket`), each marked `core` or `zone` |
| GET | `/workspaces/{id}/events/effects` | viewer | Observed lift of past events on this shop's sales |
| GET | `/workspaces/{id}/events/regions` \| PUT `/events/region` | viewer \| admin | States and zones; set the shop's state |
| GET | `/workspaces/{id}/events/coverage` | viewer | How far the dated table reaches and its confidence mix |
| GET / POST | `/workspaces/{id}/sources` | viewer / analyst | Connected links (Google Sheet, Drive, Dropbox) with schedule (`manual`, `hourly`, `daily`), last result and failures; up to 5. Links are checked on creation (https, allow-listed host) |
| PATCH / DELETE | `/workspaces/{id}/sources/{source_id}` | analyst | Rename, change schedule, pause or resume; remove (imported data stays) |
| POST | `/workspaces/{id}/sources/{source_id}/run` | analyst | Check the link now (202); runs in the background and imports only new orders |
| GET | `/workspaces/{id}/sources/{source_id}/runs` | viewer | Recent checks with what each added |

Uploads now return `column_mapping.remembered: true` (and `profile_name`) when the file's layout matches a mapping confirmed before.

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

## Personas and voice

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/auth/demo-status` | public | `{enabled, personas[]}`; empty unless `DEMO_LOGIN_ENABLED=true` (never in production) |
| POST | `/auth/demo-login` | public | `{persona}` signs in as that sample person (CSRF header required, throttled); 404 when off |
| GET | `/workspaces/{id}/me?lang=` | viewer | The caller's role and persona: pages, capabilities, suggestions in `en`, `hinglish` or `hi` |
| POST | `/workspaces/{id}/invitations` | admin | Accepts `persona` beside `role`; 400 if the persona does not fit the role |
| PATCH | `/workspaces/{id}/members/{user}` | admin | `{role, persona?}`; omit `persona` to keep it (cleared if it no longer fits) |
| POST | `/workspaces/{id}/assistant/voice` | viewer | Multipart `audio` (16-bit PCM WAV, up to 15 s and about 1 MB) and `language` (`hi`, `en`, `mr`, `gu`); returns `{text, language, seconds, ms, reason, confidence}`; audio is not stored |

Routes for the credit book, costs, pricing, supplier bills and reports answer 403 to a persona without the matching capability ([PERSONAS](PERSONAS.md)).
