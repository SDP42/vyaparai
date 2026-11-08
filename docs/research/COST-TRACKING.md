# Knowing the true cost of a product

Question from the owner: prices keep changing, so how do we know the real cost? Is there a free API,
or must the shopkeeper update prices by hand?

## Short answer

There is **no free API for what a particular shop pays its supplier**. That price depends on the
supplier, the scheme, the quantity and the day, and only the shop's own purchase bills hold it.
A free government API does exist for **fresh produce market prices**, but it is a reference, not the
shop's cost. So the design is: *capture cost from documents the owner already has, and make manual
updates the fallback, not the main route.*

## Sources of cost, best first

| Source | How | Notes |
|---|---|---|
| Purchase bills | Import supplier invoices/purchase register (CSV/Excel now, billing-app connectors in Phase 15, bill photo/PDF extraction later) | Most accurate; gives a dated cost per batch |
| Cost column on sales export | Already supported: each line stores a `unit_cost_snapshot` | Cost is frozen on the bill, so history stays correct when prices move |
| Billing-app purchase price | Billing apps already hold a purchase price per item; the connector reads it | No retyping |
| Quick manual update | One screen: SKU, new cost, effective date; bulk paste from a sheet | Fallback; shows "cost last updated N days ago" |
| Market price reference | Agmarknet daily mandi prices via data.gov.in (free key) for staples and produce | Reference only, shows direction; not used as cost |

Sources: [Agmarknet dataset on data.gov.in](https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi),
[datagovindia wrapper](https://pypi.org/project/datagovindia/0.4). A free key is needed; check the
dataset page for the exact resource ID before building.

## How the product treats a changing cost

1. **Cost history table**: `product_costs(product, cost, effective_from, source)`. Never overwritten.
2. **Which cost applies**: the cost on each sale line is the one valid on the bill date (what we do today). For stock valuation and reorder advice we use the latest purchase cost, with weighted average as an option.
3. **Margin leak alert** (Phase 14): when a cost rises and the selling price has not, show the products now earning below the margin floor, and what price restores it.
4. **Stale-cost warning**: margin figures already carry cost coverage; add "cost older than 60 days" so owners know when to refresh.
5. **Supplier price changes** between two purchase bills are flagged automatically ("Mustard Oil cost up 7% since 10 Sep").

## Sample data

The generator now includes cost changes on six products (oil, sugar, dal, ghee, eggs), so margin and
cost-change features can be built and tested against moving costs.

## Open decisions

- Costing method for valuation: last purchase cost (simple, default) or weighted average.
- Whether to include the Agmarknet reference in the first version (needs an API key and a mapping from our SKUs to commodity names).
- Bill photo/PDF extraction: a later add-on that needs an LLM provider (decision D3).
