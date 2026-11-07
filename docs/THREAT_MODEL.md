# Threat model

| Threat | Mitigation (status) |
|---|---|
| **Tenant data leakage** | `workspace_id` on every tenant table; `WorkspaceScopedRepository`; membership checked per request; non-members get 404; tests in `tests/test_tenancy.py` ✅ |
| **Privilege escalation** | Role hierarchy; admins cannot grant owner; RBAC tests ✅ |
| **Credential stuffing / brute force** | Argon2id hashing ✅; timing-equalised login ✅; rate limiting ⬜ (Phase 11) |
| **Account enumeration** | Same error + timing for unknown email and wrong password ✅ (registration still reveals existing emails, documented trade-off) |
| **Token theft** | Short-lived JWT (30 min) ✅; HttpOnly cookie + refresh rotation ⬜ (F2) |
| **Weak production config** | App refuses to start in production with the dev JWT secret or SQLite ✅ |
| **Secrets in Git** | `.env` ignored; `.env.example` only ✅ |
| **Malicious uploads** | Size/row limits, magic-byte checks, no macro execution, stored outside web root ⬜ (Phase 1) |
| **SQL injection** | ORM/parameterised queries only ✅; agents get no raw SQL; allow-listed metric API ⬜ (Phase 8) |
| **Prompt injection via documents** | Retrieved text treated as data; permission filter before retrieval; adversarial test docs ⬜ (Phase 7) |
| **Unsafe agent actions** | Read-only tools; human approval for any write; no purchases ⬜ (Phase 9) |
| **XSS / CSRF** | React escaping; no `dangerouslySetInnerHTML`; CSRF protection when moving to cookies ⬜ |
| **Log leakage** | Structured logs without request bodies or passwords ✅; PII redaction ⬜ |
| **Dependency risk** | Locked deps (`uv.lock`, `package-lock.json`) ✅; automated audit in CI ⬜ |
