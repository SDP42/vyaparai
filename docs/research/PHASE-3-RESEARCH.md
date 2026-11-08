# Phase 3 research: customer and product intelligence

_Date: 2026-11-08 · Blueprint §14 (customer segment filter), §34 Week 6 (RFM, product contribution, cohorts)_

Phase 3 delivers *descriptive* analytics before any predictive model: who the customers are, who is
slipping away, which products earn their shelf space, and what is bought together. Everything is
deterministic and explainable (blueprint: "interpretable segment rules").

## 1. What I looked up

| Topic | Finding | Source |
|---|---|---|
| RFM scoring | Rank customers on recency, frequency and monetary value and split into **five equal buckets** scored 1–5; the most recent quintile scores 5. Cut-offs are relative to your own customer base; quintiles create arbitrary boundaries, and skewed revenue is often log-transformed (a rank-based score is unaffected by a monotone transform) | [Ecosire RFM guide](https://ecosire.com/blog/customer-rfm-analysis-segmentation-ltv), [Bloomreach RFM](https://documentation.bloomreach.com/engagement/docs/rfm-segmentation-explained), [MetricGate](https://metricgate.com/docs/rfm-segmentation/) |
| RFM segments | Names agree (Champions, Loyal, At Risk, Hibernating, Can't Lose Them), **cut-offs vary by vendor**: e.g. Champions = R, F, M all 4–5; At Risk = R 1–2 with F and M 3–5; Hibernating = low on all | [Blueshift RFM](https://help.blueshift.com/hc/en-us/articles/41011474524179-RFM-scores-segments), [Skypoint](https://docs.skypoint.ai/rfmmodel-explore) |
| Cohort retention | Assign each customer to the month of their **first purchase**; count unique customers who buy in each later month; divide by cohort size. Read across a row for one cohort, down a column to compare cohorts at the same age | [Hex cohort analysis](https://hex.tech/blog/cohort-analysis/), [Shopify cohort retention](https://www.shopify.com/blog/cohort-retention-analysis) |
| Repeat purchase rate | No source gives an exact formula; the standard one (my knowledge, not from the results) is customers with ≥ 2 orders ÷ customers | — |
| Basket analysis | **Support** = share of orders containing the itemset; **confidence** = P(B given A); **lift** = confidence ÷ support(B); lift 1 = independent, > 1 positive association, < 1 substitution. No universal minimum support; it depends on data size | [Towards Data Science: market basket analysis](https://towardsdatascience.com/a-gentle-introduction-on-market-basket-analysis-association-rules-fa4b986a40ce), [Select Statistics](https://select-statistics.co.uk/?p=721) |
| Product portfolio | Menu-engineering matrix: plot items by **popularity** and **profitability**; above average on both = Stars, popular but low margin = Plowhorses, unpopular but high margin = Puzzles, low on both = Dogs. Sources disagree on cut-offs (menu average vs fixed). Suggested actions: protect Stars, attack the cost of Plowhorses, promote Puzzles, remove most Dogs | [Toast menu engineering](https://pos.toasttab.com/restaurant-management/restaurant-menu-engineering), [Loaded](https://www.loadedhub.com/resources/menu-engineering-matrix-restaurant) |
| ABC (Pareto) | **Not found** in my searches. The usual convention (A = first ~80 % of sales, B = next ~15 %, C = last ~5 %) is from my own knowledge; treat the cut-offs as a stated convention | — |

## 2. Decisions

### 2.1 Customers
| # | Decision | Why |
|---|---|---|
| 1 | Only customers with an ID are analysed; **walk-in orders are excluded** and their share is reported | They cannot be tracked over time |
| 2 | **As-of date** = the period's end date; R = days from the customer's last completed order to the as-of date | Matches the rest of the app's period model; supports "as of last month" |
| 3 | F = completed orders and M = net sales in a **lookback window** (default 365 days, capped by available data) | Bounds the history; configurable |
| 4 | Scores 1–5 by **tie-fair percentile rank** (`floor(percentile × 5) + 1`; recency reversed). Fewer than 10 customers → warn that segments are unreliable | Rank scoring is invariant to skew; ties must not split arbitrarily |
| 5 | **Named segments** by first-match rules on R, F (and M for Can't lose): Champions R≥4 ∧ F≥4 · Loyal R≥3 ∧ F≥3 · New (1 order, first order ≤ 30 days ago) · Promising R≥4 ∧ F≤2 · Needs attention R=3 ∧ F≤2 · Can't lose R≤2 ∧ F≥4 ∧ M≥4 · At risk R≤2 ∧ F≥3 · Hibernating R≤2 ∧ F≤2. Every (R, F) pair is covered | Vendor cut-offs vary, so ours are explicit, documented and tested |
| 6 | An **absolute status** independent of the relative scores: Active (≤ 30 days since last order), Cooling (31–44), Lapsed (≥ 45; configurable). "Lapsed regulars" = lapsed with ≥ 2 orders | Relative quintiles always put someone in the bottom bucket; a shopkeeper also needs "who has actually gone quiet" |
| 7 | **Repeat rate** = customers with ≥ 2 orders ÷ customers; **revenue per customer**; **top-10 % share** of net sales (concentration) | Standard retail health measures |
| 8 | **Cohorts** by first-order month, retention by months since first order, customers only | §1 |

### 2.2 Products
| # | Decision | Why |
|---|---|---|
| 9 | Per product and category: units, net sales, discount rate, **margin ₹ and %** (only lines with a cost), cost coverage, change vs comparison | Blueprint §34 |
| 10 | **ABC class** by cumulative share of net sales: A to 80 %, B to 95 %, C the rest | Stated convention (§1) |
| 11 | **Portfolio quadrant** (menu-engineering adapted to retail): popularity = units ≥ the median product; profitability = margin % ≥ the overall margin %; Stars / Workhorses / Puzzles / Dogs; products with no cost are "Unknown" | Sources agree on the four quadrants, not the cut-offs, so ours are stated |
| 12 | **Discount analysis**: discount rate by product/category, share of lines sold at a discount, flag *discount-heavy* (rate ≥ 2 × overall and ≥ 3 %) | "Discount impact" (§14) |
| 13 | **Basket pairs** on completed orders in the period: support, confidence both ways, lift; only pairs with ≥ N orders (default 5) are shown; top products capped to bound the work; wording is "bought together", never causal | Lift is unstable on rare items |
| 14 | **CSV exports** for the customer list and the product table | Blueprint §34 |

### 2.3 Out of scope for Phase 3
Churn *prediction* and k-means segmentation (Phase 4 ML platform; MODELS.md); returns (decision D6); customer names/phones (minimal-PII design).

## 3. Test plan
1. Hand-computed fixture of ~12 customers: exact R/F/M, scores, segments, statuses, repeat rate, concentration.
2. Rule coverage: every (R, F) pair maps to exactly one segment.
3. Tie handling and tiny customer bases; walk-ins excluded.
4. Cohort matrix hand-computed (including a customer who returns after a gap).
5. Product margin, ABC cut-offs, quadrants, discount flags on a fixture; products without cost.
6. Basket support/confidence/lift hand-computed; minimum-orders filter.
7. CSV exports parse and match the JSON; tenancy and viewer access.
8. Reconciliation on the 8,188-row sample (segment counts sum to customers; ABC shares sum to 100 %).
