# Alerts and anomalies (Phase 14)

## Method

Explicit rules with fixed thresholds, so an owner can see exactly why something fired. No learned
model: with weeks of history per shop a black box would be wrong often and impossible to explain.

- **Sales drop or spike (a day):** compare the day with the **same weekday over the previous eight weeks**
  (a Sunday against Sundays). Baseline = median; spread = MAD × 1.4826 (a robust standard deviation).
  Fire when the day is at least 30 % below the baseline (45 % is high) **and** the robust z-score is at
  most −2.5, or the MAD is zero. Spikes (+40 %) are information only. Needs at least 4 comparable weeks and
  a baseline of at least ₹200, so tiny shops do not fire on noise.
- **Sales drop (a week):** the last 7 days against the mean of the four weeks before: −15 % medium, −25 % high.
- **Margin leak:** from the cost history ([COST-TRACKING.md](COST-TRACKING.md)). High when the loss is at
  least ₹500 in the window or the margin fell 5 points or more.
- **Discount creep:** discount rate over the last 7 days against the 4 weeks before: +3 points medium, +5 high.
- **Product stopped:** sold on at least 8 of the 28 days before the last week and nothing in the last 7.
- **Lapsed regulars:** five or more customers with two or more orders and no order for 45 days (ten or more is medium).
- **Data nudges:** most sales have no cost; latest sales are more than 3 days old.

## Lifecycle

Alerts are keyed by rule and subject. Recomputing opens new problems, **resolves** ones that stopped being
true, reopens a resolved one if the problem returns (no duplicates), and keeps a **dismissed** one hidden while
it lasts. Open counts feed the sidebar badge, and the highest-priority high alert becomes the digest's action.

## Limits

- Closed days, holidays and festivals look like drops; the same-weekday baseline softens but does not remove this.
- Needs about five weeks of history before the sales rules can fire.
- Stock-out risk and "forecast missed" alerts need inventory data and a longer forecast track record (later phases).
- Alerts show in the app and the digest; push by WhatsApp or SMS comes with campaign sending.
- Thresholds are our starting point. They should be tuned from which alerts owners dismiss and which they act on.
