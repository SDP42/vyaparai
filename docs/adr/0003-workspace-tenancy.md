# 0003 · Workspace as tenant; non-members get 404

- **Date:** 2026-11-07 · **Status:** Accepted

**Context.** Multi-user workspaces are a later feature, but retrofitting tenancy is expensive and risky.

**Decision.** Every business-owned table has `workspace_id`. Routes are nested under
`/workspaces/{workspace_id}`. A `WorkspaceContext` dependency loads the caller's membership;
`require_role(min)` enforces owner > admin > analyst > viewer. Tenant queries go through
`WorkspaceScopedRepository`. A non-member gets **404**, not 403, so workspace IDs can't be probed.

**Consequences.** Every new endpoint gets isolation by default. Tests must cover each new tenant
resource (pattern in `tests/test_tenancy.py`). PostgreSQL RLS may be added later as defence in depth.
