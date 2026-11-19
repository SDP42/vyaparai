# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/),
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### 2026-11-12
**Added**
- **Daily routines:** Today page, galla (day-end cash count) with expenses, expiry watch, supplier order lists to share, one-line udhaar and expense entries read back before saving ([DAILY](docs/DAILY.md)).
- **Agents:** six read-only automation agents (morning brief, reorder planner, udhaar collector, day-end check, expiry clearance, price watch), a per-shop daily schedule and a cron runner (`app.agent_runner`).
- **Web:** Today, Galla, Orders and Expiry in the navigation in three languages; Today is the first phone tab; Investigate runs helpers now or every day.

### 2026-11-11
**Added**
- **Personas:** five jobs with their own pages, assistant remit, capability-guarded routes and per-field hiding of cost and margin; one-tap sample sign-in (development only); Team page job and bill-name selectors.
- **Voice:** spoken questions in Hindi, Hinglish and English, transcribed on the server with faster-whisper and Whisper medium; confirm-the-words step; read-aloud answers; spoken-number and Hindi product-name understanding with "did you mean".
- **Staff:** optional Cashier/Staff column on import, sales by person, counter staff see only their own.
- **Web:** closed-shop opening (cloth, ribbon, draggable scissors); generated API types (`make gen-api`); headline and intro of every page in Hinglish and Hindi.
- **API:** `openapi.json` export with a staleness test; ₹ in PDF reports (bundled Noto Sans, SIL OFL).
- **Docs:** PERSONAS, VOICE, ACCESSIBILITY, ADR 0008, research on personas and voice; README, ROADMAP, ARCHITECTURE, THREAT_MODEL, MODELS, DATA_DICTIONARY, MVP and others rewritten for the current system.

**Changed**
- Text colours darkened to pass WCAG AA; small targets and heading order fixed.
- Landing: the dashboard preview no longer clips numbers; features describe the real product.
- CI: pushes to main are no longer cancelled by the next push; the search model is cached.

**Removed**
- The 3D key-and-lock opening, three.js and its assets; the static demo-persona dashboard.

**Security**
- PyAV is excluded (its wheels bundle GPL codecs); `pip-audit` clean; the demo sign-in is refused in production.

### Earlier work (before 2026-11-08)

### Added
- **API:** Phase 2 analytics: metric registry (v1, 16 metrics), `/metrics`, `/analytics/{filters,overview,drivers,transactions}`;
  period comparison, price-volume-mix drivers, insights, coverage warnings; migration `46f90922b2e7` (`orders.business_date`). 61 new tests.
- **Web:** app shell, Command center, Sales explorer and Data page for accounts; Recharts trend with comparison overlay.
- **Docs:** Phase 2 and ML research, model catalogue, ADRs 0006 and 0007, refreshed README, roadmap and phases.

### Fixed
- **API:** imported wall-clock times are now interpreted in the workspace timezone (were stored as UTC).

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
