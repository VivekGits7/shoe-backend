#!/usr/bin/env bash
#
# Daily PostgreSQL backup for shoe-backend.
# Dumps the whole DB (custom/compressed format) into backups/ and keeps the last N days.
#
# Run manually:   ./scripts/backup_db.sh
# Restore later:  pg_restore --clean --if-exists -h HOST -p PORT -U USER -d DB backups/<file>.dump
#
# Cron (daily at 02:00) — edit `crontab -e` and add (absolute path to this repo):
#   0 2 * * * cd /Users/vivek/Documents/Codehub/shoe-backend && ./scripts/backup_db.sh >> logs/backup.log 2>&1
#
# Requires pg_dump on PATH (install: `brew install libpq` then add its bin to PATH).

set -euo pipefail

# Move to the project root (parent of scripts/) so relative paths + .env resolve.
cd "$(dirname "$0")/.."

# Load DB credentials from .env without printing them.
set -a
# shellcheck disable=SC1091
source .env
set +a

BACKUP_DIR="backups"
RETENTION_DAYS=14   # keep this many recent dumps; older ones are pruned

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTFILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.dump"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup of '${POSTGRES_DB}' -> ${OUTFILE}"

# -Fc = custom compressed format (supports selective pg_restore). PGPASSWORD avoids URL-encoding the password.
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  -h "$POSTGRES_DB_HOST" \
  -p "$POSTGRES_DB_PORT" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -Fc \
  -f "$OUTFILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete: $(du -h "$OUTFILE" | cut -f1) -> ${OUTFILE}"

# Prune dumps older than RETENTION_DAYS.
find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.dump" -type f -mtime "+${RETENTION_DAYS}" -print -delete \
  | sed 's/^/[pruned] /' || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Done. Current backups:"
ls -1t "$BACKUP_DIR"/*.dump 2>/dev/null | head -5 | sed 's/^/  /'
