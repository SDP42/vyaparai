# Dev log

Short, dated notes on what changed and why. Newest first.

## 2026-11-19 · Showcase kit and the complete project document

**Screenshots.** `scripts/capture-screens.mjs` drives headless Chrome over the DevTools protocol (Node's built-in WebSocket, no Puppeteer), signs in with a sample account and saves 25 screens: the opening, the landing sections, sign-in, nine app pages and three phone views ([docs/linkedin](linkedin/README.md)). Landing shots skip the opening through its session flag so the cloth is not caught mid-fade.

**Slides and repository card.** Four 4:5 slides frame real screenshots (cover, Ask, agents, opening), and a repository card is drawn from the real Git history: 461 commits from 7 to 12 November, Python 55% and TypeScript 44%.

**Project document.** A 16-section document (problem, tour, jobs, assistant and voice, agents, forecasting, architecture with a diagram, stack and licences, design, security, quality, measured results and limits, deployment, roadmap, repository) exported to a 28-page PDF with 13 figures.

## 2026-11-12 · A real cloth, a new landing page, daily routines and automation agents

**Opening.** The cloth is now simulated: a Verlet particle grid hung from a rail that is narrower than the fabric, so it gathers into real folds, lit from the side so each fold throws a shadow, with a satin ribbon and bow (three.js, MIT; textures generated in code). Cutting the ribbon removes its links at the cut, and the rail lets go from the middle outward so the cloth falls under gravity. The drawn version stays as the fallback without WebGL.

**Landing page.** Rebuilt after the research on what reads as professional: a real Today screen in the hero, a strip of checkable facts instead of invented proof, one pinned how-it-works scene, product screens revealed with clip paths, stacking cards for each job in the shop, a voice section, and a plain "it will / it will not" section.

**Daily routines.** A Today page, the galla (day-end cash count), expenses, an expiry list, supplier order lists to share, and one-line entries ("Ramesh ko 200 udhaar") read back before saving ([DAILY](DAILY.md)).

**Agents.** Six automation agents on top of the four analysts, each a small read-only LangGraph graph that prepares findings and drafts, runnable now or every day at a chosen hour through a cron-friendly runner ([AGENTS](AGENTS.md)).

## 2026-11-11 · Engineering follow-ups, a new opening, staff sales

**Opening.** The 3D key-and-lock scene is gone. The page now opens on a closed shop: a woven cloth tied with a red satin ribbon and a paper tag, scissors beside it. Drag them to the dotted line (or tap them, or press Enter) and the ribbon is cut, the bow and tag fall, and the cloth drops in strips from the middle out. It is drawn in code (no images, models or sounds), shown once per visit, skippable, and absent under reduced motion. The landing dashboard preview no longer clips numbers (its layout follows its own width) and the features section describes what the product really does.

**Speech and names.** Spoken amounts (lakh, crore, डेढ़, सवा, साढ़े) are read, and Hindi product names find English catalogue items through a glossary and sound matching, with "did you mean" buttons when unclear. Personas hide cost and margin per field for jobs without the margin capability.

**Staff.** An optional Cashier or Staff column is read on import; the Staff page shows bills, average bill, items per bill, discount and margin per person, and counter staff see only the name linked to their account.

**Housekeeping.** OpenAPI is exported and checked by a test, and the web types are generated from it. PDF reports use Noto Sans, so amounts print with ₹. An accessibility audit of the landing, sign-in and all app pages found low-contrast text colours, small targets and heading jumps; all fixed ([ACCESSIBILITY](ACCESSIBILITY.md)). Every page headline and intro now exists in Hinglish and Hindi. Dependency audit: no known Python vulnerabilities; PostCSS inside Next 15 is the one npm finding (accepted).

## 2026-11-11 · Personas and voice

**Personas.** Five jobs (owner, operations manager, analyst, accountant, counter staff), each with its own pages, the questions the assistant will answer, and the data it may open ([PERSONAS.md](PERSONAS.md)). A persona is stored on the membership and the invitation, must fit the member's role, and is enforced on the server: the assistant refuses out-of-remit questions before running any tool, the credit book, cost, pricing, supplier-bill and report routes require a capability, and the navigation shows only the persona's pages. The sign-in page now signs in as real sample accounts (development only, refused in production) instead of the old static demo dashboard, which was removed.

**Voice.** Speak a question in Hindi, Hinglish or English ([VOICE.md](VOICE.md)). The browser records and turns the clip into 16 kHz WAV; our server transcribes it with faster-whisper and the Whisper medium weights (MIT), discards the audio, and the person confirms or edits the words before the question is asked. Answers can be read aloud with the phone's own voice. On synthetic speech, medium got the right intent on 17 of 17 clean and 15 of 17 noisy questions (small: 15 and 13) and invented no words from silence or noise; these are optimistic and need a test with real shopkeepers. Findings worth keeping: Whisper spells Hindi by ear, so the question understanding now matches on a consonant skeleton and knows Devanagari spellings of English words; and PyAV (a faster-whisper dependency) bundles GPL codecs, so it is excluded and stubbed rather than installed.

## 2026-11-10 · Copilot, agents, recommendations and reports

**Copilot.** Added product questions, follow-ups that reuse the last question's context, an evidence list on every answer, and a streaming endpoint whose steps are the real recorded ones ([ASSISTANT.md](ASSISTANT.md)). Routing is 100% on 73 questions but keywords were added for misses, so that is a development figure.

**Agents.** Built `investigate_sales` and `weekly_review` as LangGraph graphs over existing services, with a 16-node and 20-second budget, one retry per node, and every step stored and viewable ([AGENTS.md](AGENTS.md)). No language model is used on purpose: steps stay inspectable and text in reviews or documents cannot steer the workflow. Tests plant a sales drop, fail a node, and cut the budget. Weights are transparent rules, not probabilities.

**Recommendations and reports.** Seven kinds of suggestion with a stated impact range; the ones that rest on assumed recovery or uplift rates say so and rank by that. A broken signal does not hide the rest. Reports are frozen snapshots rendered as PDF and CSV; the PDF is English with "Rs" because the built-in fonts lack the rupee sign ([RECOMMENDATIONS.md](RECOMMENDATIONS.md)). The impact assumptions are general, not measured on any shop.

## 2026-11-10 · Udhaar

The research named credit as a strong need that incumbents cover only as a ledger. Built a ledger (import in several layouts, manual entries), FIFO ageing, a chase-first order, drafted reminders in three languages with a firmer tone as dues age, an overdue alert and assistant answers ([UDHAAR.md](UDHAAR.md)). Nothing is sent by the product; a WhatsApp link pre-fills the draft when a phone is saved. All of it is rule-based and tested on a synthetic ledger; whether the tone and the chase order feel right to real shopkeepers is untested.

## 2026-11-10 · Ask, documents (RAG) and a layout pass

**Assistant.** A rules-based router sends English, Hindi and Hinglish questions to read-only tools over the existing services; the answer is written from the tool's numbers, with the period it used and a link to check it. A 66-question set routes 100% but only after I added keywords for the misses (it began at 91%), so treat that as a development figure ([ASSISTANT.md](ASSISTANT.md)).

**Documents.** Compared keyword search, two pretrained embedding models and two fusion methods on 57 labelled questions, then chose a multilingual MiniLM with a 0.3 keyword weight; keywords alone score 1.00 on questions that reuse a document's words but 0.50 on paraphrases, embeddings alone the reverse. The corpus is 12 passages we wrote and the weight was tuned on the same questions, so real performance is unmeasured ([DOCUMENTS.md](DOCUMENTS.md)). Tests caught a title line being returned as the answer and Hinglish questions falling below the confidence floor; both fixed. Restricted documents are filtered before ranking.

**Layout.** Measured every grid at 1100px: odd numbers of cards (3 category cards, 5 metric tiles, 7 review themes) left an empty slot in the last row. Added a wrapping `fluid` row whose last cards grow to fill it, removed double padding on the newer pages, and split Team into two columns.

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
