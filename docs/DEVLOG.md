# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-07 · Responsive pass + performance

- Phone: the hero word now samples a stacked "VYA / PAR / व्यापार" layout on portrait screens
  (it was tiny before). A static typographic word renders instantly and cross-fades to particles on
  the first WebGL frame, so the hero is never blank while three.js loads.
- 3D node labels are clamped inside the viewport; the scroll cue no longer wraps.
- Dashboard: mobile section nav and persona chip replace the sidebar under `md`; the products
  table becomes stacked rows on phones.
- Feature bento: 1 column on phones, 2 on tablets, 6-column bento on large screens.
- Perf: `Hero` imported node data from the scene module, which pulled three.js into the main
  bundle. Splitting it out dropped landing first-load JS from 401 kB to 169 kB.
- Repo: commits no longer carry a Co-Authored-By trailer (owner preference).

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
