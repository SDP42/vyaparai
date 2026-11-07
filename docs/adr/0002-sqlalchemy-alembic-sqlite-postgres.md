# 0002 · SQLAlchemy 2.0 + Alembic; SQLite in dev, PostgreSQL in prod

- **Date:** 2026-11-07 · **Status:** Accepted

**Context.** The blueprint asks for no Docker requirement locally, but a production-grade relational store.

**Decision.** SQLAlchemy 2.0 typed ORM with portable types (`Uuid`, `Numeric`, `JSON`, non-native
enums). Alembic migrations with batch mode for SQLite. Settings refuse SQLite when `APP_ENV=production`.
A test asserts that `alembic upgrade head` produces exactly the schema the models describe.

**Consequences.** Zero-setup local development. Some PostgreSQL-only features (RLS, partial
indexes, `JSONB` operators) must be added behind dialect checks.
