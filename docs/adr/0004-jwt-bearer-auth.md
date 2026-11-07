# 0004 · Short-lived JWT bearer tokens for the MVP

- **Date:** 2026-11-07 · **Status:** Accepted (revisit in Phase F2)

**Decision.** Argon2id password hashing (`pwdlib`), HS256 JWT access tokens valid for 30 minutes,
OAuth2 password flow so Swagger's "Authorize" works. Login is timing-equalised for unknown emails.

**Consequences.** Simple and testable. There is no refresh or revocation yet. Before public use,
the web app moves to an HttpOnly, SameSite cookie with refresh-token rotation and CSRF protection.
