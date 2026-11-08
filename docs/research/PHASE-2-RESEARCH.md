# Phase 2 research: metric layer, comparisons and driver analysis

_Date: 2026-11-08 · Blueprint sections: §13 Canonical metrics, §14 Sales intelligence_

The goal of Phase 2 is a **trusted** command center: every number comes from one definition, every
comparison states what it is compared with, and every "why" is an arithmetic decomposition that
adds up exactly, not a story. This note records what I looked up and the decisions it led to.

## 1. What the blueprint requires

- **One canonical implementation** shared by dashboards, API and Copilot, published as a **metric registry** (§13).
- Net sales must state its treatment of **discounts, refunds, cancellations, tax and shipping**.
- Gross profit = net sales − COGS on a **documented cost basis**; AOV = eligible net sales ÷ eligible completed orders.
- Customer count needs explicit **active / new / repeat windows**.
- **Every metric response** carries period, currency, filters, **calculation version** and **data freshness**.
- Sales intelligence (§14): trend, period comparison, category contribution, top/bottom products,
  **drivers of change** (volume, price, mix, discount, data coverage), filters (date, region, channel,
  category, segment), drill-through to transactions, and **no causal claims** from comparisons.

## 2. Findings

### 2.1 Price–volume–mix (PVM) analysis
Sources: [Coefficient: PVM analysis](https://coefficient.io/cfo-resources/price-volume-mix-analysis-excel),
[Zebra BI: PVM bridge](https://zebrabi.com/template/bridge-price-volume-mix/),
[Achievable CMA: sales variances](https://app.achievable.me/study/cma-part-1/learn/performance-management-cost-and-variance-measures-flexible-budgets-sales-variances-4).

- Price and volume effects are defined consistently; **mix conventions differ** (vs prior-period mix or
  vs a standard/budget mix), and the price effect can use current or prior volume.
- The invariant every source relies on: **price + volume + mix = total revenue change**.
- Decision: pick **one** convention, document it, and make "effects sum to the change" a unit test.

### 2.2 Retail KPI definitions
Sources: [Umbrex retail KPI definitions](https://www.umbrex.com/resources/retail-industry-playbooks/retail-kpi-dashboard-weekly-business-review-playbook/retail-kpi-architecture-and-metric-definitions/),
[Cin7: retail KPIs](https://cin7.com/blog/retail-kpis).

- Net sales = gross sales − returns/allowances (discounts are usually netted too).
- Average transaction value = sales ÷ transactions, **but sources disagree on gross vs net sales in the
  numerator**, so the definition must be stated on the metric itself.
- Units per transaction (basket depth) = units ÷ transactions. Track margin as both **₹ and %**.
- Decision: AOV uses **net** sales (as the blueprint says); also expose units per order and gross margin ₹ and %.

### 2.3 Comparing periods
Sources: [Holistics period comparison](https://docs.holistics.io/docs/period-comparison),
[GoodMetrics date options](https://docs.goodmetrics.io/stats-dashboard/dates).

- Tools offer a **plain calendar shift** and a **weekday-matched shift** (whole weeks). Weekday matching
  is preferred when weekdays differ in traffic, which is true of every shop (Saturdays vs Tuesdays).
- For year-over-year, shift **364 days** (52 weeks) so weekdays align. Moving festivals still need care.
- Decision: offer **previous period** (same length, immediately before), **same weekdays last year**
  (−364 days) and **none**; always return and show the comparison's own date range.

### 2.4 Metric registries / semantic layers
Sources: [dbt MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow), [Lyft metric semantic layer](https://eng.lyft.com/metric-semantic-layer-how-lyft-governs-and-scales-key-data-definitions-56bee3643c29),
[Polar: semantic vs metrics layer](https://www.polaranalytics.com/post/semantic-layer-vs-metrics-layer-vs-data-catalog-what-is-the-difference).

- A metric layer holds definitions (what to calculate), dimension bindings, aggregation types, time-grain
  rules, ownership and versioning, kept in version-controlled code.
- A definition change normally applies everywhere at once; I found nothing on per-metric version **pinning**.
- Decision: a small Python registry with `key`, `version`, `unit`, formula text, inclusions/exclusions
  and the dimensions it supports. The version is returned in every response; changing a formula bumps it
  and is recorded in the changelog. (Pinning old versions is not needed at this scale.)

## 3. Decisions for Phase 2

| # | Question | Decision | Why |
|---|---|---|---|
| 1 | What counts as a sale? | Order status `completed` only. `pending`, `cancelled`, `returned` are excluded and counted separately as data-coverage facts | Matches blueprint "eligible completed orders" |
| 2 | Net sales | Σ(quantity × unit price) − Σ line discounts. **GST and shipping excluded.** Unit prices are assumed ex-GST (stated in the UI and METRICS.md) | Matches the owner's GST return; stated assumption |
| 3 | Gross profit | Net sales − Σ(quantity × unit-cost snapshot), computed **only on lines that have a cost**; margin % = profit ÷ net sales of the same lines; **cost coverage %** returned | Avoids overstating profit when costs are missing |
| 4 | AOV | Net sales ÷ distinct completed orders | Blueprint §13 |
| 5 | Day boundaries | Store a **business date** on each order, computed in the workspace timezone (default Asia/Kolkata) when importing | Day buckets must match the shopkeeper's day, not UTC; avoids timezone SQL differences between SQLite and PostgreSQL |
| 6 | Default period | Last 30 days **ending at the latest order date** in the workspace | Imported history is rarely "today"; an empty "last 30 days" would be useless |
| 7 | Comparison | previous period · same weekdays last year (−364 d) · none | §2.3 |
| 8 | Trend grain | Day, week (Mon–Sun) or month; **gap-filled** with zeros so missing days are visible | A line that skips days hides stock-outs |
| 9 | Customers | **Active** = distinct customers with ≥1 completed order in the period · **New** = first-ever completed order in the period · **Repeat** = active with ≥2 completed orders ever. Anonymous (walk-in) orders reported as a share | Blueprint §13; METRICS.md v1 |
| 10 | Drivers | PVM on **gross** revenue per product, plus a separate **discount** effect and a **new/discontinued products** effect (§4) | Gross/discount split lets us name discounting as a driver; effects must sum exactly |
| 11 | Contribution tables | Δ net sales by category, product, channel, region, with share of total change | §14 "contribution by product/category/channel" |
| 12 | Insights | Rule-based, deterministic facts with evidence references; **no causal wording** ("explained by", not "caused by") | §14; also prepares the Copilot (Phase 8) |
| 13 | Drill-through | Paginated order lines for the same filters and period | §14 |
| 14 | Data coverage | Return days-with-data in each period, % lines with cost, orders excluded by status; warn when the comparison period is empty or partial | §14 "data coverage" |
| 15 | Money type | Decimal in code, rounded to 2 dp at the boundary; JSON as strings for money | Floats lose paise |

## 4. The driver method (documented convention)

Let, per product *i* in a period: `q` = units, `g` = gross price per unit (= gross revenue ÷ q), `d` = line discounts.
Totals: `Q = Σ q`, `G = Σ q·g` (gross revenue), `D = Σ d`, net `N = G − D`. Prior period has subscript 0, current 1.
Let `ḡ0 = G0 / Q0` and `s_i = q_i / Q` (unit share).

For products sold in **both** periods (set C):

- **Volume** = (Q1c − Q0c) × ḡ0c: more or fewer units at the prior average price.
- **Mix** = Q1c × Σ (s1_i − s0_i) × (g0_i − ḡ0c): shift of units towards dearer or cheaper products.
- **Price** = Σ q1_i × (g1_i − g0_i): change in list/billed price on current units.

For products in only **one** period: **New & discontinued** = Σ G1 (new) − Σ G0 (gone).
**Discounts** = −(D1 − D0).

Identity (proved in the unit test): **Volume + Mix + Price + New/discontinued + Discounts = N1 − N0**.

Attribution caveat shown in the UI: these are *arithmetic attributions of a change*, not proof of cause
(a price rise may have *caused* lower units; the decomposition cannot say).

## 5. Alternatives considered and rejected

- **pandas for analytics:** fine for 200k rows, but pulls whole tables into memory and would fork the logic
  from the database. SQL aggregates plus small Python post-processing keep one path.
- **SQL timezone conversion at query time:** differs between SQLite and PostgreSQL. A stored business date is simpler and indexable.
- **Counting returns as negative sales now:** needs a `returns` table (decision D6). Until then returned
  orders are excluded and the response says so.
- **ML/LLM "explanations":** unnecessary and unverifiable at this stage; Phase 8 will *narrate* these numbers, never produce them.

## 6. Test plan (known answers)

1. **Hand-computed fixture:** a tiny workspace with exact expected KPIs for two periods.
2. **Reconciliation:** driver effects sum to the net sales change (tolerance ₹0.01) on the fixture, on the
   8,188-row sample and on random generated data.
3. **Filters:** category/channel/region filters equal an independent SQL query.
4. **Comparison alignment:** previous-period and −364-day ranges; same-length check; weekday check.
5. **Tenancy:** another workspace's data never appears; viewers can read, outsiders get 404.
6. **Edge cases:** empty period, single-day period, products new/discontinued, missing costs, status exclusions, timezone day boundary.

## 7. Sources

- [Coefficient: PVM analysis](https://coefficient.io/cfo-resources/price-volume-mix-analysis-excel)
- [Zebra BI: price-volume-mix bridge](https://zebrabi.com/template/bridge-price-volume-mix/)
- [Achievable: sales variances](https://app.achievable.me/study/cma-part-1/learn/performance-management-cost-and-variance-measures-flexible-budgets-sales-variances-4)
- [Umbrex: retail KPI definitions](https://www.umbrex.com/resources/retail-industry-playbooks/retail-kpi-dashboard-weekly-business-review-playbook/retail-kpi-architecture-and-metric-definitions/)
- [Cin7: retail KPIs](https://cin7.com/blog/retail-kpis)
- [Holistics: period comparison](https://docs.holistics.io/docs/period-comparison)
- [GoodMetrics: date options](https://docs.goodmetrics.io/stats-dashboard/dates)
- [dbt MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow)
- [Lyft: metric semantic layer](https://eng.lyft.com/metric-semantic-layer-how-lyft-governs-and-scales-key-data-definitions-56bee3643c29)
- [Polar Analytics: semantic vs metrics layer](https://www.polaranalytics.com/post/semantic-layer-vs-metrics-layer-vs-data-catalog-what-is-the-difference)
