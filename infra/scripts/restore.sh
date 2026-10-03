#!/usr/bin/env bash
# =============================================================================
# infra/scripts/restore.sh
# Restore a specific backup from R2 into the running postgres container.
# UNTESTED — has not run on a real server. Test at Gate B. (§18.4)
#
# Usage:
#   ./restore.sh <backup-filename>
#   e.g.: ./restore.sh db-20261001T120000Z.dump.age
#
# Required env vars: R2_ENDPOINT, R2_BUCKET, AGE_KEY_FILE (path to age private key)
# =============================================================================
set -euo pipefail

BACKUP_FILE="${1:?Usage: restore.sh <backup-filename>}"
BACKUP_DIR=/var/backups/conversx
LOCAL_AGE="$BACKUP_DIR/$BACKUP_FILE"
LOCAL_DUMP="$BACKUP_DIR/${BACKUP_FILE%.age}"

mkdir -p "$BACKUP_DIR"

echo "[restore] Downloading $BACKUP_FILE from R2"
rclone copyto "r2:$R2_BUCKET/db/$BACKUP_FILE" "$LOCAL_AGE" \
  --s3-endpoint "$R2_ENDPOINT"

echo "[restore] Decrypting with age private key"
age --decrypt -i "$AGE_KEY_FILE" -o "$LOCAL_DUMP" "$LOCAL_AGE"

echo "[restore] Restoring into postgres container"
echo "WARNING: This will DROP and recreate the database. Press Ctrl-C within 10s to cancel."
sleep 10

docker compose -f /opt/conversx/infra/docker-compose.yml \
  exec -T postgres \
  psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_restore;"

docker compose -f /opt/conversx/infra/docker-compose.yml \
  exec -T postgres \
  psql -U "$POSTGRES_USER" -c "CREATE DATABASE ${POSTGRES_DB}_restore;"

docker compose -f /opt/conversx/infra/docker-compose.yml \
  exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "${POSTGRES_DB}_restore" < "$LOCAL_DUMP"

echo "[restore] Done. Restored into ${POSTGRES_DB}_restore. Review before swapping to ${POSTGRES_DB}."
echo "[restore] To swap: rename via psql, restart API."

# Clean up decrypted file immediately
rm -f "$LOCAL_DUMP"
echo "[restore] Decrypted dump deleted."
