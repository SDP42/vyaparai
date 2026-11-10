# MVP release checklist

The MVP journey (blueprint §03): create a workspace, upload a retail file, map columns, review
validation, see trusted numbers, investigate sales, forecast, get alerts and a daily digest, plan
stock, and bring in a teammate. `apps/api/tests/test_mvp_journey.py` runs that path as one signed-in
user, through the cookie session, on every test run.

## Ready

| Area | State |
|---|---|
| Sign-in | 15-minute access token in memory, rotating HttpOnly refresh cookie, reuse detection, logout everywhere, login and sign-up throttling |
| Team | Roles, one-time invitation links, last-owner protection, audit trail |
| Data in | CSV/Excel upload, remembered mappings, validation with error file, idempotent import, connected sheet links, scheduled imports |
| Numbers | Versioned metric layer, comparisons, price-volume-mix drivers, drill-through |
| Customers, products | RFM and segments, cohorts, ABC, margins, basket pairs |
| Forecasts | Many models, honest backtests, intervals, festival and weather signals, registry with ship gate |
| Decisions | Alerts, daily digest, stock advice, margin leaks, campaigns (draft and measure) |
| Licences | Audited, enforced by a test ([LICENSES.md](LICENSES.md)) |

## Known gaps before a public launch

- Throttle counters are in memory (one process). Use Redis before running several workers (Phase 11).
- No email delivery of invitations: the owner shares the link. Digest email needs SMTP settings.
- The typed API client is still hand-written; generating it from OpenAPI is open (F2).
- The persona demo still exists beside real accounts (decision F-C).
- No hosted deployment, backups or runbook yet (Phase 11).
- Campaign sending and uplift measurement (3B C2-C4), Copilot, reviews and documents are later phases.

## Release gate

1. `uv run pytest`, `ruff check`, `mypy app` and `tsc --noEmit` pass.
2. The journey test passes against a clean database (`alembic upgrade head`).
3. Production settings validate: a real `SECRET_KEY`, PostgreSQL, HTTPS-only origins.
