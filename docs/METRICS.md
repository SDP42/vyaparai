# Canonical metric definitions

These definitions are implemented **once**, in `apps/api/app/services/analytics/metrics.py`, and shared by
the dashboard, the API and (later) the Copilot. The registry is also served at
`GET /api/v1/workspaces/{id}/metrics`. Rationale: [research/PHASE-2-RESEARCH.md](research/PHASE-2-RESEARCH.md).

Every analytics response carries: `period`, `compare` range, `currency`, `filters`,
`metric_versions` and `data_freshness`.

## Eligibility and assumptions

- **Eligible order** = status `completed`. `pending`, `cancelled` and `returned` orders are excluded
  and reported separately as data coverage (`excluded_orders_by_status`).
- **Unit prices are assumed to exclude GST.** If your export's rate includes GST, net sales will include it too.
  GST (`tax_amount`) and shipping are never part of net sales.
- **Business date** = the calendar day in the workspace timezone (default Asia/Kolkata), stored on the
  order at import. A period `from`–`to` is inclusive on both ends.
- Money is exact (Decimal) and returned as strings rounded to 2 decimals.

## Registry (version 1)

| Key | Label | Unit | Definition |
|---|---|---|---|
| `gross_sales` | Gross sales | ₹ | Σ `quantity × unit_price` over eligible lines |
| `discounts` | Discounts | ₹ | Σ line `discount_amount` over eligible lines |
| `net_sales` | Net sales | ₹ | `gross_sales − discounts` |
| `orders` | Orders | count | Distinct eligible orders |
| `units` | Units sold | count | Σ `quantity` over eligible lines |
| `aov` | Average order value | ₹ | `net_sales ÷ orders` (net, per blueprint §13) |
| `units_per_order` | Units per order | count | `units ÷ orders` |
| `discount_rate` | Discount rate | % | `discounts ÷ gross_sales` |
| `cogs` | Cost of goods sold | ₹ | Σ `quantity × unit_cost_snapshot` over eligible lines **that have a cost** |
| `gross_profit` | Gross profit | ₹ | Net sales **of lines with a cost** − `cogs` |
| `gross_margin` | Gross margin | % | `gross_profit ÷ net sales of lines with a cost` |
| `cost_coverage` | Cost coverage | % | Share of eligible net sales on lines that have a cost. Below 100 %, profit is understated |
| `active_customers` | Active customers | count | Distinct customers with ≥ 1 eligible order in the period |
| `new_customers` | New customers | count | Active customers whose **first-ever** eligible order falls in the period |
| `repeat_customers` | Repeat customers | count | Active customers with ≥ 2 eligible orders ever |
| `anonymous_order_share` | Walk-in orders | % | Eligible orders with no customer ÷ eligible orders |

## Comparisons

| Mode | Range |
|---|---|
| `previous_period` | Same number of days, ending the day before `from` |
| `previous_year` | The same range shifted back **364 days**, so weekdays line up |
| `none` | No comparison |

Change is `(current − previous) ÷ |previous|`; it is `null` when `previous = 0` (never infinity).
For percentage metrics (margin, discount rate) the change is reported in **percentage points**.

## Drivers of change (net sales)

Per product, from gross price `g`, units `q` and discounts `d`; `ḡ0` is the prior average gross price.
Products sold in both periods (set C):

- **Volume** = (Q1c − Q0c) × ḡ0c
- **Mix** = Q1c × Σ (s1ᵢ − s0ᵢ)(g0ᵢ − ḡ0c), where `sᵢ` is the product's share of units
- **Price** = Σ q1ᵢ × (g1ᵢ − g0ᵢ)

Products in one period only: **New & discontinued** = Σ gross(new) − Σ gross(discontinued).
**Discounts** = −(D1 − D0).

**Identity (unit-tested):** Volume + Mix + Price + New/discontinued + Discounts = net sales change.
These are arithmetic attributions of a change, **not** proof of cause.

## Coverage warnings returned with every response

- Comparison period has no data, or fewer days with data than the current one
- Cost coverage below 95 %
- Orders excluded by status (and their count)
- Orders without a customer (walk-ins), which limit customer metrics
- Current period starts before the first order date

## Change log

| Version | Date | Change |
|---|---|---|
| 1 | 2026-11-08 | First registry: sales, profit, order and customer metrics; PVM drivers |
