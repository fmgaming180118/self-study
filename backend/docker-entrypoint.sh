#!/bin/sh
set -e

# If running auxiliary commands like pytest, python, bash, or sh, bypass wait-for-db
case "$1" in
    pytest|python|python3|bash|sh)
        exec "$@"
        ;;
esac

echo "==> Self Study OS - Production Entrypoint <=="

# Wait for PostgreSQL to become ready
echo "==> Waiting for database to be ready..."
python - <<'EOF'
import os
import sys
import time
from urllib.parse import urlparse
import socket

db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/self_study_os")
clean_url = db_url.replace("postgresql+asyncpg://", "http://").replace("postgresql://", "http://")
parsed = urlparse(clean_url)
host = parsed.hostname or "db"
port = parsed.port or 5432

retries = 30
while retries > 0:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host, port))
        sock.close()
        print(f"Database reachable at {host}:{port}")
        sys.exit(0)
    except Exception as e:
        print(f"Waiting for database at {host}:{port}... ({retries} retries left)")
        time.sleep(2)
        retries -= 1

print("ERROR: Database connection timed out.")
sys.exit(1)
EOF

echo "==> Database is available. Running migrations & initialization..."

# Run Alembic migrations if alembic versions exist
if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions/*.py 2>/dev/null)" ]; then
    echo "==> Running Alembic migrations..."
    alembic upgrade head || {
        echo "Alembic migration warning, continuing..."
    }
fi

# Seed initial MVP skills if database is empty
python init_db.py

echo "==> Application ready to start."

# Execute CMD passed to container
exec "$@"
