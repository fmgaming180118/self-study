#!/bin/bash
set -e

# ==============================================================================
# Self Study OS - Zero-Downtime Production Deployment Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "🚀 Starting Production Deployment"
echo "📁 Working Directory: $PROJECT_DIR"
echo "⏰ Time: $(date)"
echo "=================================================="

# Check for production env file
if [ ! -f ".env.production" ]; then
    if [ -f ".env" ]; then
        echo "⚠️  .env.production not found, using .env"
        ENV_FILE=".env"
    else
        echo "❌ ERROR: Neither .env.production nor .env found!"
        echo "   Please create .env.production from .env.production.example"
        exit 1
    fi
else
    ENV_FILE=".env.production"
fi

# Run pre-deployment database backup if database container is running
if docker ps | grep -q "self_study_db_prod"; then
    echo "💾 Creating safety database backup before deployment..."
    chmod +x scripts/backup-db.sh
    ./scripts/backup-db.sh || echo "⚠️ Backup warning, proceeding with deployment..."
fi

echo "🔨 Building production images..."
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml build

echo "🚢 Launching updated containers..."
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml up -d --remove-orphans

echo "⏳ Waiting for services to become healthy..."
MAX_WAIT=90
COUNT=0
HEALTHY=false

while [ $COUNT -lt $MAX_WAIT ]; do
    NGINX_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' self_study_nginx_prod 2>/dev/null || echo '"unknown"')
    BACKEND_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' self_study_backend_prod 2>/dev/null || echo '"unknown"')
    FRONTEND_STATUS=$(docker inspect --format='{{json .State.Health.Status}}' self_study_frontend_prod 2>/dev/null || echo '"unknown"')

    if [ "$NGINX_STATUS" = '"healthy"' ] && [ "$BACKEND_STATUS" = '"healthy"' ] && [ "$FRONTEND_STATUS" = '"healthy"' ]; then
        HEALTHY=true
        break
    fi

    echo "   [$COUNT/$MAX_WAIT s] Waiting... Nginx: $NGINX_STATUS | Backend: $BACKEND_STATUS | Frontend: $FRONTEND_STATUS"
    sleep 5
    COUNT=$((COUNT + 5))
done

if [ "$HEALTHY" = true ]; then
    echo "=================================================="
    echo "✅ Production Deployment Successful!"
    echo "=================================================="
    chmod +x scripts/smoke-test.sh
    ./scripts/smoke-test.sh
else
    echo "=================================================="
    echo "❌ Deployment Warning: Some services did not reach healthy state in time."
    echo "   Check logs using: docker compose -f docker-compose.prod.yml logs --tail 50"
    echo "=================================================="
    exit 1
fi
