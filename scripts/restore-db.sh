#!/bin/bash
set -e

# ==============================================================================
# PostgreSQL Database Restore Script
# ==============================================================================

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-backup-file.sql.gz>"
    echo "Example: $0 backups/self_study_db_20260905_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

if docker ps | grep -q "self_study_db_prod"; then
    CONTAINER="self_study_db_prod"
elif docker ps | grep -q "self_study_db"; then
    CONTAINER="self_study_db"
else
    echo "❌ ERROR: No PostgreSQL container running."
    exit 1
fi

DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-self_study_os}

echo "⚠️  WARNING: Restoring will overwrite existing database '$DB_NAME' in '$CONTAINER'!"
read -p "Are you sure you want to proceed? (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "🔄 Restoring database from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

echo "✅ Database restore completed successfully!"
