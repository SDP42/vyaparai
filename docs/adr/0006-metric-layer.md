# 0006 · One metric layer with a stored business date

- **Date:** 2026-11-08 · **Status:** Accepted

**Context.** The dashboard, the API and the future Copilot must never disagree about a number
(blueprint §13). Day buckets must match the shopkeeper's day, and SQLite (dev) and PostgreSQL (prod)
handle timezones differently.

**Decision.**
1. All analytics go through one engine (`services/analytics/`) fed by a versioned registry (`metrics.py`).
   Every response returns the metric versions, period, filters, currency and data freshness.
2. Orders store a **business date** (workspace-timezone calendar day) at import; analytics bucket by it.
3. Money is `Decimal`; driver analysis uses a documented price–volume–mix convention with an
   exact-sum identity enforced by tests.
4. Eligibility is explicit: only `completed` orders count; excluded orders are reported, not hidden.

**Consequences.** Simple, fast, dialect-independent queries and one place to change a definition (bump
its version). Changing a workspace's timezone requires recomputing business dates (a future admin task).
Per-metric version pinning is out of scope. See [research/PHASE-2-RESEARCH.md](../research/PHASE-2-RESEARCH.md).
