# Data dictionary

All tables use UUID primary keys and `created_at` / `updated_at` (UTC). Tenant-owned tables carry
`workspace_id` (FK → `workspaces.id`, `ON DELETE CASCADE`, indexed). Money is `NUMERIC(14,2)`,
quantity is `NUMERIC(12,3)` (loose goods sold by weight), never float.

## Identity & tenancy

| Table | Key columns | Notes |
|---|---|---|
| `users` | `email` (unique, lower-cased), `full_name`, `hashed_password` (Argon2id), `is_active` | |
| `workspaces` | `name`, `slug` (unique), `currency` (default `INR`), `timezone` (default `Asia/Kolkata`), `created_by_id` | One business = one workspace |
| `memberships` | `workspace_id`, `user_id`, `role` ∈ owner/admin/analyst/viewer, `persona?` ∈ owner/ops_manager/analyst/accountant/cashier, `staff_name?` | Unique (`workspace_id`, `user_id`). The persona narrows what is shown and asked; `staff_name` links the person to the name on their bills |
| `invitations` | `workspace_id`, `role`, `persona?`, `token_hash` (SHA-256, the token is never stored), `expires_at`, `used_at`, `revoked_at` | One-time link, valid 7 days |
| `refresh_tokens` | `user_id`, `family_id`, `token_hash`, `family_started_at`, `expires_at`, `used_at`, `revoked_at`, `user_agent` | Rotating sessions; reuse of a used token revokes its family |
| `audit_logs` | `workspace_id?`, `actor_user_id?`, `action`, `entity_type`, `entity_id`, `details` (JSON), `request_id` | Append-only |

## Ingestion

| Table | Key columns | Notes |
|---|---|---|
| `datasets` | `name`, `source_filename`, `file_type`, `file_hash` (SHA-256), `file_size_bytes`, `row_count`, `status` (uploaded → mapped → validated → imported / failed), `column_mapping` (JSON: fields + date order), `inspection` (JSON), `validation` (JSON summary), `storage_path` | Unique (`workspace_id`, `file_hash`) → duplicate upload detection. Files are stored outside the web root under `STORAGE_DIR/{workspace_id}/` |
| `jobs` | `job_type` ∈ import/forecast_training/embedding, `status` ∈ queued/running/succeeded/failed/cancelled, `progress` 0–100, `rows_total/accepted/rejected`, `error_message`, `result` | Polled via `GET /jobs/{id}` |

## Commerce core

| Table | Key columns | Notes |
|---|---|---|
| `products` | `sku`, `name`, `category`, `unit_cost`, `list_price`, `active` | Unique (`workspace_id`, `sku`) |
| `customers` | `external_key`, `region`, `city`, `marketing_consent`, `status` | Minimal PII by design: no names or phone numbers |
| `orders` | `external_key`, `customer_id?`, `dataset_id?` (lineage), `order_date` (UTC instant), **`business_date`** (calendar day in the workspace timezone; analytics buckets by this), `channel?`, **`staff?`** (the cashier or salesperson on the bill, as typed), `status` ∈ pending/completed/cancelled/returned, `currency`, `shipping_amount`, `tax_amount` | Unique (`workspace_id`, `external_key`); indexes (`workspace_id`, `order_date`) and (`workspace_id`, `business_date`). Imported wall-clock times are interpreted in the workspace timezone |
| `order_items` | `order_id`, `product_id`, `quantity`, `unit_price`, `discount_amount`, `unit_cost_snapshot` | Cost snapshot keeps historical margin accurate |

## Other tables, by area

| Area | Tables |
|---|---|
| Ingestion and connectors | `mapping_profiles` (remembered column mappings), `import_sources`, `source_runs` (connected links and their runs) |
| Stock and costs | `stock_snapshots`, `inventory_settings` (lead time, safety days, pack size) |
| Forecasting | `forecast_runs`, `forecast_series` (per-series model, pattern, confidence, backtest error and bias), `weather_daily` (cached weather) |
| Alerts, digest, goals, recommendations, reports | `alerts`, `digests`, `digest_settings`, `goals`, `recommendations`, `saved_reports` |
| Campaigns | `campaigns`, `campaign_recipients`, `customer_contacts` (phone and consent, kept apart from `customers`) |
| Credit and bills | `credit_entries` (udhaar ledger), `purchase_bills`, `purchase_bill_lines` |
| Daily routines | `expenses` (day, category, amount, paid by, note), `day_closes` (one per day: morning cash, cash/UPI/card sales, taken out, counted cash), `expiry_items` (name, optional product, batch, expiry date, quantity, how it was cleared) |
| Automations | `agent_schedules` (workflow, enabled, local hour, last day run) |
| Language | `reviews`, `documents`, `document_chunks` (passage text and embedding), `agent_runs`, `agent_steps` (stored investigation traces) |

Every one of these carries `workspace_id` and is only reached through workspace-scoped queries.

## Import file format (Phase 1)

One row per order line. Column names are free-form; the user maps them in the UI.

| Canonical field | Required | Example |
|---|---|---|
| `order_id` | ✅ | INV-2041 |
| `order_date` | ✅ | 2026-10-21 or 21/10/2026 |
| `sku` | ✅ | ATT-5KG |
| `product_name` | ✅ | Aashirvaad Atta 5kg |
| `quantity` | ✅ | 2 |
| `unit_price` | ✅ | 295.00 |
| `category` | | Staples |
| `discount` | | 10.00 |
| `unit_cost` | | 248.00 |
| `customer_id` | | C-1093 |
| `region` / `city` | | Maharashtra / Pune |
| `channel` | | store / online |
| `staff` (cashier, salesperson) | | Sunita Patil |
| `status` | | completed |
| `tax_amount` | | 14.75 |
