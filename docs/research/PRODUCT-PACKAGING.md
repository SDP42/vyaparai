# Product packaging and the path to a subscription model

_2026-11-09. Market figures come from blogs and comparison sites that disagree with each other; treat every
price as a hypothesis to test with real owners, not a decision._

## What the market charges (directional)

| Product | What it is | Price seen (disagreeing sources) |
|---|---|---|
| Vyapar | Billing and GST | free tier; about ₹1,999 to ₹3,499 a year per company |
| myBillBook | Billing | about ₹699 to ₹2,899 a year |
| Zoho Books | Accounting | free tier; from about ₹749 a month |
| Busy | Accounting, desktop | from about ₹5,400 a year |
| Khatabook | Credit ledger | free |

Sources: [Vyapar comparison](https://www.vyaparapp.in:443/comparison-with-other-apps), [G2](https://www.g2.com/articles/zoho-books-vs-tally-vs-vyapar),
[Zoho pricing note](https://www.patronaccounting.com/blog/zoho-books-pricing-india-2026).
We are an add-on **decision layer** on top of these, so our price must sit comfortably next to a billing app that
costs a few thousand rupees a year, and be justified by money found.

## Pricing principles (from the research)

- Free tiers must prove value without giving away the upgrade reason; limits that feel like an unlock convert better than walls ([Userpilot](https://userpilot.com/blog/?p=12092), [WinSavvy](https://www.winsavvy.com/?p=72579)).
- SMB freemium conversion is often quoted at about 2 to 10 %; use it only as a planning range, our own cohorts decide ([Inc42](https://inc42.com/?p=21954), [Userpilot](https://userpilot.com/blog/?p=27720)).
- Indian owners weigh software against a junior employee's salary (about ₹15,000 to ₹25,000 a month) and a price copied from the US has failed ([EchAI](https://echai.ventures/gtm/from/evandsouza-com), [Upgrowth](https://upgrowth.in/blog/page/7)). Price in INR, per shop, and show the rupees found.
- Onboarding success and depth of use matter more than the price page.

## Value metric

Charge **per shop (store)**, with usage meters only on things that cost us money. Show the owner a running
"money found" total (margin leaks flagged, win-back revenue measured against the holdout, stock-outs avoided).

## Draft packages (to test, not final)

| | Free: Look | Starter | Growth | Chain |
|---|---|---|---|---|
| Shops, users | 1, 1 | 1, 3 | up to 3, 10 | unlimited |
| Orders imported per month | 500 | 5,000 | 25,000 | high cap |
| Command center, sales, customers, products | yes | yes | yes | yes |
| Data import wizard, quality report | yes | yes | yes | yes |
| Forecasts | top 10 products, 7 days | all products, 14 days | + weather signal, tuning | + custom models |
| Alerts | top 3 | all rules | + custom thresholds | + routing to staff |
| Cost history and margin leaks | summary only | full + price suggestions | full | full |
| Digest | weekly, in app | daily and weekly email | + WhatsApp copy | + per-shop |
| Campaigns | preview only | audience and CSV export | + sending credits, holdout reports | + automation |
| Connectors and scheduled import | no | manual | yes | yes |
| Multi-store, staff roles | no | no | yes | yes |
| Copilot (ask in plain language) | no | no | limited | full |
| Support | community | email | chat | priority |

## Cost drivers that need meters

| Driver | Why | Meter |
|---|---|---|
| Weather data (Open-Meteo paid plan or self-hosted) | free tier is non-commercial | included on Growth and above |
| WhatsApp, SMS, email sending | per-message fees, templates, opt-in records | monthly message credits |
| AI answers (Copilot, later) | per-token cost | monthly questions |
| Forecast and tuning compute | CPU time | forecast runs per day; tuning on higher plans |
| Storage and history | grows with data | months of history kept |

## What to build so packaging works

1. **Entitlements service:** `plans` (features and limits), `subscriptions` (workspace, plan, status, period), `usage` counters, and a
   `require_feature(...)` guard that answers with a clear upgrade message instead of an error.
2. **Metering points:** orders imported, forecast runs, messages sent, AI questions, shops, users.
3. **Upgrade moments:** a leak found while on Free ("₹1,561 lost this month: turn on monitoring"), a forecast that
   would have flagged a stock-out, a campaign ready to send.
4. **Billing:** an Indian provider with recurring payments and UPI autopay, and GST invoices (provider choice and GST treatment to verify).
5. **Trial and onboarding:** import in the first session, a seeded sample shop, a checklist, and a 14-day trial of the next tier.
6. **Success metrics:** activation (data imported within 24 hours), weekly active owners, digest opens, alerts acted on,
   campaigns sent, 90-day retention, upgrade rate by trigger.

## Features still worth adding, in order of willingness to pay

| Priority | Feature | Why owners pay |
|---|---|---|
| 1 | **Inventory and reorder advice** (phase 5) | Stock-outs and dead stock are the biggest cash leaks |
| 2 | **Purchase bills and supplier prices** (15B extension) | True cost without retyping; supplier price tracking |
| 3 | **Connectors and scheduled import** (phase 15) | Removes the manual-import chore that kills retention |
| 4 | **Credit (udhaar) and collections** (phase 13) | Cash stuck with customers; reminders that work |
| 5 | **Campaign sending and measured uplift** (3B C2-C4) | Directly attributable revenue, easy to justify a price |
| 6 | **Mobile app and Hinglish/Hindi** (phase 18) | Owners live on their phones |
| 7 | **Multi-store and staff** (phase 17) | The natural upgrade for growing shops |
| 8 | **Pricing and promotion advisor** (phase 16) | Which discounts paid off |
| 9 | **Copilot** (phase 8) | Ask in plain language; strong demo, real running cost |
| 10 | **Goals and benchmarks** (phase 19) | Retention hook once peers exist |
| Later | GST reports export, loyalty points, barcode and POS integration, supplier ordering, online-store imports | Breadth and lock-in |

## Open decisions

- Final tier boundaries and prices (test with owners; start with a free tier and one paid tier).
- Billing provider and GST handling.
- Whether to price per shop or per seat for chains.
- How much of the weather and messaging cost is absorbed versus metered.
