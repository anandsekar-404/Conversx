#!/usr/bin/env bash
# =============================================================================
# scripts/backup_postgres.sh
# Production Automated PostgreSQL Backup Script
#
# Creates timestamped, gzip-compressed backups with configurable retention.
# Detects failure and exits with non-zero status.
# =============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/conversx}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/conversx_backup_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[backup] Starting PostgreSQL backup at $(date -u)..."

# Ensure postgres container is running
if ! docker ps --filter "name=conversx-postgres" --filter "status=running" -q | grep -q .; then
    echo "[backup ERROR] conversx-postgres container is not running!" >&2
    exit 1
fi

# Run pg_dump from inside container and stream through gzip
if docker exec conversx-postgres pg_dump -U "${POSTGRES_USER:-conversx}" "${POSTGRES_DB:-conversx}" | gzip -c > "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || echo "0")
    if [ "${BACKUP_SIZE}" -le 50 ]; then
        echo "[backup ERROR] Backup file is suspiciously small (${BACKUP_SIZE} bytes). Possible failure!" >&2
        rm -f "${BACKUP_FILE}"
        exit 1
    fi
    echo "[backup SUCCESS] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE} bytes)"
else
    echo "[backup ERROR] pg_dump execution failed!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Retention policy: remove backups older than RETENTION_DAYS
echo "[backup] Enforcing retention policy: deleting backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "conversx_backup_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -exec rm -f {} +

echo "[backup] Backup job finished successfully."
