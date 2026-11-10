# Pricing and promotion advisor

Answers two questions from the shop's own sales: **did my discounts pay off?** and **which price moves look safe?**

## Discounts

For each product over the last 180 days:

- A **discount day** is a day when at least 3% of that product's gross sales were discounted. A **normal day** is under 1% (days with no sales count, so the baseline is true average demand).
- The baseline is the product's normal-day average **for each weekday**, so a Saturday offer is compared with a normal Saturday.
- **Lift** = units on discount days / units normal days of the same weekdays would have sold - 1.
- **Profit effect** = profit on discount days minus the profit the baseline units would have earned at the normal margin. Profit is after the discount.
- Both come with a bootstrap 95% range over the discount days. **Paid off** only if the whole profit range is above zero; **lost money** only if it is entirely below; otherwise **cannot tell**.
- A product needs at least 3 discount days and 28 normal days, and a recorded cost for profit to be judged.

## Price moves

- A move is a lasting change of at least 3% in the product's weekly average net price, stable for two weeks, with two stable weeks before.
- Units in the two weeks after are compared with the two weeks before, giving a rough elasticity (% change in units per % change in price). Rows with under 20 units a week are marked "few sales".
- **Suggestions** are one-week trials of +3% on products with a margin under 20% and a positive expected effect. They use the product's own measured response when there is one, otherwise a stated range of assumed responses (shoppers losing 0.5 to 1.5% of units per 1% price rise), and the page says which.
- Suggestions and losing discounts feed the recommendations ("Stop discounting X", "Try a price for Y"), and the Ask page answers "did my discounts work?".

## Limits

- It compares like weekdays but cannot isolate a discount from a festival, the weather or a stock-out on the same days. Treat "lost money" as a reason to test, not proof.
- One shop has few price changes and plenty of noise; elasticities are rough.
- No competitor prices, no stock effects, and no cross-product effects (a discount that moves customers between products looks like a lift on one and a drop on another).
- Tested on planted data (a discount with a real lift, one with none, and a price rise with no volume loss); not yet measured on real shop history.

## API

`GET /workspaces/{id}/pricing/discounts` · `GET /workspaces/{id}/pricing/moves`
