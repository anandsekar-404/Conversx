#!/usr/bin/env bash
# =============================================================================
# infra/scripts/backup.sh
# Daily backup: pg_dump → age-encrypt → upload to R2 (+ optional B2).
# UNTESTED — has not run on a real server. Test at Gate B. (§18.4)
#
# Required env vars (from .env on the VM, NOT in git):
#   POSTGRES_USER, POSTGRES_DB, AGE_RECIPIENT, R2_ENDPOINT, R2_BUCKET,
#   AWS_ACCESS_KEY_ID (= R2_ACCESS_KEY_ID), AWS_SECRET_ACCESS_KEY,
#   HEALTHCHECK_PING_URL
#   Optional: B2_BUCKET, B2_KEY_ID, B2_APPLICATION_KEY
# =============================================================================
set -euo pipefail

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=/var/backups/conversx
OUT="$BACKUP_DIR/db-$STAMP.dump.age"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting pg_dump at $STAMP"
docker compose -f /opt/conversx/infra/docker-compose.yml \
  exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" \
  | age -r "$AGE_RECIPIENT" > "$OUT"

echo "[backup] Uploading to R2: $R2_BUCKET"
rclone copyto "$OUT" "r2:$R2_BUCKET/db/$(basename "$OUT")" \
  --s3-endpoint "$R2_ENDPOINT"

# Optional: second copy to Backblaze B2
if [ -n "${B2_BUCKET:-}" ]; then
  echo "[backup] Uploading to B2: $B2_BUCKET"
  rclone copyto "$OUT" "b2:$B2_BUCKET/db/$(basename "$OUT")"
fi

# Retention: keep 7 daily, 4 weekly, 3 monthly
# Simple implementation: delete files older than 90 days locally
find "$BACKUP_DIR" -type f -name "*.dump.age" -mtime +90 -delete

# Raw audio is NEVER included in backups (§11)
# Verify no audio files snuck in
if find "$BACKUP_DIR" -name "*.webm" -o -name "*.wav" -o -name "*.mp3" | grep -q .; then
  echo "[backup] ERROR: audio file found in backup dir!" >&2
  exit 1
fi

# Dead-man's-switch ping — failure to ping alerts the monitoring system
curl -fsS "$HEALTHCHECK_PING_URL" > /dev/null
echo "[backup] Done — dead-man's-switch pinged"
