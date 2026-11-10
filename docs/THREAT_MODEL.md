# Threat model

| Threat | Mitigation (status) |
|---|---|
| **Tenant data leakage** | `workspace_id` on every tenant table; `WorkspaceScopedRepository`; membership checked per request; non-members get 404; tests in `tests/test_tenancy.py` ✅ |
| **Privilege escalation** | Role hierarchy; admins cannot grant owner; RBAC tests ✅ |
| **Credential stuffing / brute force** | Argon2id hashing ✅; timing-equalised login ✅; rate limiting ⬜ (Phase 11) |
| **Account enumeration** | Same error + timing for unknown email and wrong password ✅ (registration still reveals existing emails, documented trade-off) |
| **Path traversal via filenames** | Only the base name is kept for display; stored files are named by UUID ✅ |
| **Duplicate / replayed imports** | SHA-256 file hash unique per workspace; orders skipped by `(workspace, external_key)` on re-import ✅ |
| **Half-imported data** | Import runs in one transaction; failures roll back and are recorded on the job ✅ |
| **Token theft** | Access JWT lives 15 min and only in page memory ✅; the refresh token is random, stored as a SHA-256 hash, sent as an HttpOnly SameSite=Lax cookie limited to `/api/v1/auth` (Secure in production), rotated on every use; reuse of an old token revokes the whole sign-in family; 14-day idle and 30-day absolute limits; logout and sign-out-everywhere revoke server-side ✅. Cookie endpoints also require `X-Requested-With: vyapar` and a known `Origin` (CSRF) ✅. Login is throttled (5 failures per 15 min per address and per account) and registration (10 per hour per address) ✅. The counters are in memory, so they reset on restart and are per process: move them to Redis before running more than one worker (Phase 11) |
| **Weak production config** | App refuses to start in production with the dev JWT secret or SQLite ✅ |
| **Secrets in Git** | `.env` ignored; `.env.example` only ✅ |
| **Malicious uploads** | 25 MB / 200k-row limits, extension + file-signature checks, streamed size cap, `.xlsx` opened read-only with `data_only` (no macros/formulas run), stored outside the web root under `STORAGE_DIR/{workspace}/`, analyst role required ✅; antivirus scan and upload fuzzing ⬜ (Phase 11) |
| **SSRF via connected links** | https only, host allow-list, one DNS resolution with every address required to be public, connection pinned to that address, redirects re-checked per hop (max 3), size and time caps, HTML refused, internal addresses never shown in errors; tested with loopback, private, metadata, multicast and IPv4-mapped addresses and against live DNS ✅; network egress isolation for production ⬜ (Phase 11) |
| **SQL injection** | ORM/parameterised queries only ✅; agents get no raw SQL; allow-listed metric API ⬜ (Phase 8) |
| **Prompt injection via documents** | Retrieved text treated as data; permission filter before retrieval; adversarial test docs ⬜ (Phase 7) |
| **Unsafe agent actions** | Read-only tools; human approval for any write; no purchases ⬜ (Phase 9) |
| **XSS / CSRF** | React escaping; no `dangerouslySetInnerHTML`; CSRF protection when moving to cookies ⬜ |
| **Log leakage** | Structured logs without request bodies or passwords ✅; PII redaction ⬜ |
| **Dependency risk** | Locked deps (`uv.lock`, `package-lock.json`) ✅; automated audit in CI ⬜ |
