# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-07 (late) · Back to the yellow design + a realistic opening

- Owner feedback: the dark/blue 10-section landing felt wrong; the earlier **yellow** design (its
  content, animations, transitions and scroll effects) was better, and the key/shop looked cartoonish.
- Restored the yellow landing sections from git (`ea23f8e`) and wrote a **simple hero** in that style.
  Removed the dark landing components and the Recharts dependency.
- Rebuilt the opening for realism: CC0 Poly Haven HDRI (`cobblestone_street_night`) for reflections;
  PBR texture sets for the painted metal shutter, plaster and concrete pavement; 30 individual slats;
  a bevelled brass padlock (ExtrudeGeometry); a tube-swept steel shackle; a flat key with real
  bitting; a warm street-lamp spotlight with soft shadows; a backlit sign; ACES tone mapping; a vignette.
- Assets in `apps/web/public/assets/opening/` (CC0, see `LICENSES.md`), recompressed to ~3 MB.

## 2026-11-07 · Two-page frontend stage: landing page built (owner reprioritised it first)

- New master prompt: build only (1) a cinematic key-and-lock opening and (2) the Vyapar.ai
  landing page. Phase 1 inspection report: `docs/frontend/PHASE-1-REPORT.md`.
- Owner asked for the **landing page first**, in a **bright** theme, and **no religious motifs**.
- Landing page (`components/landing/*`), all ten sections from the brief: navigation, hero with an
  interactive R3F "data-to-decision" core (Sales, Customers, Inventory, Forecasts), problem section
  (scattered fragments snap into order on scroll), 10-capability bento, pinned how-it-works timeline,
  Recharts product preview, intelligence showcase tabs, simulated Copilot conversation, trust chain,
  final CTA and footer. One consistent demo story (Oct net sales −6.2%), clearly labelled.
- Interim key-and-lock opening restored in front of the landing (`components/opening/*`): click the
  key, it flies into the lock, shackle pops, shutter rolls up, camera dives in, with synthesized sound.
  **Not yet photoreal**; that is the next phase.
- Removed rejected prototypes (particle hero, ledger hero, शुभ लाभ elements, bright v1 sections).
- Verified at desktop and mobile widths; production build passes.

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
