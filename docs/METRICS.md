# Canonical metric definitions (v1 draft)

Every metric has **one** implementation in the metric layer (Phase 2), shared by dashboards, the API
and the Copilot. Every metric response includes: `period`, `currency`, `filters`,
`definition_version` and `data_freshness`.

| Metric | Definition (v1) | Includes | Excludes |
|---|---|---|---|
| **Gross sales** | Σ `quantity × unit_price` | all line items on eligible orders | — |
| **Discounts** | Σ `discount_amount` | line-level discounts | — |
| **Net sales** | Gross sales − discounts − returns | completed orders | tax (GST), shipping, cancelled/pending orders |
| **COGS** | Σ `quantity × unit_cost_snapshot` | completed orders | lines without a cost (flagged as coverage gap) |
| **Gross profit** | Net sales − COGS | | |
| **Gross margin %** | Gross profit ÷ Net sales | | undefined when net sales = 0 |
| **Orders** | count of distinct completed orders | | cancelled, pending |
| **Units** | Σ `quantity` on completed orders | | |
| **AOV** | Net sales ÷ Orders | | |
| **Discount rate** | Discounts ÷ Gross sales | | |
| **Active customers** | customers with ≥ 1 completed order in the period | | anonymous orders |
| **New customers** | first completed order falls in the period | | |
| **Repeat customers** | ≥ 2 completed orders, ever, with ≥ 1 in the period | | |

**Eligible order** = `status = completed`. Returned orders reduce net sales in the period of the
return (once a `returns` table exists; until then `status = returned` orders are excluded and the
response carries a caveat).

**Time bucketing** uses the workspace timezone (default Asia/Kolkata), not UTC.

**Change explanation (Phase 2):** period-over-period change in net sales is decomposed into
**volume**, **price**, **mix** and **discount** effects. These are attributions, not causal claims.
