# Inventory and reorder advice (Phase 5)

## What it answers

How long will today's stock last, what should I order and how much, and where is cash stuck on the shelf.

## Inputs

- **Stock counts** uploaded as a CSV (SKU, stock, optional date, lead time, pack size) or typed per product. Snapshots are dated and kept, so history is not lost. Headers are matched by common names (Item Code, Closing Stock and so on); bad rows are reported, not silently dropped.
- **Per product:** delivery time in days (default 3), pack size (default 1), safety days (default 2).
- **The forecast** (p50 and p90 for each of the next 14 days). Without one, the product's last four weeks of sales are used and the row says so.

## Rules

1. **Stock today** = latest snapshot minus the units sold since its date, never below zero.
2. **Days of cover** = how many days that stock lasts against the daily forecast. After the 14-day forecast the daily rate is held flat (capped at 60 days).
3. **Order now** when cover is shorter than the delivery time (it runs out before an order placed today could arrive).
4. **Order soon** when cover is at most delivery time plus the days between orders (default 7).
5. **Order quantity** covers delivery time plus the review period at a demand level between the median and the p90 forecast: lean 0, balanced 0.5, cautious 1, then rounded up to whole packs.
6. **Too much** when cover exceeds 45 days; **not selling** when nothing sold in 30 days with stock on the shelf.
7. **Cash tied up** = stock today times the latest unit cost; **excess cash** = the part above 45 days of demand.

Hand-checked example (lead 3, review 7, p50 10 a day, p90 14): 25 on hand is urgent and orders 95; 80 on hand is "order soon" and orders 40 (48 with packs of 12).

## Where it shows up

Alerts (stock-out risk, products to order, dead stock), the owner digest (a stock-out becomes "Do this"), and the Festivals page (products a coming festival touches whose stock may not last).

## Limits

- Stock is only as current as the last count; sales since the count are subtracted, but returns, theft and wastage are not.
- Orders already on the way are not known, so the suggestion may overlap them.
- One lead time per product, not per supplier; no supplier minimum order values yet.
- The forecast assumes no promotions; a planned offer can raise demand.
- Not tied to a purchase-bill import yet (phase 15B follow-up).
