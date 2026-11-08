# Roadmap & status

_Last updated: 2026-11-08_

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ blocked / decision needed

Detailed backend/product phases: [PHASES.md](PHASES.md).
Current frontend stage (two-page marketing site): [frontend/PHASE-1-REPORT.md](frontend/PHASE-1-REPORT.md).

## Current focus: two-page frontend stage

Per the master prompt, this stage builds **only** (1) the cinematic key-and-lock opening and
(2) the Vyapar.ai landing page on `/`. No backend work happens in this stage. The owner reordered the
work: **landing page first**, then the photoreal opening.

| Frontend phase | Status | Notes |
|---|---|---|
| 1 · Inspect repo & visual direction | ✅ | Report: `docs/frontend/PHASE-1-REPORT.md` |
| 6 · Main landing page | ✅ | **Owner reverted to the yellow "Bahi-Khata" design** (simple hero, story scroll, zoom reveal, features, principles, CTA); dark/blue 10-section version removed |
| 2 · Realistic key, lock, shutter, storefront | ✅ | CC0 HDRI + PBR textures, slatted shutter, brass padlock, cut key, backlit sign; depth of field, bloom, vignette, grain |
| 3 · Click + scroll-controlled unlock (0–20–45–60–75–100 %) | ✅ | Click inserts the key; a pinned 700vh section scrubs settle → turn → release → open → shutter → walk-in; reversible |
| 4 · Audio + cinematic shop opening | 🟡 | Interior with labelled goods; sounds synced to scroll (synthesized). Recorded CC0 audio still pending (decision F-A) |
| 5 · Shop → Vyapar.ai transition | ✅ | "Your business is open." → "Now, let's make it intelligent." → cream fade → VYAPAR.ai → hero |
| 7 · Integrate + polish responsiveness | 🟡 | Desktop + mobile checked; short-height laptops crop pinned headings |
| 8 · Full visitor-journey test | ⏸ | Needs a visual pass with the browser visible (the 3D can't render in a hidden preview pane) |

## Product / backend phases

| Phase | Status | Notes |
|---|---|---|
| 0 · Foundation & discovery | ✅ code · ⏸ decisions | Backend skeleton, auth, tenancy, migrations, CI done |
| 1 · Data ingestion & quality | ✅ | Upload → inspect → map → validate → import, error CSV, background job, demo data, UI wizard, 25 tests |
| 2 · Metric layer & sales analytics | ⬜ | **Next up**: canonical metrics on the imported data + command center |
| 3 · Customer & product intelligence | ⬜ | |
| 4 · Forecasting | ⬜ | |
| F2 · App shell on real APIs | ⬜ | |
| 5 · Inventory & decisions | ⬜ | P1 |
| 6 · NLP reviews | ⬜ | P1 |
| 7 · RAG | ⬜ | P1 |
| 8 · Copilot | ⬜ | P1 |
| 9 · Agents | ⬜ | P1 |
| 10 · Recommendations & reports | ⬜ | P2 |
| 11 · Hardening & launch | ⬜ | |

## Done

### Landing page (`apps/web/components/landing`), yellow design restored on 2026-11-07
- Bright warm "Bahi-Khata" palette (cream, ink, sindoor red, haldi yellow, mor teal), Bricolage
  Grotesque + Instrument Serif
- **Simple hero**: "Your business deserves more than *guesswork.*" Clear copy, two buttons, and the
  product dashboard card tilting upright as you scroll
- Pinned horizontal **story** (data enters → organised → insight → you approve), **zoom-through**
  product reveal, **feature bento** with spotlight, **ledger marquee + principles**, magnetic **CTA**
- No religious motifs; the CTA's large word is now "व्यापार" (business)

### Opening (`apps/web/components/opening`)
- Night street lit by a CC0 HDRI; PBR textures for the painted steel shutter, plaster and pavement
- 30 individual shutter slats slide into a drum housing; bevelled brass padlock, nickel cylinder,
  steel shackle; a flat key with cut teeth; backlit acrylic sign and tube light; warm interior
- Click the key → it arcs to the lock, inserts, turns → shackle springs → lock drops → shutter
  rises → camera walks in → landing page
- Starts muted, with a sound toggle and Skip (Esc); reduced-motion and no-WebGL users skip it
- No religious motifs

### Backend (`apps/api`)
- FastAPI app factory, `/api/v1`, OpenAPI at `/docs`, typed settings with production guards
- Models for users, workspaces, memberships, datasets, jobs, audit logs, products, customers,
  orders and order items; Alembic migration with a drift test
- Auth (register/login/me), workspace RBAC, audit log, health probes; 29 tests passing

### Repo & docs
- README, PHASES, ROADMAP, ARCHITECTURE, RESEARCH, METRICS, DATA_DICTIONARY, API, THREAT_MODEL,
  DESIGN_SYSTEM, ADRs, CONTRIBUTING, CHANGELOG, DEVLOG, frontend Phase 1 report
- GitHub Actions CI; issue & PR templates

## Next up

1. **Phase 2 · metric layer + command center**: net sales, gross profit, orders, AOV, period
   comparison, drivers (volume / price / mix), dashboard on real imported data.
2. Visual QA of the opening with the browser visible; then recorded CC0 audio (F-A).

### Previously listed

1. **Frontend Phase 2 · photoreal storefront**: HDRI lighting, CC0 PBR textures (painted
   metal shutter, granite, concrete), a detailed brass padlock and nickel key, an individual-slat
   shutter, depth of field. Review still frames before animating.
2. **Phase 3 · scroll-scrubbed unlock**: pinned, reversible 0–100 % sequence.
3. **Phases 4–5 · audio + interior + digital transition**.

## Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| F-A | Opening audio | You download CC0 clips · I source Pixabay CC0 · keep synthesized | Recorded CC0 clips |
| F-B | Key & padlock models | Custom-built in code · licensed Sketchfab model | Custom-built |
| F-C | `/login` and `/app` routes | Leave unlinked · remove | Leave unlinked during this stage |
| F-D | HDRI mood | `cobblestone_street_night` · `modern_buildings_night` · `dresden_station_night` | `cobblestone_street_night` |
| D1 | Starter dataset | Synthetic · Online Retail II · Olist | Synthetic + Online Retail II |
| D2 | Product name | Keep "Vyapar" · rename | Check trademark |
| D3–D5 | LLM provider, job runner, hosting | see earlier | Decide when those phases start |

## Known limitations

- The opening is far more realistic but not yet film-grade: no depth of field or bloom, and simple interior goods.
- In dev the opening needs a few seconds to load its assets (~3 MB textures + 1.8 MB HDRI).
- Pinned sections crop their headings on screens shorter than about 650 px.
- Landing first-load JS is 171 kB; three.js loads lazily with the opening.
- All landing figures are illustrative demo data; the Copilot is a front-end simulation.
- SQLite is used in development; production requires PostgreSQL.
