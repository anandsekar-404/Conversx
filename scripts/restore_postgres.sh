#!/usr/bin/env bash
# =============================================================================
# scripts/restore_postgres.sh
# Production PostgreSQL Database Restore Script
#
# Restores a compressed .sql.gz backup into conversx-postgres container
# =============================================================================
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 /path/to/conversx_backup_TIMESTAMP.sql.gz" >&2
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[restore ERROR] Backup file does not exist: ${BACKUP_FILE}" >&2
    exit 1
fi

echo "[restore] Verifying archive integrity..."
gzip -t "${BACKUP_FILE}"

echo "[restore] Restoring database from ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | docker exec -i conversx-postgres psql -U "${POSTGRES_USER:-conversx}" "${POSTGRES_DB:-conversx}"

echo "[restore] Running post-restore table verification..."
docker exec -i conversx-postgres psql -U "${POSTGRES_USER:-conversx}" "${POSTGRES_DB:-conversx}" -c "\dt"

echo "[restore SUCCESS] Database restored and verified successfully."
