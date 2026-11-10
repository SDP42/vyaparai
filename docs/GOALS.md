# Goals and benchmarks

## Goals

Set a target for the month or week (or any custom period up to a year). Measures: net sales, orders, gross profit (reach this much), gross margin and average order value (reach at least this), discount rate and udhaar older than 30 days (keep under this).

For measures that add up over the period (sales, orders, profit):

- **Pace** = progress against the target divided by the share of the period gone (1.0 is exactly on pace). **Needed a day** = what is left divided by the days left.
- **Likely finish** is a range, not a promise: so far plus a simulated rest of the period drawn from the last 28 days of actual daily values (1,000 resamples; the 10th to 90th percentile).
- **Status**: *on track* if even the low end reaches the target, *at risk* if the target sits inside the range, *behind* if even the high end falls short, *reached* once the value is there, and *met* or *missed* when the period is over. Trouble is listed first.

For rate measures and udhaar the measure is compared with the target as it stands.

Goals behind or at risk appear as recommendations ("you need ₹X a day; the last four weeks averaged ₹Y") with no invented impact, in the store comparison as a flag, and in the Ask page ("am I on track?").

## Benchmarks

**There are no peer benchmarks.** Comparing a shop with similar shops needs data from many shops, shared with their agreement and anonymised; the product has none and does not collect any. What the Goals page offers instead are benchmarks from the shop's *own* history: the same measure over the last 12 completed months or weeks, with a usual period (median), the best, and a stretch (top quarter), each one click from becoming a target. At least three past periods are needed.

A peer network would need, at minimum: explicit opt-in, a minimum of about ten shops per comparison group, only medians and ranges shown, no shop identifiable, and a way to leave and delete. That is not built.

## Limits

- The projection assumes the next days look like the last 28; a festival, a closure or a stock-out in that window will break it.
- Gross profit counts only sales with a recorded cost.
- Goals are per shop; staff-level targets are not possible without a cashier on each sale (see [STORES](STORES.md)).
- Tested on planted data with known answers (steady and noisy sales, finished and in-progress periods); not on real shop history.

## API

`GET /workspaces/{id}/goals/metrics` · `GET .../goals` · `POST .../goals` · `GET .../goals/benchmarks?metric=&period=` · `DELETE .../goals/{id}` (closes it)
