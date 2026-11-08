# Research notes: gaps in the blueprint and what to add

The 50-page blueprint is strong on principles but leaves several decisions open. This document
lists those gaps, then proposes additions that make Vyapar AI specifically useful for Indian
small and medium retailers. Items here are **proposals** until they move into
[PHASES.md](PHASES.md).

## 1. Gaps in the blueprint (things it implies but does not define)

| Gap | Why it matters | Proposal | Phase |
|---|---|---|---|
| No **returns/refunds** table | "Net sales" (§13) cannot be defined without it | Add `returns` (order_item_id, qty, amount, reason, date) | 1–2 |
| No **inventory snapshot** table | §15 needs stock-on-hand over time | `inventory_snapshots` (product, date, on_hand, reserved, inbound) | 5 |
| No **reviews** / **documents** tables | §17 and §18 need storage + lineage | `reviews`, `documents`, `document_chunks` | 6–7 |
| Starter **dataset** not chosen | Every metric test needs fixtures | See [starter datasets](#starter-datasets) | 0 |
| **Background job** runner not chosen | Imports and training are long-running | DB-backed `jobs` table + in-process worker; Redis queue later | 1 |
| **Token lifecycle** (refresh, revoke, reset) | Blueprint asks for short sessions + recovery | Refresh token in HttpOnly cookie, rotation, password reset | F2 |
| **Rate limiting** | Login brute force, upload abuse | `slowapi` or reverse-proxy limits | 11 |
| **Timezone & currency** handling | Day boundaries change daily sales | Store UTC; bucket by workspace timezone (default Asia/Kolkata) | 2 |
| **Typed API contract** for the web app | Avoid frontend/backend drift (§08) | Generate TS types from `/api/v1/openapi.json` | F2 |
| **Observability** | Debugging agents and imports | Request IDs (done) → OpenTelemetry traces later | 9, 11 |
| **Data retention / deletion** | Privacy (§24) | Workspace export + hard-delete job; retention policy doc | 11 |

## 2. India-specific additions (high value, low cost)

1. **GST awareness** — store `tax_amount` per order (done) and optional HSN/SAC code per product;
   report sales both ex-GST and incl-GST so numbers match the owner's GST returns.
2. **Indian number formatting** — show ₹12,34,567 (lakh/crore grouping) via `Intl.NumberFormat('en-IN')`.
3. **Festival seasonality** — Diwali, Navratri, Dussehra, Eid, Holi, Onam, Pongal, wedding season
   as forecast features. Their dates move each year, so keep a dated holiday table.
4. **Credit sales (udhaar) & receivables ageing** — very common in Indian retail; a
   "who owes me, for how long" view is often more valuable than a forecast.
5. **Payment-mode analytics** — UPI vs cash vs card mix and trend.
6. **Imports from common billing tools** — mapping presets for Tally, Busy, Marg and
   spreadsheet exports so column mapping is one click.
7. **Multilingual reviews** — Hindi, Hinglish (Roman script) and regional languages; evaluate a
   multilingual model (e.g. MuRIL / IndicBERT / multilingual-E5) against the TF-IDF baseline.
8. **WhatsApp-style summaries (P2)** — a weekly one-screen summary is how many owners would
   actually consume insights.
9. **Bilingual UI** — English first, Hindi labels later; the landing page already uses
   "व्यापार" as a brand element.

## 3. Starter datasets

Verify each licence before committing data to the repo. Never commit real customer data.

| Dataset | Grain | Fits | Licence (verify) | Notes |
|---|---|---|---|---|
| **Synthetic generator** (ours) | line item | all P0 metrics | ours | Known answers → exact metric tests. **Use first.** |
| UCI *Online Retail II* | line item, 2009–2011 | sales, RFM, forecasting | CC BY 4.0 | UK retailer; has returns as negative qty — good for net-sales tests |
| Olist Brazilian E-commerce | orders, items, reviews, customers | sales, reviews, delivery | CC BY-NC-SA 4.0 | Non-commercial; reviews in Portuguese |
| M5 Forecasting (Walmart) | daily item-store | forecasting | competition terms | Large; good for forecasting benchmarks only |

## 4. Technology choices (researched recommendations)

| Area | Choice | Why |
|---|---|---|
| API | FastAPI + Pydantic v2 | Typed contracts, OpenAPI for free |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Mature, works on SQLite and PostgreSQL |
| Passwords | Argon2id via `pwdlib` | Current OWASP recommendation; passlib is unmaintained |
| Tokens | PyJWT (HS256), short expiry | Simple; move to cookie session for the web app |
| Data wrangling | pandas (+ `python-calamine` for fast XLSX) | Ecosystem; Polars if imports get slow |
| Forecasting | `statsforecast` (ETS/ARIMA/Theta/MSTL, Croston/SBA/TSB), LightGBM global + quantile models, Optuna tuning, conformal intervals, ensembles | One protocol compares many models; see [ML plan](research/PHASE-4-ML-PLAN.md) |
| NLP | scikit-learn TF-IDF + LR, then multilingual transformer | Blueprint asks for a measured baseline |
| RAG | Sentence-Transformers + FAISS, `pymupdf` / `python-docx` | Local-first, no paid vector DB |
| Agents | LangGraph | Explicit typed state graph (blueprint §21) |
| Web | Next.js + TypeScript + Tailwind | Blueprint §08 |
| Motion | Motion (Framer) for UI, GSAP ScrollTrigger for the landing story, Lenis smooth scroll | Blueprint §06; one animation system per element |
| 3D | three.js via React Three Fiber + drei | Blueprint §05 |
| UI primitives | shadcn/ui-style (Radix) components, owned in-repo | Accessible, no lock-in |

### Design references studied for the landing page
React Bits (text-split, particle and spotlight-card patterns), shadcn/ui (accessible
primitives), Aceternity/Magic UI-style scroll reveals, and three.js points/particle morph
techniques. We **re-implement** patterns rather than copy components, and deliberately avoid
the purple-blue "AI SaaS" gradient look — see [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## 5. Naming risk

"Vyapar" is also the name of a widely used Indian GST billing/accounting app. If this project
is ever public or commercial, check trademark conflicts and consider a distinct name or a
clear sub-brand. Fine for a private portfolio project as-is; recorded as decision **D2** in
[ROADMAP.md](ROADMAP.md#open-decisions-need-owner-input).
