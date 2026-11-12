# Daily-use features: what would make a shopkeeper open this every day

Research notes, 2026-11-12. **[V]** = read on a fetched page this session. **[U]** = general knowledge or a
search-result summary, not read at source. Most market sources are vendor pages: they show what is sold, not
proof of what owners need. Every ranking below is a hypothesis to test with real shopkeepers.

## 1. What the evidence says

**What competing apps offer**

| App | Features named on its own page | Mark |
|---|---|---|
| Vyapar (billing) | GST/non-GST bills, payment modes recorded on bills, bill-wise profit, stock, barcode, purchase-bill OCR, WhatsApp bill sharing and reminders, staff logins, offline billing, 9+ languages, e-invoice and e-way bill. Expense tracking, day book and batch tracking are **not** named on the home page; expiry appears only under pharmacy | [V] vyaparapp.in |
| myBillBook | Billing, low-stock alerts, **batch and expiry**, WhatsApp/SMS reminders, UPI links, **loyalty points**, online catalogue, daily business report (cash flow, sales, dues), GSTR-1/2/3B reports, "AI bank reconciliation", AI follow-up calls. No expense or attendance feature named | [V] mybillbook.in |
| OkCredit | Khata for customers and suppliers, automatic WhatsApp/SMS reminders, stock with low-stock alerts, bills, UPI collection, loans to Rs 1 lakh, 11 languages. No cashbook, expenses or staff named | [V] okcredit.in/llms.txt |
| Khatabook | Ledger, stock with low-stock alerts, expense tracking, a separate Cash Book app (daily balance, attach bill photos). Staff attendance could not be confirmed as a Khatabook product | [U] store listings via search |
| Zoho Inventory | Reorder points, batch expiry monitoring, purchase orders, vendor price lists, barcode | [V] zoho.com/in/inventory/features |
| PhonePe Business | SmartSpeaker audio confirmations, settlement tracking; "reconciliation" is not named on the page | [V] business.phonepe.com |
| Dukaan, Udaan, Paytm for Business, Marg | Not fetched this session. Online store; B2B ordering; payments and soundbox; pharmacy/distribution ERP with batch and expiry | [U] |

**Pain points**

- Flourish Ventures / 60 Decibels survey of 200 kirana owners and 198 customers: "Shopkeepers face
  difficulties purchasing and managing inventory and serving their customers"; "Identifying and anticipating
  the needs of customers is very difficult"; "I am busy serving customers and so I don't have time to learn
  about new online tools"; customers want more variety; 89% of shops carry 500+ SKUs [V, report PDF text].
  The often-quoted 74% (ordering/receiving stock) and 60% (inventory management) figures are in chart images
  I could not read [U, search summary].
- Owners compare 3-4 sources (Udaan, JioMart, local distributor) before buying one carton; margins are 5-10%;
  they live on distributor credit days; much business runs on WhatsApp [V, one practitioner essay:
  pratikchandak.substack.com, opinion not data].
- Day-end mismatches: bills marked paid before UPI money lands, several soundboxes and apps lengthening the
  day-end tally [U, vendor blogs: Petpooja, Pine Labs, BillCut].
- Expiry: packaged food leads retailer complaints about near-expiry stock in a Kirana Club survey of 9,000+
  retailers (self-selected, vendor-run) [U, search summary]. No quantified kirana or chemist expiry-loss data found.
- **Not found:** any independent study of cash tally, expenses, attendance or GST-prep burden for small shops.

**The structural gap in our product.** Everything we have reads from an imported sales file. A shop without
billing software has nothing new to show tomorrow, so there is no reason to open the app tomorrow. Daily use
needs a small thing the shopkeeper *puts in* each day, which pays back at once.

## 2. Ranked candidate features

Personas: O owner, M operations manager, An analyst, Ac accountant, C counter staff. Effort: S under a week,
M one to two weeks, L more. "Free/offline" = no external service; works in the PWA.

| # | Feature | Daily pain it solves | Who | Data needed (already have?) | Effort | External service? |
|---|---|---|---|---|---|---|
| 1 | **Day-end closing (galla tally)** | "Is the cash right, and what did I really make today?" | O, C enters | Counted cash, UPI total, opening cash, cash paid out: **new**. Sales and udhaar collected: have | M | None. Free, offline-capable |
| 2 | **Expense quick entry** (rent, bijli, salary, transport, chai) | Profit shown today ignores expenses, so it is not believed | O, Ac | **New** table: amount, category, date, optional photo | S | None |
| 3 | **Quick daily sale entry** (one total, or cash/UPI split) for shops with no billing file | No data means nothing to see tomorrow | O, C | **New** manual daily totals; flagged as "typed in, not from bills" | S | None |
| 4 | **Order list by supplier** ("aaj kya mangwana hai") | Ordering is the top reported chore; lists are scribbled and sent on WhatsApp | O, M | Order advice: have. Supplier per item: from purchase bills, have (coverage to check) | S-M | None. Person shares the text via the phone share sheet |
| 5 | **Expiry watch** (sell first / return to distributor) | Expired FMCG and medicine is a dead loss | O, M, C | Batch and expiry date: **new**. Bill OCR could read it from medical bills (unverified accuracy) | M | None |
| 6 | **Supplier dues** (what I owe, to whom, by when) | Missed distributor payments break credit days | O, Ac | Purchase bills: have. Paid/part-paid and due date: **new** fields | S-M | None |
| 7 | **Voice quick entry** ("Ramesh ko 200 udhaar", "bijli bill 1800") | Typing at a busy counter does not happen | O, C | Voice, number parsing, name matching, udhaar: have | S-M | None (Whisper on our server already) |
| 8 | **Today card with ticks** (3 things to do, mark done) | Digest is read and forgotten | O, M | Digest, alerts, udhaar chase list: have. Done state: new | S | None |
| 9 | **Rate check** (selling price, last cost, cheapest supplier for an item) | Staff ask the owner every price; owner compares distributors from memory | O, C (price only), M | Sales prices and bill costs: have. Cost hidden from C by existing masking | S | None |
| 10 | **"Customer asked, we did not have" list** | Lost sales are invisible; anticipating demand is hard [V] | C enters, O reads | **New**: item name (voice), count | S | None |
| 11 | **Staff attendance and advances** | Who came, who took an advance; salary-day arguments | O, M | **New**: staff-day present/half/absent, advance amount | S-M | None |
| 12 | **UPI statement match** | UPI received vs sales recorded | O, Ac | Imported PhonePe/Paytm/bank statement: **new**; formats vary and were not checked | M-L | None if file upload only |
| 13 | **Tax summary for the CA** (sales and purchases by rate, monthly) | Month-end scramble to send papers to the accountant | Ac, O | We store only `tax_amount`; rate and HSN: **new** | M | None. Export only |
| 14 | **Printable price list / shelf labels** | Handwritten rate cards go stale | O, C | Have | S | None |
| 15 | **Regulars who stopped coming / simple points** | Losing a regular unnoticed | O | RFM: have. Points ledger: new | S (list) / M (points) | None |

## 3. Top 5 to build next

**1. Day-end closing, with expenses folded in (rows 1-3).** *Inputs:* opening cash, counted cash, UPI total
read off the payment app, expenses paid from the till, cash given to suppliers, udhaar collected (pre-filled
from the ledger), and the sale total if no bills were imported. *Outputs:* expected cash vs counted cash with
the gap in one sentence ("Rs 340 kam hai"), today's rough profit after expenses, a 30-day history, and a
streak of days closed. *Simplest honest version:* one screen, six number boxes with big keys and voice entry,
no categories beyond a short fixed list. Profit is labelled "rough" when cost data is missing. *Person
confirms:* every number is typed or spoken and confirmed by the person; the app never reads a payment app or bank.

**2. Order list by supplier.** *Inputs:* existing order advice, last supplier and last cost per item from
purchase bills, items the owner adds by hand or voice. *Outputs:* one list per supplier in plain text
("Parle-G 2 carton"), in Hindi or English, with a Share button that opens the phone's share sheet. *Simplest
honest version:* no ordering API, no prices promised; items without a known supplier go under "Other".
*Person confirms:* quantities before sharing; the person presses send in WhatsApp themselves.

**3. Expiry watch.** *Inputs:* item, expiry date (month and year is enough), quantity; entered by hand, by
voice, or suggested from a bill photo. *Outputs:* three lists: expires this month, in 3 months, already
expired; a "sell first" hint and a "ask the distributor about return" reminder. *Simplest honest version:*
manual entry for the 20-50 items the owner worries about, not full batch stock. *Person confirms:* any date
read from a photo, before it is saved. Do not present it as a drug-compliance register.

**4. Supplier dues and rate check.** *Inputs:* purchase bills already imported; new "paid / part paid / due
on" fields. *Outputs:* "You owe Rs X to N suppliers, Rs Y this week"; per item, the last three costs by
supplier. *Simplest honest version:* dues are only as complete as the bills entered, and the screen says so.
*Person confirms:* each payment marked as paid. The app never pays anyone.

**5. Voice quick entry and the Today card.** *Inputs:* a spoken sentence; existing parsers. *Outputs:* a draft
entry (udhaar given, udhaar received, expense, "customer asked for") shown as a sentence to confirm; a home
card with three tasks and tick boxes, feeding the day-close streak. *Simplest honest version:* four sentence
shapes only; anything else goes to Ask. *Person confirms:* every entry, with name and amount read back, since
a misheard amount in a credit ledger damages trust.

## 4. Things to avoid

- **E-invoicing (IRN) and e-way bills.** Mandatory only above Rs 5 crore aggregate turnover, B2B [U, secondary
  sources; check CBIC notification 10/2023]. Our users are almost all below it; it needs government portal
  integration. Do not build or imply.
- **"GST filing" or "GST ready" claims.** Offer a summary export "for your accountant" at most. No return
  preparation, no ITC advice, no late-fee calculators presented as advice.
- **Payments.** No UPI collect links, no payment gateway, no reading SMS or payment-app notifications, no
  settlement tracking. The owner types the UPI total.
- **Loans and credit scoring** of customers or the shop. Regulated; competitors do it through NBFC partners [V OkCredit].
- **Automatic reminders or calls** (WhatsApp Business API, SMS gateways, AI calling as on myBillBook [V]).
  Paid, consent-heavy, and against our person-sends rule.
- **Payroll, PF/ESI, salary slips.** Attendance and advances are a notebook, not payroll.
- **Pharmacy compliance** (schedule registers, prescription records). Expiry watch is a reminder list only.
- **Paid or restricted data:** barcode/product databases, distributor price feeds, bank-statement aggregators.
- **A billing/POS screen.** Three large incumbents give it away free; it would also pull us into invoice-format rules.
- **Dense forms.** Each daily screen: at most six inputs, numerals large, icons with words, Hindi/Hinglish first.

## 5. What is still open in PHASES.md

Unticked checklist items (all four found by searching for `- [ ]`):

| Line | Item | Kind |
|---|---|---|
| 62 | Product name/trademark decision ("Vyapar" is an existing billing app) | Owner decision, not code |
| 241 | Demo video and interview walkthrough | People-made, not code |
| 254 | Test with real shopkeepers and recorded shop audio; Marathi/Gujarati/Tamil/Bengali speech | Real people first; then code (a different speech model) |
| 256 | Confirm persona definitions with real shop owners | Real people |

Open per the status table at the top of PHASES.md and ROADMAP.md, without a checkbox:

- F2 app shell: generated API types and an accessibility pass. Code.
- Phase 11: deployment not rehearsed on a server. Code/ops, needs a server.
- Phase 18: page bodies still English (translation "covers 4 areas"). Code plus a native-speaker review.
- Known limit in PHASES.md: no `returns` table; a timezone change does not recompute business dates. Code.
- **Stale labels to fix:** the table says Phase 0 has "3 small items open" (one unticked found), Phase M has
  "recorded audio open" (no matching checkbox), and Phase 17 shows staff attribution as not started although
  the Phase 20 list ticks it as done.

## Sources

- https://vyaparapp.in/ · https://mybillbook.in/ · https://okcredit.in/llms.txt · https://www.zoho.com/in/inventory/features/ · https://business.phonepe.com/
- https://flourishventures.com/research/digitizing-the-corner-shop/india-spotlight/ (and the linked India PDF)
- https://pratikchandak.substack.com/p/why-kirana-tech-is-so-difficult-to
- Search summaries only: Khatabook store listings, Petpooja/Pine Labs/BillCut soundbox posts, kirana.club returns note, e-invoicing threshold explainers
