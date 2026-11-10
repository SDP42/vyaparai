#!/usr/bin/env bash
# Back up PostgreSQL and uploaded files. Run from the repo root: ./scripts/backup.sh [backup-dir]
# Keep copies off the machine (another disk, cloud storage). A backup you have never restored is a hope, not a backup:
# run ./scripts/restore-check.sh regularly.
set -euo pipefail
DIR="${1:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DIR"
docker compose exec -T db pg_dump -U vyapar --format=custom vyapar > "$DIR/db-$STAMP.dump"
docker compose cp api:/data/storage - | gzip > "$DIR/files-$STAMP.tar.gz"
# keep the 14 newest of each
ls -1t "$DIR"/db-*.dump 2>/dev/null | tail -n +15 | xargs -r rm --
ls -1t "$DIR"/files-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm --
echo "Backed up to $DIR ($STAMP)"
