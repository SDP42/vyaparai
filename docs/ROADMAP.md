# Roadmap & status

_Last updated: 2026-11-11_

Legend: ✅ done · 🟡 in progress · ⬜ not started · ⏸ blocked / needs a decision

Checklists and exit criteria for every phase: [PHASES.md](PHASES.md).

## 1. Status at a glance

| # | Phase | Status | What it delivers |
|---|---|---|---|
| 0 | Foundation & discovery | ✅ | API skeleton, auth, workspaces/RBAC, audit log, migrations, CI |
| M | Marketing site (opening + landing) | ✅ | Key-and-lock opening, scroll-driven unlock, landing page |
| 1 | Data ingestion & quality | ✅ | Upload → inspect → map → validate → import; wizard UI |
| 2 | Metric layer & sales analytics | ✅ | Versioned metric registry, comparisons, price-volume-mix drivers, command center, sales explorer |
| 3 | Customer & product intelligence | ✅ | RFM, cohorts, margin and discount analysis, ABC, portfolio quadrants, basket pairs |
| **4** | **Forecasting & ML platform** | ✅ | Many models (statistical, intermittent, LightGBM, ensembles), Optuna tuning, backtests, conformal intervals, registry, UI |
| 3B | Campaigns and retention automation | ✅ | Consent and opt-outs, a person-sent outbox, holdout-measured uplift with intervals ([CAMPAIGN-RUNS](CAMPAIGN-RUNS.md)) |
| F2 | App shell polish | 🟡 | Cookie sessions and team invites done; generated API types and accessibility pass open |
| 5 | Inventory & decision support | ✅ | Stock cover, order advice, dead stock, cash tied up |
| 5B | Festivals, regions and cricket | ✅ | 320 dated events, region matching, forecast signals, alerts, Festivals page |
| 6 | NLP review intelligence | ✅ | Sentiment and themes in English, Hindi and Hinglish, with evidence |
| 7 | Document intelligence (RAG) | ✅ | Multilingual search over your own documents with citations ([DOCUMENTS](DOCUMENTS.md)) |
| 8 | Vyapar Copilot | ✅ | Ask page: English, Hindi, Hinglish; follow-ups, product questions, evidence panel, streamed steps ([ASSISTANT](ASSISTANT.md)) |
| 9 | Agent workflows | ✅ | Bounded, traced, read-only LangGraph investigations ([AGENTS](AGENTS.md)) |
| 10 | Recommendations & reports | ✅ | Ranked actions with impact ranges and approvals; PDF/CSV reports ([RECOMMENDATIONS](RECOMMENDATIONS.md)) |
| 11 | Hardening, deployment, launch | ✅ code | Shared rate limits, security headers, size limits, PostgreSQL timeouts, Docker stack, backups, runbook; not yet rehearsed on a server ([RUNBOOK](RUNBOOK.md)) |
| 12 | Daily and weekly digest (push) | ✅ | Three numbers and one action, by WhatsApp or email |
| 13 | Cash and credit (udhaar) intelligence | ✅ | Dues by age, who to chase, drafted reminders in three languages ([UDHAAR](UDHAAR.md)) |
| 14 | Alerts and anomalies | ✅ | Sales drop, margin leak, stock-out risk |
| 15 | Connectors and scheduled imports | ✅ | Remembered column mappings, connected Google Sheet or shared-file links, scheduled and deduplicated |
| 15B | Cost history and margin-leak tracking | ✅ | Cost history from every sale, margin leaks with a suggested price; purchase-bill photo/PDF import done ([BILLS](BILLS.md), [plan](research/COST-TRACKING.md)) |
| 16 | Pricing and promotion advisor | ✅ | Which discounts paid off (vs the same weekday, profit after discount), small safe price trials ([PRICING](PRICING.md)) |
| 17 | Multi-store and staff | ✅ | Side-by-side comparison, needs-attention flags, add a shop; sales by cashier or salesperson when the sales file has that column ([STORES](STORES.md)) |
| 18 | Mobile-first and Hinglish/Hindi | ✅ app · 🟡 language | Installable PWA with offline reading and Hinglish/Hindi for navigation, Ask, Next steps, Udhaar and every page's headline and intro; page bodies English ([MOBILE](MOBILE.md)) |
| 19 | Benchmarks and goals | ✅ goals | Targets with pace and a likely-finish range, benchmarks from your own history; no peer data exists ([GOALS](GOALS.md)) |
| 20 | Personas and voice | ✅ first version | Five jobs (owner, operations manager, analyst, accountant, counter staff) with their own pages, assistant remit and data guards, one-tap sample sign-ins; ask by voice in Hindi, Hinglish or English with a free Whisper model and a confirm-the-words step ([PERSONAS](PERSONAS.md), [VOICE](VOICE.md)) |

**MVP boundary:** phases 0–4 + F2 (upload → trusted metrics → forecast in a usable app). Every later phase has since
been built to a first version; what remains is proof, not features.

## 2. What is done

### Backend (`apps/api`): 633 tests, strict mypy, ruff clean
- FastAPI app factory, `/api/v1`, uniform error envelope, request IDs, JSON logs, health probes, hardening middleware
- Auth (Argon2id, rotating HttpOnly refresh sessions with reuse detection), workspaces with four roles and five
  personas, invitations, audit log, 404-on-non-member tenancy (tested), production settings guards
- Ingestion with remembered mappings, connectors and scheduled imports; the metric layer; customers, products, staff
- Forecasting with honest backtests and a ship gate; stock, costs, alerts, digest, pricing, goals, stores
- Udhaar, supplier bills (OCR), campaigns with consent and uplift, reviews NLP, document search
- The assistant (three languages, personas, voice, spoken numbers and product names), LangGraph investigations,
  recommendations and PDF/CSV reports (₹ in Noto Sans)
- `openapi.json` exported and tested for staleness; licence audit test; pip-audit clean on 2026-11-11

### Frontend (`apps/web`)
- **Marketing:** the closed-shop opening (cloth, ribbon, draggable scissors), then the landing page (hero with a
  product card, story, zoom reveal, features that describe the real product, principles, call to action)
- **App:** 24 pages behind a responsive shell (sidebar, tablet rail, phone bottom bar and sheet) filtered by the
  member's persona; voice input with a confirm step; read-aloud; PWA with offline reading; Hinglish and Hindi
  navigation, assistant, credit pages, and every page's headline and intro; types generated from the API
- Accessibility audit of the landing, sign-in and all app pages with fixes ([ACCESSIBILITY](ACCESSIBILITY.md))

### Repo and docs
- README, ROADMAP, PHASES, ARCHITECTURE, API, DATA_DICTIONARY, METRICS, MODELS, THREAT_MODEL, RUNBOOK, MVP, one doc per
  feature, research notes, eight ADRs, CONTRIBUTING, CHANGELOG, DEVLOG; GitHub Actions CI (lint, types, tests with
  coverage, web build, Docker images, dependency audit)

## 3. What is left

Not code, mostly: it needs real people, real data or a real server.

| Item | Why it is not done | Next step |
|---|---|---|
| Test voice and personas with real shopkeepers | Needs people and recorded audio; our speech tests are synthetic | Record 50–100 real questions in a real shop and re-run `scripts/eval_voice.py` logic on them |
| Confirm the five persona definitions | They come from general knowledge, not interviews | Short interviews with shop owners and counter staff |
| Native review of Hinglish and Hindi wording; translate page bodies | Needs a native speaker | Review `lib/i18n.tsx`; then translate the cards and tables |
| Marathi, Gujarati, Tamil, Bengali speech | Whisper medium is weak there; IndicWhisper needs conversion and a licence check of the exact checkpoint | See [VOICE](VOICE.md) |
| Measure review, OCR, search and pricing accuracy on real shop files | Current numbers are on small self-written sets | One consenting shop's export |
| Deployment rehearsal and restore test | Needs a real server | Follow [RUNBOOK](RUNBOOK.md) on a small VM |
| Real phone and screen-reader tests | Needs devices | Install the PWA, try microphone and read-aloud; VoiceOver or TalkBack pass |
| Hindi PDF reports | The PDF library cannot shape Devanagari | Pick a shaping engine or render Hindi reports another way |
| Per-person targets | Not built | After real staff data exists |
| Demo video and interview walkthrough | People-made | |
| Automated visitor-journey (browser) test | Not written | Playwright against the landing, opening and sign-in |

## 4. Next up

1. Real-shop voice and persona tests (above), because they decide whether those features are usable.
2. Native review of the Hindi and Hinglish wording, then translating page bodies.
3. A deployment rehearsal with a restore test.

## 5. Open decisions

| # | Decision | Options | State |
|---|---|---|---|
| D2 | Product name | Keep "Vyapar AI" · rename | **Open, the owner's call.** "Vyapar" is an existing Indian billing app; fine privately, check trademark before going public |
| D8 | Project licence | MIT · Apache-2.0 · AGPL · proprietary | **Open, the owner's call.** Dependencies are all permissive |
| D1 | Benchmark data | Synthetic only · add a public set | **Decided**: synthetic in the repo; see [ADR 0008](adr/0008-benchmark-data.md) |
| D3 | LLM for the assistant | Hosted · local · none | **Decided: none.** Answers come from tested tools; this is a safeguard as well as a limit |
| F-A | Opening audio | Recorded clips · synthesized | **Closed**: the new opening has no audio |
| F-C | Demo persona routes | Keep · remove | **Closed**: replaced by real sample accounts (dev only) |
| D4 | Background jobs | In-process · queue | In-process; revisit if several workers are needed |
| D5 | Hosting | Render, Railway, Fly, a VM | Open until the first rehearsal |
| D6 | Returns | Reject negatives · add a table | Negatives are still rejected; `returned` orders are excluded from net sales |
| D7 | ML compute | CPU only · GPU worker | CPU only; deep models stay optional |

## 6. Known limitations

- Returns (negative quantities) are rejected at import; `returned` orders are excluded from net sales.
- A rejected line inside a multi-line order leaves the rest of that order imported.
- Changing a workspace timezone does not recompute stored business dates.
- Import progress jumps 10 → 100 because the import is one transaction.
- Rate-limit counters are per process unless `REDIS_URL` is set.
- Voice needs about 2 GB of free memory with `medium` and a few seconds per question on a CPU; first use downloads
  about 1.5 GB.
- Cost and margin hiding works on field names; a sentence that mentions a margin is not rewritten.
- The Hinglish and Hindi wording has not been reviewed by a native speaker.
