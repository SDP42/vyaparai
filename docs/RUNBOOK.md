# Runbook

How to deploy, check, back up, restore and recover Vyapar AI. Written for one person running one small server.
**Not yet rehearsed on a real server**: the Docker files, compose stack and scripts were written and syntax-checked
here, but Docker and PostgreSQL were not available in the build environment, so treat the first deployment as a rehearsal.

## What runs

| Part | Image | Notes |
|---|---|---|
| `db` | postgres:16-alpine | data in the `dbdata` volume |
| `redis` | redis:7-alpine | rate-limit counters only; losing it loses nothing important |
| `api` | `apps/api/Dockerfile` | runs `alembic upgrade head` on start, then uvicorn with 2 workers; uploaded files in `/data/storage`, downloaded search model in `/data/models` |
| `web` | `apps/web/Dockerfile` | Next.js standalone server; the API address is baked in at build (`PUBLIC_API_URL`) |
| agent runner | the `api` image | not a service: add `*/15 * * * * docker compose exec -T api python -m app.agent_runner` to the host's cron so scheduled automations run |

TLS, the domain and routing `/api` to the API and everything else to the web app belong to a proxy in front (Caddy, nginx or a cloud load balancer). Cookies are `Secure` in production, so HTTPS is required.

## First deployment

1. `cp .env.production.example .env` and fill in `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (48+ random characters), `PUBLIC_URL` (https), `PUBLIC_API_URL`.
2. `docker compose up -d --build`. The API refuses to start if production settings are unsafe (short secret, SQLite, non-https origins).
3. Check `curl -s http://127.0.0.1:8000/api/v1/health/ready` returns 200, then open the site and register the first owner account.
4. The first document search or bill read downloads the search model (about 220 MB) once. The first spoken question downloads the Whisper weights into the same `models` volume (about 1.5 GB for `medium`; the API loads them at start-up when it can). Voice needs roughly 2 GB of free memory with `medium`; on a smaller server set `STT_MODEL=small` or `VOICE_ENABLED=false`. Never set `DEMO_LOGIN_ENABLED` here: the API refuses to start with it on.

## Everyday checks

- `docker compose ps` (all healthy), `docker compose logs -f api` (JSON lines with a `request_id`; a user's error message carries the same id).
- Disk: the `dbdata`, `storage` and `models` volumes. Alert before 80%.
- Rate limits: 600 requests a minute and 60 expensive ones (uploads, search, questions, investigations, reports) per address. `429` with `Retry-After` means a limit was hit. Behind a proxy keep `TRUST_PROXY=true` so the real address is used.

## Backups

- `./scripts/backup.sh` writes `db-<time>.dump` (PostgreSQL custom format) and `files-<time>.tar.gz` and keeps the 14 newest. Schedule it daily (cron) and **copy the files off the machine**.
- `./scripts/restore-check.sh backups/db-<time>.dump` restores into a throw-away database and counts users, workspaces and orders. Run it monthly. A backup that has never been restored is unproven.
- To really restore: stop the `api`, `docker compose exec -T db pg_restore -U vyapar -d vyapar --clean --no-owner < backups/db-<time>.dump`, restore the files archive into `/data/storage`, start the `api`.

## Upgrading and rolling back

1. Back up first.
2. `git pull`, `docker compose up -d --build`. Migrations run on API start.
3. Roll back the code: `git checkout <previous tag>` and rebuild. If the new version added a migration, downgrade first: `docker compose run --rm api alembic downgrade -1` (once per migration), then deploy the old code. Migrations were written to be reversible; destructive ones say so in their file.

## Incidents

| Symptom | Look at | Do |
|---|---|---|
| Site down | `docker compose ps`, proxy | restart the failed service; `docker compose logs api` |
| Everyone gets 401 | `JWT_SECRET_KEY` changed? | restore the old secret; changing it signs everyone out (intended) |
| Many 429 | proxy not forwarding the client address | set `TRUST_PROXY=true`; check `X-Forwarded-For` |
| Slow or timing-out pages | database CPU, long queries | PostgreSQL stops any statement over 15 s (`DB_STATEMENT_TIMEOUT_MS`); find the query in the logs |
| Uploads rejected with 413 | size limits | JSON 1 MB, uploads 20 MB; raise `MAX_*` only if needed |
| Search or bill reading says "not available" | `/data/models`, internet access for the first download | allow the download once, or copy the model files into the volume |
| Suspected leaked secret | | rotate `JWT_SECRET_KEY` (signs everyone out), rotate `POSTGRES_PASSWORD`, review the audit log (`/workspaces/{id}/audit-logs`) |

## Secrets

Only in `.env` on the server (not in git). Rotation: edit `.env`, `docker compose up -d`. SMTP credentials are optional and only used to email digests and reminders.

## Dependency audit

Run before each release: `uv export --no-hashes --no-dev > r.txt && uvx pip-audit --disable-pip --no-deps -r r.txt` and `npm audit --omit=dev` in `apps/web`. On 2026-11-11 the Python set had no known vulnerabilities; `npm audit` listed PostCSS inside Next 15 (it processes our own stylesheets at build time, not user input), accepted until Next 16.

## Security posture and known gaps

- Headers on every API response (no sniffing, no framing, CSP `default-src 'none'`, HSTS in production); the web app sets a strict CSP, no framing and HSTS. Request bodies over the limit are refused before they are read; chunked bodies without a length are bounded by the server and proxy limits.
- Hostile-file tests (binary junk, truncated PDFs and DOCX, UTF-16, very long lines, injection strings) run against every upload endpoint and must never produce a server error.
- Dependency audit (run on the build date, 2026-11-10): `pip-audit` found no known vulnerabilities in the Python packages. `npm audit --omit=dev` reports PostCSS issues inside Next.js. PostCSS runs at build time on our own stylesheets, not on user input, and the fix needs a breaking Next 16 upgrade, so this is an **accepted, tracked risk** until that upgrade.
- Not done: automated alerting, log shipping, a staging environment, load testing, penetration testing, and a rehearsal of the restore on a second machine.
