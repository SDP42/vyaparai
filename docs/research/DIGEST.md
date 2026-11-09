# Owner digest (Phase 12)

_2026-11-09. Sources are blogs and report templates, so treat them as direction, not proof._

## Why

Owners abandon dashboards they must remember to open ([analytics fatigue](https://analytify.io/how-to-fix-analytics-fatigue/)).
A short message that arrives on its own is the retention feature. Phase 12 builds it.

## What goes in it

Retail daily reports track revenue, transactions and customer trends, and flag discounts, stock gaps and
unusual drops; they end with takeaways and a short plan ([sales report template](https://solink.com/resources/industry-insights/retail-daily-sales-report-template/),
[daily reports for small business](https://gse.kz/en/blog/bi-small-business-10-daily-reports)). Comparing orders with sales
reveals basket or price slipping. We found nothing on WhatsApp length or timing, so length is our own choice:
under about 900 characters, readable in half a minute.

| Part | Rule |
|---|---|
| Three numbers | Sales, orders, and margin (average bill when fewer than 80 % of sales have a cost). Compared with the same weekday last week (daily) or the week before (weekly) |
| One action | The first that applies: message lapsed regulars (3 or more), stock up on a rising product (+15 % or more, 10 or more units), go easy on a falling one (−20 % or more), look into a sales drop (−10 % or worse), add missing costs (under 60 % coverage). Otherwise "nothing urgent" |
| Also | Up to two more actions as one line |
| Look ahead | The next 14 days from the latest forecast, only if it covers the digest's last day |
| Honesty notes | Data is out of date; margin hidden because costs are missing |

## Privacy

Aggregates and product names only. No customer names, IDs or phone numbers appear in a digest, so an email
sent to the wrong person leaks no customer data. Recipients are set by an owner or admin, at most five.

## Delivery

- **Email** through any SMTP server: set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
  and `APP_URL` in the API environment. Until `SMTP_HOST` is set, summaries are stored and can be copied.
- **Schedule:** run `uv run python -m app.digest_runner` from cron every 15 minutes. Each digest goes out once
  per local day, at or after the chosen hour, so running it often is safe.
- **WhatsApp:** not automated. The page offers the text to copy. Sending through the WhatsApp Business API
  needs templates, opt-in records and a provider, so it belongs with campaign sending (CAMPAIGNS-PLAN, C3).

## Limits

- Data is only as fresh as the last import; the digest says how old it is. Connectors (phase 15) fix this.
- Weekday comparison uses one day last week, which a holiday can distort; the weekly digest is steadier.
- The runner is a command, not a built-in scheduler, so something must call it.
