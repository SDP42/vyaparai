# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-09 · Model benchmark: tuning, pretrained and model choice

Ran 21 model variants on a 2-year synthetic panel (40 SKUs) with rolling backtests and a single-use
holdout ([report](research/PHASE-4-BENCHMARK.md)). LightGBM global model won (28 % better than seasonal
naive); Optuna tuning gave no measurable gain; Chronos-Bolt pretrained worked zero-shot (16 % better) and
fits cold start; slow movers sit at the noise floor; all models under-forecast the festive peak.
PyPI was ~0.06 MB/s on the dev network, so the experiment env was built from conda-forge instead.

## 2026-11-08 (night) · Product-value research, phases 12–19, Phase 4a started

- Researched why owners would use us ([PRODUCT-VALUE.md](research/PRODUCT-VALUE.md)): billing and udhaar apps record, they rarely advise. Added phases 12–19 (digest, credit, alerts, connectors, pricing, multi-store, mobile/Hinglish, goals) and the campaigns plan (3B).
- Owner feedback: sidebar and demo showed "Phase 2/3" labels on features that now exist. Replaced with real links or "Soon"; the import wizard now links to the dashboards.
- 4a: `app/services/forecasting/` with error metrics, baselines, rolling-origin backtester, demand classes. 182 tests. Pure Python by design; statsforecast and LightGBM arrive in 4b/4c.

## 2026-11-08 (evening) · Phase 3 shipped: customer and product intelligence

**Research first** ([PHASE-3-RESEARCH.md](research/PHASE-3-RESEARCH.md)): RFM scoring methods, segment
naming, cohort retention, ABC and menu-engineering quadrants, market-basket measures.

**Backend.** Scoring, segments, status, cohorts, product classification, basket pairs and CSV export
under `/analytics/customers/*`, `/analytics/products*`, `/analytics/basket`. Registry v2 adds four
customer metrics. 170 tests, including hand-computed fixtures and reconciliation on the 8,188-row sample.
Fixed a sort bug found by the tests (recency sort returned most recent first).

**Frontend.** `/app/customers` (tiles, segments, activity, R×F grid, cohort heatmap, filterable list,
CSV) and `/app/products` (portfolio, ABC, categories, product table, basket pairs, CSV). Checked in the
browser. A stale `.next` cache after adding routes caused 404s for `main-app.js`; clearing it fixed it.

**Next:** Phase 4a (forecasting foundations).

## 2026-11-08 (later) · Phase 2 shipped; ML plan written

**Research first.** Looked up price-volume-mix conventions, retail KPI definitions, comparison
alignment and metric registries; decisions are in `docs/research/PHASE-2-RESEARCH.md`. Also researched the
forecasting model landscape, time-aware tuning and intermittent demand for the owner's ML request:
`docs/research/PHASE-4-ML-PLAN.md`, `docs/MODELS.md`, ADR 0007.

**Backend.** `orders.business_date` (migration with a timezone-aware backfill; found and fixed that
imports had been labelling wall-clock times as UTC); `services/analytics/` (registry, queries, comparisons,
drivers, insights, text helpers, service) and five endpoints. 61 new tests: hand-computed fixture,
exact-sum identity on 25 random cases, filters, comparison modes, empty and single-day periods, tenancy,
and reconciliation on the 8,188-row sample.

**Bugs caught by tests or live checks.** The data-summary query kept using the UTC date; a column-level
`distinct()` warning; a Recharts tooltip typing error; wide tables forcing the Sales page to 570 px on a phone
(grid items need `min-w-0`).

**Frontend.** App shell with workspace and period/filter context; Command center, Sales explorer and Data page;
route gate that keeps the persona demo separate from real accounts. Checked in the browser on the real imported
sample at desktop and phone widths, including drill-through (857 lines for Staples = ₹2,83,054, matching the
contribution table).

**Next:** Phase 4 (forecasting and the ML platform), starting with 4a.

## 2026-11-08 · Opening finished · Phase 1 ingestion shipped

**Opening**
- Now a pinned 700vh section instead of a fixed overlay. Click the key: it arcs to the padlock,
  rolls into orientation and enters the keyway (time-based). Then **scroll drives** a paused GSAP
  timeline: settle (0–20 %) → turn (20–45 %) → release (45–60 %) → padlock opens and falls (60–75 %) →
  shutter rises slat by slat (75–100 %) → walk-in. It's fully reversible.
- Post-processing: depth of field that auto-focuses on the camera target, bloom on the sign, tube light
  and interior, vignette and grain (off on low-power devices).
- Interior: generic, unbranded labelled packets (canvas label atlas), glass jars, grain sacks and a
  glass-top counter. Sounds fire on forward threshold crossings; shop ambience loops inside.
- Hand-off: captions → cream fade → "VYAPAR.ai · Unlock the intelligence behind your business" → hero.
  The navigation stays hidden while the opening is on screen.

**Phase 1: ingestion**
- Backend: `services/ingestion/{fields,reader,parsing,pipeline}.py`, `services/datasets.py`, new
  endpoints, migration `56799aeb0cfc` (dataset inspection/validation/storage columns).
- Indian-format parsing: ₹ symbols, lakh commas, day-first dates, bill-style headers.
- Import re-validates (single source of truth), runs in one transaction, skips existing orders.
- 8,188-row sample: 8,025 valid / 163 rejected; imported net sales ₹23,90,515.55 = validation preview.
- Frontend: create account, create workspace, 4-step wizard (upload → map → review → import),
  data summary tiles, upload history, duplicate-upload handling, error CSV download.
- Fixed two client bugs before they shipped: polling cancelled by parent re-renders, and StrictMode
  double-mount (import start is now deduped per dataset).

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
