# Data dictionary

All tables use UUID primary keys and `created_at` / `updated_at` (UTC). Tenant-owned tables carry
`workspace_id` (FK → `workspaces.id`, `ON DELETE CASCADE`, indexed). Money is `NUMERIC(14,2)`,
quantity is `NUMERIC(12,3)` (loose goods sold by weight), never float.

## Identity & tenancy

| Table | Key columns | Notes |
|---|---|---|
| `users` | `email` (unique, lower-cased), `full_name`, `hashed_password` (Argon2id), `is_active` | |
| `workspaces` | `name`, `slug` (unique), `currency` (default `INR`), `timezone` (default `Asia/Kolkata`), `created_by_id` | One business = one workspace |
| `memberships` | `workspace_id`, `user_id`, `role` ∈ owner/admin/analyst/viewer | Unique (`workspace_id`, `user_id`) |
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
| `orders` | `external_key`, `customer_id?`, `dataset_id?` (lineage), `order_date`, `status` ∈ pending/completed/cancelled/returned, `channel`, `currency`, `shipping_amount`, `tax_amount` | Unique (`workspace_id`, `external_key`); index (`workspace_id`, `order_date`) |
| `order_items` | `order_id`, `product_id`, `quantity`, `unit_price`, `discount_amount`, `unit_cost_snapshot` | Cost snapshot keeps historical margin accurate |

## Planned tables

`returns` (Phase 1–2), `inventory_snapshots`, `suppliers`, `purchase_orders` (Phase 5), `reviews`
(Phase 6), `documents`, `document_chunks` (Phase 7), `recommendations` (Phase 10). See
[RESEARCH.md](RESEARCH.md#1-gaps-in-the-blueprint-things-it-implies-but-does-not-define).

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
| `status` | | completed |
| `tax_amount` | | 14.75 |
