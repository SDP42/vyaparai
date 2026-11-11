# Recommendations and reports

## Recommendations

Suggested actions from the product's own signals, ranked, with reasons and an honest impact range. Nothing happens unless the owner chooses; approving records the decision and keeps the item on a to-do list, and the action itself is done by a person on the linked page.

| Kind | Signal | Impact estimate |
|---|---|---|
| Order now | Stock runs out before a new order can arrive | Days short of delivery x daily sales x selling price (from your numbers; needs prices) |
| Raise a price | Cost rose and the price did not follow (margin leak) | The margin lost in the last 28 days, 50-100% recoverable |
| Pass on a supplier rise | A confirmed bill shows a 5%+ increase | Not estimated (needs monthly units) |
| Collect udhaar | Dues older than 30 days | Dues x 30-70% (**assumed**) |
| Clear dead stock | Cash in stock that has not sold | Cash x 20-50% (**assumed**) |
| Win back regulars | Regulars quiet for 45 days | Count x a typical month's spend x 10-35% (**assumed**) |
| Festival stock | An event within 21 days and products at risk | Daily sales x event days x 10-40% uplift (**assumed**) |

Every item shows its basis and assumptions; assumptions that are not measured on the shop's own data are marked "Includes an assumption". Where the data cannot support a number the impact is left empty, counted separately, and the item ranks last.

**Ranking**: `expected impact x confidence weight / effort weight` (confidence high 1.0, medium 0.7, low 0.4; effort S 1.0, M 1.6, L 2.5).

**Lifecycle**: proposed, approved ("I will do this"), done; or dismissed. A dismissed item is not proposed again while its cause remains. An item whose cause has gone becomes "no longer needed". A signal that fails to read never hides the others or marks existing items stale. Each decision is audited.

**Outcomes**: when an item is marked done, the number it should move is saved (udhaar older than 30 days, cash in dead stock, regulars gone quiet, products about to run out, margin leaks). Two weeks later the same number is read again and shown as improved, no change or worse, with a reminder that other things changed too. Items with no single honest number (festival stock, supplier price changes) say "not measurable".

**Limits**: the recovery and uplift shares are general assumptions, not measured on any shop; they are shown as ranges so the owner can discount them. Impacts of different items can overlap, so the total is "if you did everything", not a forecast.

## Reports

A business summary for a period: key measures with change, what changed (price, volume, mix, discounts), top and lowest products, customers, stock, udhaar, the forecast with its past error, suggested actions, and notes and limits. Saved as a frozen snapshot, rendered as PDF (reportlab) or a sectioned CSV.

**Limits**: PDFs are set in Noto Sans so amounts print with ₹, but stay English: the PDF library cannot shape Devanagari (vowel signs and conjuncts would come out wrong), so Hindi is not attempted. The snapshot stores numbers, not the charts' source data beyond the net-sales trend.

## API

`POST /workspaces/{id}/recommendations/refresh` · `GET .../recommendations?status=` · `GET .../recommendations/summary` · `POST .../recommendations/{id}/{approve|dismiss|done|reopen}` · `POST .../reports` · `GET .../reports` · `GET .../reports/{id}` · `GET .../reports/{id}/pdf` · `GET .../reports/{id}/csv` · `DELETE .../reports/{id}`
