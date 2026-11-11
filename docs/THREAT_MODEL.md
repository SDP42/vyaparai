# Threat model

Status as of 2026-11-11. ✅ built and tested · 🟡 built, with a stated gap · ⬜ not done. Each row names where it is
tested or implemented. A threat model is a list of what was considered, not a promise that nothing was missed; there
has been no external penetration test.

## Assets and trust boundaries

- **Assets:** a shop's sales, costs and margins, customer keys and consented phone numbers, the credit (udhaar) book,
  supplier bills, uploaded documents, account credentials, and recorded voice (briefly, in memory).
- **Boundaries:** the browser (untrusted), the API (trusted), the database and files on the server (trusted), model
  files downloaded once from public hosts, connected Google Sheet links and any text inside uploaded files or reviews
  (untrusted data).

## Threats and mitigations

| Threat | Mitigation (status) |
|---|---|
| **Tenant data leakage** | `workspace_id` on every tenant table; workspace-scoped queries; membership checked on every request; a non-member gets a 404 on every route; isolation tests across areas (`tests/test_tenancy.py` and per-area tests) ✅ |
| **Privilege escalation** | Role hierarchy; admins cannot grant or change owners; a persona must fit the role and never widens it; role and persona tests ✅ |
| **A job seeing data it should not** (counter staff reading margin or credit) | Persona capabilities guard the credit, cost, pricing, supplier-bill, report, customer and staff routes with a 403; cost and margin fields are emptied per field on mixed-data routes; the assistant refuses out-of-remit questions before any tool runs. `tests/test_personas.py`, `tests/test_masking.py` ✅. 🟡 Text that mentions a margin (a recommendation sentence) is not rewritten |
| **Credential stuffing and brute force** | Argon2id hashing; timing-equalised login; sign-in and registration throttles per address and per account; shared limits through Redis when configured (fails open if Redis is down) ✅ |
| **Account enumeration** | Same error and timing for an unknown email and a wrong password ✅ (registration still reveals existing emails: documented trade-off) |
| **Token theft** | Access JWT lives 15 min and only in page memory ✅; the refresh token is random, stored as a SHA-256 hash, sent as an HttpOnly SameSite=Lax cookie limited to `/api/v1/auth` (Secure in production), rotated on every use; reuse of an old token revokes the whole sign-in family; 14-day idle and 30-day absolute limits; logout and sign-out-everywhere revoke server-side ✅. Cookie endpoints also require `X-Requested-With: vyapar` and a known `Origin` (CSRF) ✅. Login is throttled (5 failures per 15 min per address and per account) and registration (10 per hour per address) ✅. Counters live in Redis when `REDIS_URL` is set (shared by every worker; if Redis is down the limiter lets requests through and logs it) and in memory otherwise ✅. All requests are also limited per address (600 a minute, 60 for expensive endpoints), request bodies over 1 MB (20 MB for uploads) are refused unread, API responses carry nosniff, no-framing and a locked-down CSP, HSTS in production, and PostgreSQL stops any statement over 15 s ✅ |
| **Session replay** | Refresh tokens rotate on every use; reuse of a used token revokes the whole family; idle (14 days) and absolute (30 days) limits; "sign out everywhere" ✅ |
| **CSRF** | The refresh and demo-login routes require a custom header and an Origin check; the API otherwise uses bearer tokens, not cookies ✅ |
| **XSS** | React escaping; no `dangerouslySetInnerHTML`; strict security headers on every response ✅ |
| **Path traversal via filenames** | Only the base name is kept for display; stored files are named by UUID ✅ |
| **Duplicate or replayed imports** | SHA-256 file hash unique per workspace; orders skipped by `(workspace, external_key)` on re-import ✅ |
| **Half-imported data** | Import runs in one transaction; failures roll back and are recorded on the job ✅ |
| **Malicious uploads** | 25 MB / 200k-row limits, extension + file-signature checks, streamed size cap, `.xlsx` opened read-only with `data_only` (no macros/formulas run), stored outside the web root under `STORAGE_DIR/{workspace}/`, analyst role required ✅; antivirus scan and upload fuzzing ⬜ (Phase 11) |
| **Oversized or abusive requests** | Body caps (1 MB JSON, 20 MB multipart, about 1 MB for a voice clip) refused before reading; per-address limits, lower on heavy routes (uploads, search, questions, voice, investigations, reports) ✅ |
| **SSRF via connected links** | https only, host allow-list, one DNS resolution with every address required to be public, connection pinned to that address, redirects re-checked per hop (max 3), size and time caps, HTML refused, internal addresses never shown in errors; tested with loopback, private, metadata, multicast and IPv4-mapped addresses and against live DNS ✅; network egress isolation for production ⬜ (Phase 11) |
| **SQL injection** | ORM and parameterised queries only; no raw SQL anywhere an agent or user text can reach; injection strings in text fields are stored as text (`tests/test_hardening.py`) ✅ |
| **Prompt injection via documents and reviews** | There is no generative model: retrieved text is quoted back as data and can never steer a workflow; permission filter before retrieval; an adversarial-document test ✅ |
| **Unsafe automated actions** | Workflows and the assistant are read-only (a test fails if the workflow module contains writes, network or process calls); nothing is sent, ordered or changed without a person; messages are drafts a person sends ✅ |
| **Voice audio privacy** | Audio is decoded and transcribed in memory and discarded; never written to disk, never logged (only durations); no third-party speech service; the words are shown to the person before anything is asked; over-long or over-large clips are refused ✅. 🟡 The browser may use a network voice for read-aloud on some devices; only answer text, not audio, would leave the device |
| **Model supply chain** | Models are downloaded once from named public repositories (Whisper from `Systran`, MiniLM through fastembed) and cached; `STT_LOCAL_FILES_ONLY` stops any fetch on a locked-down server; licences recorded in `docs/LICENSES.md`. 🟡 Weights are not checksum-pinned |
| **Demo accounts reaching production** | `DEMO_LOGIN_ENABLED` is refused at start-up when `APP_ENV=production`; the route answers 404 when off; sample accounts have random unknown passwords; shares the sign-in throttle ✅ |
| **Weak production configuration** | The app refuses to start in production with the dev JWT secret, a short secret, SQLite, non-https origins or demo login on ✅ |
| **Secrets in Git** | `.env` ignored, `.env.example` and `.env.production.example` only; no keys in the repository ✅ |
| **Log leakage** | Structured logs without request bodies, passwords, transcripts or audio ✅. 🟡 No automated PII redaction beyond that |
| **Dependency risk** | Locked dependencies (`uv.lock`, `package-lock.json`); a licence audit test; `pip-audit` in CI and run before release (clean on 2026-11-11); `npm audit` in CI is informational: PostCSS inside Next 15 is accepted until Next 16 ✅ |
| **Outside review** | ⬜ No penetration test or third-party review has been done |
