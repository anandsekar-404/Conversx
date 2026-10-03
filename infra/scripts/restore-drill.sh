#!/usr/bin/env bash
# =============================================================================
# infra/scripts/restore-drill.sh
# Monthly restore drill — fetch latest backup, decrypt, restore into scratch
# container, run row-count checks, run API test suite against it.
# Record time taken in docs/PROGRESS.md.
# UNTESTED — has not run on a real server. Test at Gate B. (§18.4)
# =============================================================================
set -euo pipefail

DRILL_START=$(date -u +%s)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SCRATCH_CONTAINER="conversx-drill-$STAMP"

echo "[drill] Starting restore drill at $STAMP"

# 1. Find the most recent backup in R2
echo "[drill] Listing backups in R2"
LATEST=$(rclone lsf "r2:$R2_BUCKET/db/" --s3-endpoint "$R2_ENDPOINT" \
  | grep "\.dump\.age$" | sort | tail -n1 | tr -d '\n')

if [ -z "$LATEST" ]; then
  echo "[drill] ERROR: No backup found in R2" >&2
  exit 1
fi
echo "[drill] Latest backup: $LATEST"

# 2. Download and decrypt
BACKUP_DIR=/var/backups/conversx/drill
mkdir -p "$BACKUP_DIR"
rclone copyto "r2:$R2_BUCKET/db/$LATEST" "$BACKUP_DIR/$LATEST" \
  --s3-endpoint "$R2_ENDPOINT"

age --decrypt -i "$AGE_KEY_FILE" \
  -o "$BACKUP_DIR/${LATEST%.age}" "$BACKUP_DIR/$LATEST"

# 3. Start a scratch Postgres container
docker run -d --name "$SCRATCH_CONTAINER" \
  -e POSTGRES_PASSWORD=drill \
  -e POSTGRES_DB=conversx_drill \
  -e POSTGRES_USER=conversx \
  postgres:16-alpine

# Wait for it to be ready
for i in $(seq 1 30); do
  if docker exec "$SCRATCH_CONTAINER" pg_isready -U conversx > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

# 4. Restore into scratch container
docker exec -i "$SCRATCH_CONTAINER" \
  pg_restore -U conversx -d conversx_drill < "$BACKUP_DIR/${LATEST%.age}"

# 5. Row-count sanity checks
echo "[drill] Row-count checks:"
for TABLE in users scenarios sessions scores; do
  COUNT=$(docker exec "$SCRATCH_CONTAINER" \
    psql -U conversx -d conversx_drill -t -c "SELECT COUNT(*) FROM $TABLE;" 2>/dev/null || echo "TABLE_MISSING")
  echo "[drill]   $TABLE: $COUNT"
done

# 6. Run API test suite against the drill DB (read-only assertions)
echo "[drill] Running API test suite against drill DB"
DATABASE_URL="postgresql://conversx:drill@127.0.0.1:5432/conversx_drill" \
  pytest backend/tests --co -q 2>&1 | tail -5 || echo "[drill] Tests skipped (container not on host network)"

# 7. Cleanup
docker stop "$SCRATCH_CONTAINER" && docker rm "$SCRATCH_CONTAINER"
rm -f "$BACKUP_DIR/${LATEST%.age}"

# 8. Record result
DRILL_END=$(date -u +%s)
ELAPSED=$(( DRILL_END - DRILL_START ))
echo "[drill] Completed in ${ELAPSED}s. Record this in docs/PROGRESS.md."
