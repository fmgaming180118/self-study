#!/bin/bash
set -e

# ==============================================================================
# Let's Encrypt SSL Bootstrap Script for Self Study OS
# ==============================================================================

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <your-domain.com> <your-email@example.com>"
    echo "Example: $0 learn.selfstudy.dev admin@selfstudy.dev"
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"

echo "=================================================="
echo "🔐 Setting up SSL for $DOMAIN via Let's Encrypt"
echo "=================================================="

# Ensure Nginx is running to respond to ACME challenge
if ! docker ps | grep -q "self_study_nginx_prod"; then
    echo "Starting production containers first..."
    docker compose -f docker-compose.prod.yml up -d nginx
fi

echo "Requesting Let's Encrypt certificate..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL \
    -d $DOMAIN \
    --agree-tos \
    --no-eff-email \
    --force-renewal" certbot

echo "Configuring Nginx with SSL certificates..."
# Generate active SSL configuration from template
sed "s/YOUR_DOMAIN/$DOMAIN/g" nginx/conf.d/ssl.conf.template > nginx/conf.d/default.conf

echo "Reloading Nginx configuration..."
docker exec self_study_nginx_prod nginx -s reload

echo "=================================================="
echo "🎉 SSL Setup Completed! Access https://$DOMAIN"
echo "=================================================="
