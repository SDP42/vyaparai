# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **API:** Phase 1 ingestion: upload (CSV/XLSX), inspection, mapping suggestions, validation,
  error CSV, background import job, data summary. Migration `56799aeb0cfc`. 25 new tests.
- **Web:** account creation, workspace setup and a 4-step import wizard on `/app`.
- **Web:** scroll-driven, reversible key-and-lock opening with depth of field, bloom, interior goods,
  synced sounds and a hand-off into the landing page.
- **Scripts:** `generate_demo_data.py` (90-day demo store, clean + messy CSVs).

### Changed
- **Web:** landing page reverted to the yellow "Bahi-Khata" design with a new simple hero.
- **Web:** key-and-lock opening rebuilt with HDRI lighting, CC0 PBR textures, slatted shutter,
  bevelled brass padlock and a properly cut key.

### Removed
- **Web:** dark/blue 10-section landing page and the Recharts dependency.

### Added
- **Web:** new Vyapar.ai landing page (10 sections), bright theme with brand violet/blue accents,
  Geist typography, interactive 3D data core, Recharts product preview, simulated Copilot.
- **Web:** interim key-and-lock shop opening with synthesized sound (photoreal version pending).

### Removed
- **Web:** particle "VYAPAR" hero, ledger hero, bright v1 landing sections and religious motifs.

### Changed
- **Web:** responsive layouts for phone, tablet and desktop (hero, story, bento, dashboard nav and tables).
- **Web:** three.js is lazy-loaded; landing first-load JS dropped from 401 kB to 169 kB.

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
