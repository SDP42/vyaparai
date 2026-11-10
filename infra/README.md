# infra

Deployment lives at the repository root so one command starts it:

- `docker-compose.yml` PostgreSQL, Redis, API and web (`make up`)
- `apps/api/Dockerfile`, `apps/web/Dockerfile`
- `.env.production.example` the variables to fill in
- `scripts/backup.sh`, `scripts/restore-check.sh` backup and restore proof (`make backup`)
- [docs/RUNBOOK.md](../docs/RUNBOOK.md) deploy, back up, restore, roll back, incidents

Nothing here has been run on a real server yet; see the runbook's first line.
