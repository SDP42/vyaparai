# Why a shop owner would use Vyapar AI

Research notes, 2026-11-08. Sources are mostly vendor blogs, so they show what the market sells, not
proof of what owners want most. Treat the conclusions as hypotheses to test with real owners.

## What owners already have

- **Billing and GST apps** (Vyapar, Busy, Swipe, VasyERP, Accountune): GST invoices, WhatsApp bill
  sharing, low-stock alerts, barcode billing, multi-branch.
- **Udhaar ledgers** (Khatabook, OkCredit, BizBahi): customer credit tracking and payment reminders.
- Sources: [billing software roundup](https://itsupplychain.com/10-best-billing-software-for-retail-shops-in-india-2026/),
  [Vyapar reviews](https://g2.com/products/vyapar/reviews?page=2),
  [WhatsApp billing tools](https://getswipe.in/blog/collections/8-best-tools-to-send-invoices-through-whatsapp-in-india),
  [OkCredit](https://okcredit.in/llms.txt).

## The gap

These tools **record** what happened. They rarely tell the owner **what to do next**. We found little
evidence of loyalty, win-back, forecasting or "why did sales change" features for small retailers.
Our edge is decision support on top of the data the owner already has, not another billing app.

## Why owners abandon analytics (and what we do about it)

[Analytics fatigue](https://analytify.io/how-to-fix-analytics-fatigue/) and
[BI adoption barriers](https://dashboardfox-website.pages.dev/blog/top-reasons-small-businesses-avoid-business-intelligence-software):
too many metrics, stale data, no time, hard to use. So:

| Risk | Product answer |
|---|---|
| Dashboards go unopened | **Push** a short daily/weekly digest with 3 numbers and one action (WhatsApp or email) |
| Too many metrics | Lead with decisions ("reorder these 5", "call these 12 customers"), not charts |
| Data is stale because entry is manual | Connectors to billing apps and POS exports, scheduled imports, so no CSV chores |
| Owners do not trust numbers | Every figure links to its definition and the rows behind it (already built) |
| English-only, desktop-only | Hinglish/Hindi, phone-first, installable |

## Why they would use us instead of doing it themselves in Excel

1. **Time:** the weekly review that takes an evening becomes a 2-minute digest.
2. **Money found:** slow stock tied up in cash, products sold at a loss after discounts, regulars who stopped coming, stock-outs on best sellers. Each is a rupee figure, not an opinion.
3. **Trust:** same definitions every time, with evidence, and uncertainty shown honestly.
4. **Action:** one tap to a drafted reorder list or a drafted customer message.

## New phases this adds

| Phase | Name | Why an owner cares |
|---|---|---|
| 12 | Daily and weekly digest (push) | The app comes to them; this is the retention feature |
| 13 | Cash and credit (udhaar) intelligence | Money stuck with customers and suppliers; who to remind, expected collection |
| 14 | Alerts and anomalies | Sales drop, margin leak, stock-out risk, unusual discounts, flagged within a day |
| 15 | Connectors and scheduled imports | Billing app exports, Tally/Zoho/Busy files, POS drop folder, so data stays fresh |
| 16 | Pricing and promotion advisor | Which discount paid off, safe price changes, festive-season planning |
| 17 | Multi-store and staff | Compare shops, per-store targets, staff roles and activity |
| 18 | Mobile-first and language | Installable PWA, Hinglish/Hindi UI, big-tap layouts, offline read |
| 19 | Benchmarks and goals | Targets and progress, anonymised peer ranges once there are enough shops |
| 3B | Campaigns and retention automation | Already planned: [plan](CAMPAIGNS-PLAN.md) |

Order recommendation after Phase 4: 3B (C1) → 12 → 14 → 5 → 13 → 15 → 16 → 18 → 17 → 19, then 6–11.
Digest and alerts come early because they decide whether owners come back.
