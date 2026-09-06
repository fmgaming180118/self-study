#!/bin/bash
set -e

# ==============================================================================
# PostgreSQL Automated Backup Script with Retention
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/self_study_db_$TIMESTAMP.sql.gz"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "💾 Initiating database backup..."

# Detect container name (production or dev)
if docker ps | grep -q "self_study_db_prod"; then
    CONTAINER="self_study_db_prod"
elif docker ps | grep -q "self_study_db"; then
    CONTAINER="self_study_db"
else
    echo "❌ ERROR: No PostgreSQL container running (checked self_study_db_prod and self_study_db)."
    exit 1
fi

DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-self_study_os}

docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ Backup successfully created: $BACKUP_FILE ($FILE_SIZE)"

# Clean up old backups older than retention days
echo "🧹 Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "self_study_db_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -exec rm -f {} \;

echo "✨ Backup job completed."
