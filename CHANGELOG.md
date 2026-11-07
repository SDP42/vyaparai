# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **API:** FastAPI app factory, typed settings with production guards, JSON logging, request IDs,
  uniform error envelope, liveness/readiness probes.
- **API:** Models for users, workspaces, memberships, datasets, jobs, audit logs, products,
  customers, orders and order items. Initial Alembic migration.
- **API:** Register/login/me with Argon2id + JWT. Workspace CRUD, members, RBAC, audit log,
  dataset/job read endpoints.
- **API:** 29 tests covering health, auth, tenant isolation, RBAC, security and migration drift.
- **Web:** Next.js app with the "Bahi-Khata" design tokens and fonts.
- **Web:** Landing page with a 3D shattering-word hero, pinned horizontal story, zoom-through
  product reveal, bento features, ledger marquee, principles and CTA.
- **Web:** Persona sign-in page with a colour-flood transition, and a persona-aware demo dashboard.
- **Docs:** README, PHASES, ROADMAP, ARCHITECTURE, API, DATA_DICTIONARY, METRICS, THREAT_MODEL,
  DESIGN_SYSTEM, RESEARCH, ADRs 0001–0005, CONTRIBUTING, DEVLOG.
- **CI:** GitHub Actions for API lint/type/test and web type-check/build.
