#!/usr/bin/env bash
# Prove a backup can be restored: load it into a throw-away database and count the rows. Run from the repo root.
set -euo pipefail
DUMP="${1:?usage: restore-check.sh path/to/db-YYYYmmdd-HHMMSS.dump}"
docker compose exec -T db psql -U vyapar -d postgres -c "DROP DATABASE IF EXISTS restore_check;" -c "CREATE DATABASE restore_check;"
docker compose exec -T db pg_restore -U vyapar -d restore_check --no-owner < "$DUMP"
docker compose exec -T db psql -U vyapar -d restore_check -tAc "SELECT 'users', count(*) FROM users UNION ALL SELECT 'workspaces', count(*) FROM workspaces UNION ALL SELECT 'orders', count(*) FROM orders;"
docker compose exec -T db psql -U vyapar -d postgres -c "DROP DATABASE restore_check;"
echo "Restore check passed for $DUMP"
