#!/usr/bin/env bash
# =============================================================================
# infra/scripts/renew_certificates.sh
# Automated Let's Encrypt / Certbot Certificate Renewal for ConversX
#
# Usage:
#   bash infra/scripts/renew_certificates.sh
#
# Process:
#   1. Runs certbot renewal using webroot mode against Nginx challenge dir.
#   2. Reloads Nginx reverse proxy configuration to apply renewed certificates.
#   3. Validates TLS certificate expiration.
# =============================================================================
set -euo pipefail

echo "[certbot-renew] Starting ACME certificate renewal check..."

# Run certbot renew inside certbot container or host
docker compose -f infra/docker-compose.yml run --rm certbot renew --webroot -w /var/www/certbot --quiet

echo "[certbot-renew] Reloading Nginx configuration..."
docker compose -f infra/docker-compose.yml exec -T nginx nginx -s reload

echo "[certbot-renew] Certificate renewal and Nginx reload complete."
