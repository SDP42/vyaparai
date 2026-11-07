# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-07 · Phase 0 + F1 kickoff

- Read the 50-page blueprint. Mapped its 16 weeks onto 12 phases (+2 frontend tracks) in `PHASES.md`.
- Backend foundation: layers, models, migrations, auth, workspace tenancy with 404-on-non-member,
  audit log. Strict mypy, ruff, 29 passing tests.
- Found gaps in the blueprint: no returns table (needed for net sales), no inventory snapshots,
  reviews or documents tables, no dataset chosen. Logged in `RESEARCH.md`.
- Naming risk: "Vyapar" is an existing Indian billing app. Logged as decision D2.
- Frontend: picked the "Bahi-Khata" palette over the blueprint's navy/violet to avoid the generic
  AI look. Built the particle-shatter hero (word sampled from the real fonts → 3D data core),
  the scroll story, the zoom reveal and the persona login → demo dashboard.
- Verified in the browser: shatter, zoom, labels, horizontal story, zoom-through and persona redirect.
- **Next:** Phase 1 ingestion (upload → inspect → map → validate → import).
