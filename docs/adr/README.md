# Architecture decision records

Short, dated records of significant decisions. Format: context → decision → consequences.
Add a new file `NNNN-title.md`; never rewrite an accepted ADR, supersede it instead.

| # | Title | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with FastAPI | Accepted |
| [0002](0002-sqlalchemy-alembic-sqlite-postgres.md) | SQLAlchemy 2.0 + Alembic; SQLite dev, PostgreSQL prod | Accepted |
| [0003](0003-workspace-tenancy.md) | Workspace-as-tenant with 404-on-non-member | Accepted |
| [0004](0004-jwt-bearer-auth.md) | Short-lived JWT bearer tokens for the MVP | Accepted |
| [0005](0005-frontend-stack-and-visual-language.md) | Next.js + GSAP + Lenis (R3F removed), "Bahi-Khata" visual language | Accepted (amended) |
| [0006](0006-metric-layer.md) | One metric layer, stored business date, exact-sum drivers | Accepted |
| [0007](0007-ml-approach.md) | ML approach: model portfolio, one protocol, ship gate | Accepted |
| [0008](0008-benchmark-data.md) | Benchmark data: synthetic in the repo, real accuracy on real shops | Accepted |
