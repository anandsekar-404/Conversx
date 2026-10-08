# ConversX — PostgreSQL Automated Backup & Recovery Guide

## 1. Overview & Strategy

The ConversX PostgreSQL database stores user accounts, practice attempts, delivery metrics, moderation audit events, and user appeals. In accordance with ConversX privacy standards, raw user audio and raw communication transcripts are never stored.

This document details the automated backup creation, storage, retention, restore procedure, and disaster recovery verification.

---

## 2. Backup Architecture

```text
Cron / Scheduled Task (Daily at 02:00 UTC)
         │
         ▼
scripts/backup_postgres.sh (or backup_postgres.py)
         │
         ├── 1. Verify conversx-postgres container health
         ├── 2. Stream pg_dump through gzip compression
         ├── 3. Write to /var/backups/conversx/conversx_backup_YYYYMMDD_HHMMSSZ.sql.gz
         ├── 4. Verify backup size (> 50 bytes) and archive integrity
         └── 5. Prune backups exceeding BACKUP_RETENTION_DAYS (default: 7 days)
```

---

## 3. Backup Configuration & Parameters

| Parameter | Environment Variable | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **Backup Directory** | `BACKUP_DIR` | `/var/backups/conversx` | Local host directory for compressed backup archives. |
| **Retention Window** | `BACKUP_RETENTION_DAYS` | `7` | Days to keep daily backups before automatic deletion. |
| **Database Name** | `POSTGRES_DB` | `conversx` | Target PostgreSQL database name. |
| **Database User** | `POSTGRES_USER` | `conversx` | Application database user with pg_dump privileges. |

---

## 4. Automated Backup Scripts

### Linux / Production VM Script
Location: [`scripts/backup_postgres.sh`](file:///C:/Users/anand/Conversx/scripts/backup_postgres.sh)

```bash
# Run backup manually
bash scripts/backup_postgres.sh

# Cron Configuration (add via `crontab -e` on Oracle VM)
0 2 * * * /opt/conversx/scripts/backup_postgres.sh >> /var/log/conversx_backup.log 2>&1
```

### Cross-Platform Python Utility
Location: [`scripts/backup_postgres.py`](file:///C:/Users/anand/Conversx/scripts/backup_postgres.py)

```bash
# Run backup via python
python scripts/backup_postgres.py backup --dir ./backups --retention-days 7

# Verify archive integrity
python scripts/backup_postgres.py verify-backup ./backups/conversx_backup_20261008_171131Z.sql.gz
```

---

## 5. Restoration Procedure

To restore the database from a backup file:

### Step 1: Place Application in Maintenance Mode
Temporarily stop write traffic to avoid inconsistencies:
```bash
docker compose -f infra/docker-compose.yml stop api worker
```

### Step 2: Execute Restore Script
Location: [`scripts/restore_postgres.sh`](file:///C:/Users/anand/Conversx/scripts/restore_postgres.sh)

```bash
# Verify archive integrity and apply
bash scripts/restore_postgres.sh /var/backups/conversx/conversx_backup_20261008_171131Z.sql.gz
```

Or via Python:
```bash
python scripts/restore_postgres.py restore /var/backups/conversx/conversx_backup_20261008_171131Z.sql.gz
```

### Step 3: Run Alembic Migration Verification
Verify that schema migrations match the current codebase:
```bash
docker compose -f infra/docker-compose.yml run --rm api alembic -c backend/alembic.ini upgrade head
```

### Step 4: Restart Application Services
```bash
docker compose -f infra/docker-compose.yml up -d api worker
```

### Step 5: Verify Application Health
```bash
curl -fsS https://api.conversx.com/health
```

---

## 6. Disaster Recovery Drill (Restore Verification)

To prove backups actually restore without touching the live database:
```bash
python scripts/restore_postgres.py drill /var/backups/conversx/conversx_backup_20261008_171131Z.sql.gz
```

The drill validates:
1. Gzip archive headers and checksums.
2. Complete SQL structure readability.
3. Successful table creation and row insertion into a scratch database (`conversx_drill`).
