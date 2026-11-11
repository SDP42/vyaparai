# Vyapar AI: Personas and Voice Research

Tags: [V] = read on a source page during this research; [U] = general knowledge, not verified here. URLs in the Sources section.

## Executive summary
1. Five personas map to roles: owner=owner, ops manager=admin, accountant=viewer (finance scope), analyst=analyst, counter staff=a NEW restricted "staff/viewer-lite" scope (the four roles are too coarse; see Part 1).
2. The key permission line is cost data: purchase price, margin, supplier dues, staff pay, owner's udhaar/credit book are hidden from counter staff; the accountant sees books but not casual "what-if" tools.
3. STT default: faster-whisper `small` (multilingual), int8, CPU. Code and weights are MIT [V]. Force `language="hi"`, VAD on, domain initial prompt.
4. STT upgrade path: AI4Bharat IndicWhisper Hindi (Vistaar), MIT-licensed fine-tuned checkpoints [V], Hindi avg WER 13.6 vs Whisper-class models markedly worse [V for 13.6; U for Whisper comparison]. It is medium-sized (~769M, [U]), so convert to CTranslate2 int8 and expect ~2-3x slower than `small`.
5. Do not default to IndicConformer-600M (MIT [V], 22 languages, but needs NeMo/`trust_remote_code`, HF gated [V], heavy deps) or Tara (Apache-2.0 [V] but 1.55B Whisper-large-v3 based, too heavy for CPU interactive use [U]).
6. TTS: use browser `speechSynthesis` (hi-IN / en-IN) as default; no server model, no licence issue for us. Treat voice availability as best-effort and always show text.
7. AVOID Piper Hindi voices: two of three (pratham, priyamvada) cite a CC BY-NC-SA 4.0 dataset [V]; the third (rohan, IIT Madras IndicTTS) links a licence PDF I could not read [V]. Current Piper is GPL-3.0 [V].
8. Whisper on short Hindi commands hallucinates on silence, flips script (Urdu/Roman/English) and misdetects language [U]; mitigate with VAD, a minimum-duration gate, `no_speech_threshold`, a language hint and a post-check on the transcript.
9. UX: always show "I heard: ..." with Yes/Edit before answering; never act on a transcript alone; read numbers back; discard audio in memory after transcription (never write to disk).
10. Biggest unverified item: exact Whisper per-language Hindi WER from the paper (not retrieved); benchmark `small` vs IndicWhisper on 50 recorded shop commands before shipping.

---

## Part 1. Personas

Context [U]: Indian retail is dominated by small family-run shops; owners often also run the counter, use WhatsApp, UPI apps and a paper/Excel/Vyapar-style billing app; owners are comfortable in Hindi/regional language and Hinglish for numbers and product names, with English used for app labels. GST filing is commonly done by an outside CA or accountant who gets data via Tally exports or a monthly bundle of bills [U]. I did not find a single authoritative source page for each role description; descriptions below are from general knowledge unless tagged.

Permission vocabulary in the app: owner (everything), admin (operate and configure, no billing/ownership transfer), analyst (read all analytics, run what-ifs, no edit of master data), viewer (read selected dashboards). Gap: counter staff need less than "viewer" if viewer sees dashboards that include margin. Recommendation: add a scope flag `hide_costs` (and `hide_people`) that applies to any role; staff = viewer + hide_costs + hide_people + hide_credit.

### P1. Store owner (dukandaar / "seth")
- Goals [U]: know today's sales, cash, what to reorder, who owes money, which items are dead stock, whether the month is better than last.
- Language [U]: spoken Hindi/Gujarati/Marathi etc.; Hinglish for business words ("stock", "profit", "bill", "GST"); often types little, prefers voice; reads numbers fluently in Roman or Devanagari digits.
- Sees everything. Should NOT: have destructive actions one voice command away (delete data, change prices) without confirmation.
- Example questions (EN / Hinglish):
 1. How much did I sell today? / Aaj kitna bikri hua?
 2. What is my profit this month? / Is mahine ka munafa kitna hai?
 3. Which items are about to run out? / Kaun sa maal khatam hone wala hai?
 4. Who owes me money? / Kis kis se paisa lena hai?
 5. Which products are not selling? / Kaun sa saaman nahi bik raha?
 6. How does this month compare to last month? / Pichhle mahine se is mahine kaisa raha?
 7. What should I order this week? / Is hafte kya mangwana chahiye?
 8. Which supplier is giving me the best rate? / Kis supplier ka rate sabse achha hai?
- Role: owner.

### P2. Store / operations manager
- Goals [U]: keep shelves stocked, track staff attendance and targets, manage receiving and returns, run promotions, daily closing report.
- Language [U]: Hinglish plus English for reports; comfortable with spreadsheets and basic apps; may be a family member or a senior employee.
- Should see: stock, sales, reorder, expiry, staff performance counts. Should NOT see: owner's personal drawings, loan/credit book of the owner, other branches' staff pay unless delegated, purchase-price negotiations (owner discretion; default hidden, can be enabled).
- Questions:
 1. Which items are below reorder level? / Kaun se items reorder level se neeche hain?
 2. Which medicines expire in 30 days? / 30 din mein kaun si dawai expire hogi?
 3. Sales by salesperson today / Aaj kis staff ne kitna becha?
 4. Which shelf is dead stock? / Kaun sa maal kai mahine se nahi bika?
 5. How many returns this week? / Is hafte kitne return aaye?
 6. What sold most yesterday evening? / Kal shaam ko sabse zyada kya bika?
 7. Is there any stock mismatch? / Stock mein koi gadbad hai kya?
 8. Show Diwali-week forecast for sweets (generic: "festival week") / Tyohar ke hafte mein kitna maal lagega?
- Role: admin (with `hide_costs` default ON, owner can switch off).

### P3. Counter / billing staff (cashier, salesperson)
- Goals [U]: find price and stock for a customer right now, check if an item is available in another size/colour, suggest alternatives, see own sales.
- Language [U]: regional language/Hinglish; lowest literacy of the five; wants voice, short answers, big text; names products by brand or nickname ("Parle-G", "XL wala shirt").
- Should NOT see: purchase cost, margin, supplier names/dues, other staff's pay or sales ranking beyond own, owner's credit book/customer dues of others (privacy), total profit. Why: staff turnover is high [U] and cost price lets staff or customers undercut the owner's pricing; customer credit is personal and social-sensitive.
- Questions:
 1. Price of this item? / Iska rate kya hai?
 2. Is size L in stock? / L size hai kya?
 3. Do we have this in blue? / Ye neele rang mein hai?
 4. Any discount running? / Koi offer chal raha hai?
 5. How many are left? / Kitne piece bache hain?
 6. What goes with this phone? / Is phone ke saath kya dena chahiye?
 7. Is there a cheaper alternative? / Isse sasta koi hai kya?
 8. What did I sell today? / Maine aaj kitna becha?
- Role: viewer + `hide_costs`, `hide_people`, `hide_credit`; endpoints limited to item price/stock lookup and own sales.

### P4. Accountant / CA (view-only, usually external)
- Goals [U]: reconcile sales vs GST returns, check input tax credit, review payables/receivables, ageing, expense categorisation, year-end closing; needs traceable numbers, not recommendations.
- Language [U]: English accounting terms mixed with Hindi when talking to the owner; high literacy, wants exports (CSV/Excel) and period-bound reports.
- Should see: sales, purchases, taxes, receivables/payables ledgers, expenses. Should NOT: change data (view-only), see personal items outside the business books, see raw customer phone numbers unless needed (data minimisation), run what-if/pricing tools, or see staff pay beyond payroll totals unless owner shares. Access should be time-limited and logged.
- Questions:
 1. Total GST collected this quarter? / Is quarter mein kitna GST collect hua?
 2. Sales by tax rate (5/12/18%) / 5, 12, 18 percent ke hisaab se sales?
 3. Outstanding receivables aged over 60 days / 60 din se purane baaki kitne hain?
 4. Payables due this month / Is mahine kisko kitna dena hai?
 5. Purchases without a bill / Bina bill ki kharidari kaun si hai?
 6. Expense totals by category / Kharche category ke hisaab se?
 7. Cash vs UPI split / Cash aur UPI ka hisaab?
 8. Export March ledger / March ka khata nikalo.
- Role: viewer (finance scope: sales, purchases, tax, ageing; no staff/inventory-recommendation panels).

### P5. Data analyst / business partner (co-owner, consultant, franchise partner)
- Goals [U]: category performance, margin by product, price elasticity ideas, seasonality, cross-store comparison; wants drill-down and exports.
- Language [U]: English-first, analytical vocabulary; partners/family may use Hinglish.
- Should see: aggregated and item-level analytics including margins (that is the job), if the owner grants it. Should NOT: see individual customers' credit entries or phone numbers (use pseudonymised IDs), staff personal pay, edit data, access the voice/audio of staff, or export raw PII.
- Questions:
 1. Top 10 products by margin / Margin ke hisaab se top 10 items?
 2. Category trend over 6 months / 6 mahine mein category ka trend?
 3. Which discounts raised volume? / Kaun se discount se bikri badhi?
 4. Basket combinations that sell together / Kaun se items saath mein bikte hain?
 5. Weekend vs weekday sales / Weekend aur weekday ka farak?
 6. Stock turnover days by category / Kis category ka maal kitne din mein bikta hai?
 7. Compare store A and B / Store A aur B ki tulna?
 8. Forecast next month for category X / Agle mahine X category ki bikri?
- Role: analyst (cost visible if owner enables; PII masked).

### Permission matrix (default)
| Data | owner | admin(ops) | analyst | viewer(CA) | viewer(staff) |
|---|---|---|---|---|---|
| Sales, stock, price | yes | yes | yes | sales/tax only | price/stock, own sales |
| Purchase cost, margin | yes | opt-in | yes | purchase ledger only | no |
| Supplier dues | yes | opt-in | aggregate | yes | no |
| Customer credit (udhaar) | yes | opt-in | masked | ageing yes | no |
| Staff pay | yes | no | no | totals only | no |
| Config / users / delete | yes | partial | no | no | no |
| Voice input | yes | yes | yes | yes | yes |
Rationale [U]: least-privilege, DPDP-style purpose limitation for customer data, and the usual retail norm that margin knowledge is owner-controlled. Enforce on the server per endpoint; never rely on prompt wording to hide data from the assistant (filter the data given to it).

---

## Part 2. Voice for low-literacy users

### (a) Speech-to-text on CPU

Whisper sizes [V]: tiny 39M, base 74M, small 244M, medium 769M, large 1550M, turbo 809M; code AND weights MIT [V, openai/whisper README]. GPU VRAM column: ~1/1/2/5/10/6 GB [V]; the same figures are a rough CPU RAM guide in fp32 [U], int8 via CTranslate2 roughly halves it [V-partly: faster-whisper `small` int8 used 1477 MB vs 2257 MB fp32 in its benchmark].
faster-whisper [V]: MIT; `small`, 13 min audio, 8 threads i7-12700K, beam 5: fp32 2m37s, int8 1m42s (about 7.6x real time) with 1.5 GB RAM; openai/whisper fp32 6m58s. Silero VAD built in via `vad_filter`, default only drops silence >2 s unless `min_silence_duration_ms` tuned [V].
Per size, our rough int8 CPU expectation on a 4-core server [U]: tiny/base well under 0.1 RTF, small ~0.15-0.3, medium ~0.5-1.0. For 3-6 s commands, `small` should return in ~1-2 s, medium in 3-6 s [U]. Measure on the real server.

| Model | Licence (code / weights) | Size | CPU feasible | Hindi quality | Notes |
|---|---|---|---|---|---|
| Whisper tiny/base | MIT / MIT [V] | 39M/74M | yes, fast | poor on Hindi [U] | too many errors for commands |
| Whisper small | MIT / MIT [V] | 244M | yes (1.5 GB int8 [V]) | usable, errors on names/numbers [U] | RECOMMENDED default |
| Whisper medium | MIT / MIT [V] | 769M | slow-ish | better [U] | optional config |
| Whisper large-v3/turbo | MIT [V] | 1.5B / 809M | too slow on CPU [U] | best Whisper | no |
| IndicWhisper (AI4Bharat Vistaar) | MIT, "applies to all fine-tuned models" [V] | Whisper-medium class (~769M, [U]) | yes with CT2 int8 conversion [U] | Hindi avg WER 13.6; per set Kathbath 10.3, CV 11.4, FLEURS 15.0, Gramvaani (noisy phone) 26.8 [V]; beat Google 23.9, Azure 20.0 [V] | 12 languages incl. Marathi, Gujarati, Tamil, Bengali [V]; zip checkpoints hosted on E2E object store, not HF [V]; HF-Transformers format, not native faster-whisper [U] |
| IndicConformer 600M multi | MIT [V], HF gated (must share contact info) [V] | 600M hybrid CTC/RNNT | feasible (ONNX/CPU) [U] | 22 languages [V]; no WER obtained | needs `trust_remote_code`; README points to NeMo fork [V]; HF card recommends newer "Indic-Transcribe" [V], not evaluated |
| Vakyansh (EkStep) | repo MIT, but model/data licences not stated on page [V] | wav2vec2 class | feasible | not verified | skip unless licence confirmed |
| Tara (Trelis) | Apache-2.0 [V] | ~1.55B (Whisper-large-v3) [V] | too heavy for CPU realtime [U] | Vistaar Hindi mean 12.06 [V]; hi-en code-switch supported, English words in Latin script [V] | interesting later on GPU/queue |

Whisper paper per-language Hindi WER: not retrieved; I recall Hindi FLEURS WER in the 20s for large-v2 and worse for small [U]. Benchmark warning [V]: Whisper's default text normaliser distorts Devanagari matras and inflates WER; compare models with the same Devanagari-preserving normaliser.
Scripts/languages: Hindi in Devanagari is Whisper's native output. Romanised Hinglish ("aaj kitna bikri hua") is NOT a reliable Whisper output: it may produce Devanagari, English or garbled Roman text [U]. Do not fight this: transcribe to Devanagari, then let the NLU layer normalise (map Devanagari + English tokens to intents/entities; optionally transliterate to Roman with a permissive lib such as `indic-transliteration` [U, check licence]). Marathi/Gujarati/Tamil/Bengali: Whisper small is weak [U]; IndicWhisper covers all four [V].
Indian-accented English: Whisper small/base is fair [U]; set `language="en"` per user preference.

Recommendation:
- DEFAULT: faster-whisper `small`, `compute_type="int8"`, language hint from user profile (hi/en/mr/gu/ta/bn), beam_size 1-2, `vad_filter=True`. Weights MIT [V] (openai/whisper README states "code and model weights are released under the MIT License").
- UPGRADE: AI4Bharat IndicWhisper checkpoint for the user's language, converted with `ct2-transformers-converter --quantization int8`, MIT [V] per Vistaar README. Before adopting, check the specific checkpoint's own licence file because Vistaar says licence applies to the fine-tuned models but the training data (Kathbath etc.) carries its own terms [U]. A/B on 50 real shop recordings; ship only if exact-match on intents/numbers is clearly better.

### (b) Text-to-speech
- Browser `speechSynthesis` (Web Speech API) with `lang="hi-IN"` / `en-IN`: zero server cost, no model licence for us, audio never leaves the device when the voice is local [U]. Caveats [U]: voice list depends on OS/browser; Android Chrome and iOS usually have a Hindi voice, desktop Linux often does not; some Chrome "Google" voices are network voices (privacy: text, not audio, goes to Google); no Gujarati/Tamil on many devices. Feature-detect `getVoices()` for the language and fall back to text-only with a visible note.
- Piper: current Piper (OHF-Voice/piper1-gpl) is GPL-3.0 [V]: not allowed. The older rhasspy/piper was MIT [U] and the `piper-voices` HF repo is tagged MIT [V], but per-voice dataset terms differ: Hindi voices are pratham, priyamvada, rohan [V]. pratham and priyamvada model cards cite AI4Bharat IndicNLP data under CC BY-NC-SA 4.0 [V] (non-commercial and share-alike; reject). rohan is "Hindi Mono Male" from IIT Madras IndicTTS with a separate licence PDF [V] that I could not read; treat as unverified, do not ship.
- Other [U]: Meta MMS-TTS is CC-BY-NC (reject); Coqui TTS XTTS has a non-commercial licence (reject); AI4Bharat Indic-TTS/Vakyansh TTS weights have unclear terms (verify before use).
- Recommendation: browser SpeechSynthesis, answers kept to 1-2 short sentences, a "listen" button (never autoplay), numbers rendered as digits plus words ("एक हज़ार दो सौ रुपये"), and visible text always.

### (c) UX guidance for non-technical users
- Push-to-talk big button (hold or tap-tap), not always-on listening. Show a clear animated level meter so the user knows the mic works. Mic permission request preceded by one plain-language line in their language.
- Short noisy audio: record 16 kHz mono, require 0.7-8 s; if shorter or below an RMS/VAD threshold, say "सुनाई नहीं दिया, फिर से बोलिए" rather than transcribing. Add 300 ms pre-roll/post-roll so the first word is not clipped. Cap at ~15 s with auto-stop after ~1.2 s of silence (Silero VAD client-side via ONNX is an option [U]).
- Always confirm what was heard: show the transcript and the interpreted query as a plain sentence ("आज की बिक्री दिखा रहा हूँ?") with big Haan/Nahi buttons; low-confidence parse asks, high-confidence parse runs but remains editable. Never run state-changing actions from voice alone.
- Code-mixing: expect Hindi grammar with English nouns (stock, size, bill, GST, UPI). Maintain a lexicon mapping Devanagari and Roman variants ("स्टॉक"/"stock"/"stok") to canonical entities; fuzzy-match product names against the shop's own catalogue (rapidfuzz, MIT [U]).
- Numbers and names: Hindi number words (पचास, डेढ़, ढाई, सवा) and "lakh/crore" need a dedicated parser; read the parsed value back ("₹ 12,500"). Product/brand names are the top error source: constrain by catalogue and offer top-3 candidates as buttons.
- Language: let users pick their language once; allow switching with an icon, not a setting menu. Avoid jargon: say "मुनाफ़ा/profit", not "gross margin".
- Accessibility: large tap targets, high contrast, text equivalents for every voice feature, works without audio, adjustable speaking speed, support screen readers (ARIA live region for the transcript), do not rely on colour alone.
- Privacy: record in memory (MediaRecorder blob), send over TLS to our own server, transcribe, discard buffers immediately; no audio on disk, no logs of audio or raw transcripts by default (log only intent type and latency), no third-party ASR/TTS API calls. Tell the user so in one line. Transcripts may contain customer names: treat as personal data, apply the same role filters.

### (d) Whisper failure modes on short Hindi commands and mitigations (all [U] unless tagged)
| Failure | Cause | Mitigation |
|---|---|---|
| Hallucinated text on silence/noise ("Thanks for watching", subtitle credits, repeated phrases) | trained on web subtitles; short or empty input | VAD gate before Whisper [V: faster-whisper has Silero VAD]; reject audio under ~0.5 s of speech; `no_speech_threshold` ~0.6 with `log_prob_threshold` -1.0; `condition_on_previous_text=False`; blocklist of known hallucinations; discard if compression ratio > 2.4 |
| Wrong script (Urdu/Arabic script, Roman, or English translation of Hindi) | language auto-detect on <3 s of audio | pass `language="hi"`; `task="transcribe"` (never translate); check output script and re-run with the alternate language if the script mismatches |
| Language misdetection (Hindi heard as Urdu/Marathi/Punjabi etc.) | short clips, accents, code-mixing | per-user language hint; restrict detection to the shop's languages |
| Dropped or misspelt product names and numbers | rare words, spoken numerals | `initial_prompt` with domain vocabulary in the right script ("बिक्री, स्टॉक, मुनाफ़ा, उधार, GST, रिटेलर, बिल"); `hotwords` if the faster-whisper version supports it; post-correct by fuzzy match to the catalogue |
| Truncated first word | VAD or button latency | pre-roll buffer, VAD `speech_pad_ms` 300-400 |
| Slow first request | model load | load model at server start, keep warm; `cpu_threads` set; single shared instance with a queue |
| Prompt leakage (output echoes the prompt) | initial prompt too long | keep it under ~30 tokens, test with silence |
| Devanagari WER inflated in evaluation | normaliser [V] | evaluate with a Devanagari-preserving normaliser |
Validation plan: record 50-100 commands per persona with real shop noise, include silence and music-only clips, measure intent accuracy and hallucination rate, and gate rollout on a threshold set by the team.

## Sources
- openai/whisper README (MIT code and weights, sizes): https://github.com/openai/whisper
- faster-whisper (MIT, CPU benchmark, VAD): https://github.com/SYSTRAN/faster-whisper
- AI4Bharat Vistaar / IndicWhisper (MIT, Hindi WER table): https://github.com/AI4Bharat/vistaar ; paper https://arxiv.org/abs/2305.15386
- IndicConformer: https://github.com/AI4Bharat/IndicConformerASR ; https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual
- Tara (Apache-2.0): https://huggingface.co/Trelis/tara
- Vakyansh models: https://github.com/Open-Speech-EkStep/vakyansh-models
- Piper voices and model cards: https://huggingface.co/rhasspy/piper-voices/tree/main/hi/hi_IN ; https://github.com/OHF-Voice/piper1-gpl
- Whisper paper (not read; Appendix D per-language WER): https://arxiv.org/abs/2212.04356
- Persona descriptions: no single source page read; from general knowledge of Indian SMB retail practice [U].
