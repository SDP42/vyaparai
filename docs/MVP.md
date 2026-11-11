# MVP release checklist

The MVP journey (blueprint §03): create a workspace, upload a retail file, map columns, review
validation, see trusted numbers, investigate sales, forecast, get alerts and a daily digest, plan
stock, and bring in a teammate. `apps/api/tests/test_mvp_journey.py` runs that path as one signed-in
user, through the cookie session, on every test run.

## Ready

| Area | State |
|---|---|
| Sign-in | 15-minute access token in memory, rotating HttpOnly refresh cookie, reuse detection, logout everywhere, login and sign-up throttling (shared through Redis when configured) |
| Team | Roles, five jobs (personas) with their own pages, assistant remit and data guards, one-time invitation links, last-owner protection, audit trail |
| Data in | CSV/Excel upload, remembered mappings, validation with error file, idempotent import, connected sheet links, scheduled imports, optional cashier column |
| Numbers | Versioned metric layer, comparisons, price-volume-mix drivers, drill-through |
| Customers, products, staff | RFM and segments, cohorts, ABC, margins, basket pairs, sales by cashier |
| Forecasts | Many models, honest backtests, intervals, festival and weather signals, registry with ship gate |
| Decisions | Alerts, daily digest, stock advice, margin leaks, pricing advice, goals, ranked next steps, saved PDF/CSV reports |
| Credit and bills | Udhaar ledger with ageing and reminder drafts; supplier bills read by OCR and checked by a person |
| Campaigns | Consent and opt-out, person-sent outbox with a daily cap, holdout design and uplift |
| Language | Assistant and reminders in English, Hindi and Hinglish; reviews; document search; speech to text on your own server |
| Phones | Installable PWA, offline reading, phone layout with a bottom bar |
| Operations | Docker Compose stack, backup and restore scripts, runbook, hardening middleware, production settings guards |
| Licences | Audited, enforced by a test ([LICENSES.md](LICENSES.md)) |

## Known gaps before a public launch

- **Not tested with real shopkeepers.** Voice, personas, wording and layouts have only been exercised by the team and
  by synthetic speech. Accuracy figures for reviews, OCR, search, pricing and recommendations come from small
  self-written sets.
- **Deployment not rehearsed.** The Docker stack, backups and restore are written and tested in parts, not run on a
  real server. Voice needs about 2 GB of free memory with the default `medium` model.
- **Language.** Hinglish and Hindi wording has not had a native-speaker review; page bodies other than the assistant,
  the credit pages and Next steps are English. PDF reports are English.
- **No email delivery of invitations:** the owner shares the link. Digest email needs SMTP settings.
- **Not tried on a real phone or with a screen reader.**
- **Open decisions:** the project licence, and a trademark check on the name "Vyapar".
- **No outside review:** no penetration test.

## Release gate

1. `uv run pytest`, `ruff check`, `mypy app` and `tsc --noEmit` pass.
2. The journey test passes against a clean database (`alembic upgrade head`).
3. Production settings validate: a real `SECRET_KEY`, PostgreSQL, HTTPS-only origins.
