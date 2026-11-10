# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-10 · Purchase bills

Research said the biggest weakness is data access, so bills now come in by photo or PDF ([BILLS.md](BILLS.md)). Pretrained OCR was allowed, so RapidOCR (PaddleOCR models, CPU) is used when installed, with Tesseract as the fallback and the PDF text layer first. A drafted bill is checked by a person before it changes any cost. Real OCR on a rendered bill read every line, total, GSTIN and date correctly, but that is one clean image: accuracy on real, crumpled bills is unmeasured. Confirmed bills feed a supplier price history and an alert when a price rises 5% or more.

## 2026-11-10 · F2 sessions, team invites, MVP journey, Phase 6 reviews

**Sessions.** Researched OWASP's session guidance, then moved sign-in off `localStorage`: a 15-minute access token lives only in page memory and a rotating refresh token sits in an HttpOnly cookie. Reusing an old refresh token revokes the whole sign-in; logout and "sign out everywhere" revoke server-side; cookie endpoints need a custom header and a known Origin; login and sign-up are throttled. The throttle counters are in memory, which is fine for one process and must move to Redis before several workers. **Team.** Roles can be changed, members removed (never the last owner), and one-time invitation links created (the token travels after `#`, is stored hashed, expires in 7 days). **MVP.** `test_mvp_journey.py` walks sign-up to stock advice to teammate to sign-out as one user; [MVP.md](MVP.md) lists what is ready and what is not.

**Reviews (Phase 6).** Researched first ([REVIEWS-NLP.md](research/REVIEWS-NLP.md)): no permissively licensed Hinglish review dataset exists that we could confirm, so nothing third-party is bundled; the word lists and test sets are our own. The reading is a transparent lexicon plus a model learned from each shop's own star ratings. Honest numbers: on the first self-written set macro-F1 was 0.90 to 1.00, but that set was written next to the lexicon so it proves little. A second set written without the lexicon open scored about 65% correct, every miss being a review with no known opinion words (none flipped polarity). I then broadened the vocabulary generally, which makes that second set a development set whose score (now ~92%) is optimistic. True accuracy on unseen shop reviews is unknown and probably 0.6 to 0.75; the page says how many reviews had no recognised words.

## 2026-11-10 · Phase 15: connectors and scheduled imports

Researched first ([CONNECTORS.md](research/CONNECTORS.md)). The searches could not confirm any billing app's export columns, so instead of guessing
presets the product now **remembers a confirmed column mapping by the file's header fingerprint**, which works for any app from the
second file on. Owners can connect a published Google Sheet, Drive or Dropbox link that is fetched hourly or daily; unchanged files are skipped
and changed ones add only new orders. The fetch is the risky part, so it follows OWASP's SSRF guidance (allow-list, one DNS resolution, public addresses only, connection
pinned to the address, per-hop redirect checks, caps). The tests caught a real gap: Python treats multicast addresses as "global", so they
were being allowed; multicast, reserved, unspecified and IPv4-mapped internal addresses are now refused. Live checks: localhost, a metadata name and an
unlisted host were refused, and a real HTTPS download from an allowed host worked. Also fixed an older bug: the API sends UTC times without a
marker, so the browser showed them hours off ("Checked 6 h ago" right after a check, wrong "Built" time on forecasts).

## 2026-11-09 (night) · Phase 5 inventory and the festival, region and cricket system

**Festivals first, in depth.** One research agent produced a sourced, cross-checked table (320 events, 2024-2028: festivals,
holidays, season windows, cricket) and notes on why something is on almost every day, which dates really move retail, regional
differences and cricket's effect. I validated it before use: no duplicate ids or impossible dates, and anchors I know independently
all matched (Diwali, Holi, Eid, Raksha Bandhan, Onam, IPL and World Cup finals). It also had to be extended backwards to 2024,
because the model needs past events to learn from. The tests exposed a modelling flaw: "national" events limited to some zones
and Kerala-centric Onam showing for Tamil Nadu. Fixed with core versus zone relevance (weight 0.5), a state setting, and tests for six
states. Events feed the forecast as a signal group that is kept only if the backtest improves; warnings name the festival.
**Phase 5.** Stock counts, cover from the forecast, order advice, dead stock and cash tied up, with alerts and a Stock page.
An alert fires when a festival is close and products it touches may run out. 300+ backend tests.

## 2026-11-09 (late night) · Phase 4 completed

Finished what was left of the forecasting phase, following the benchmark: a dependency-free **Theta** model joins
LightGBM and the recent average (best per product by backtest); a per-shop **method comparison**; optional
**tuning** by seeded random search inside the training period (it found nothing better than the defaults on the
2-year data, as the benchmark predicted, so it is off by default); an owner-set **festive uplift**, labelled as an
assumption; a **registry** with numbered versions, a **ship gate** and rollback; and a scheduled rebuild command
(`python -m app.forecast_runner`). Decisions and evidence for what was not shipped (ETS/ARIMA, Croston, ensembles,
Chronos, MLflow) are in [PHASE-4-DECISIONS.md](research/PHASE-4-DECISIONS.md). Bugs the tests caught: the finished job
overwrote its own options. Theta's weekday shrinkage was halving the pattern for steady shops; it now trusts the
pattern after 8 weeks. 268 backend tests.

## 2026-11-09 (night) · Phases 15B and 14: cost history and alerts; packaging plan

**Costs.** Every sale line already stores the cost at the time, so cost history needs no new data entry. The cost
engine compares the last 28 days with the 28 before on lines that have a cost, flags a **margin leak** when cost
rose 3 % or more and the margin fell more than a point, and suggests the price that restores the old margin
(cost / (1 - old margin)). On the 40-product sample it finds the planted rises (eggs, sugar, toor dal, ₹1,561 lost).
**Alerts.** Fixed rules: a day against the same weekday over 8 weeks (median and MAD), week drop, margin leak,
discount creep, product stopped, lapsed regulars, data nudges. Alerts open, resolve and stay dismissed
correctly; a high alert becomes the digest's action; the sidebar shows a badge. Both were checked by hand:
sales drop -64.9 % (z -8.97), discount +10 pts, leak ₹200 with a ₹180 suggestion. One test of mine used the wrong
window (a product needed 8 selling days inside the window).
**Also.** A workspace switcher (needed to view the new sample; also groundwork for multi-store) and
[PRODUCT-PACKAGING.md](research/PRODUCT-PACKAGING.md): market prices, draft tiers, meters for the costly features,
the entitlements service to build, and the next features ranked by willingness to pay.

## 2026-11-09 (late) · Phase 12: owner digest

Researched what a daily summary should hold ([DIGEST.md](research/DIGEST.md)), then built it: three numbers
(sales, orders, margin or average bill) against the same weekday or week before, one prioritised action
(lapsed regulars, rising or falling products from the forecast, sales drop, missing costs), the forecast
outlook, and honest notes about stale data. Text for a phone, HTML for email, SMTP delivery that stays off
until configured, a once-per-local-day runner (`python -m app.digest_runner`), history, and a Digest page.
Tests used a shop computed by hand (daily +40.0 %, margin 37.9 %; weekly +22.9 %, margin 39.7 %). Found by
tests: dates are not JSON-storable, and one margin change used banker's rounding (39.65 became 39.6).
No customer names or IDs appear in a digest.

## 2026-11-09 (night) · Campaigns C1

Researched win-back practice and consent rules, then built the campaign planner: eight segment plays,
offers that keep a margin floor (largest safe discount d = 1 - (1-m)/(1-f), checked by hand), a step ladder
that never opens with the deepest offer, per-customer timing from their own order gap, a stable 10 % holdout,
English and Hinglish messages with an opt-out line, projections labelled as assumptions, and an audited CSV
export. Nothing is sent. Page: /app/campaigns. A sample-data test caught my own wrong assertion: products
already below the floor correctly get no discount. Consent storage (C2), sending (C3) and measurement (C4) remain.

## 2026-11-09 (evening) · Forecasting in the product, weather signal

Built the forecasting engine (global LightGBM, simple-average fallback, 3 rolling backtests, intervals
calibrated to 80 % coverage, per-series model choice), stored runs, the Forecasts page and product drawer.
Added optional outside signals: the engine runs with and without them and keeps them only if the backtest
improves by 2 %. Weather comes from Open-Meteo's free endpoint (non-commercial), blocked in production
without a paid key. A real call for Pune worked; weather was tried and rejected on the sample data
(39.3 % vs 39.5 % error), which is the right answer because the sample has no weather effect.
Bugs found by use: a React dev-mode flag stopped the job poller; jobs lost to a server restart could block
new runs (now recovered after 15 minutes).

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
