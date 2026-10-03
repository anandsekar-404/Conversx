#!/usr/bin/env bash
# =============================================================================
# infra/scripts/deploy.sh
# Pull-based deploy script — run by a systemd timer every 2 minutes on the VM.
# UNTESTED — has not run on a real server. Test at Gate B. (§18.4)
# =============================================================================
set -euo pipefail

cd /opt/conversx
source .env.deploy   # sets GHCR_IMAGE; this file is NOT in git

IMAGE="$GHCR_IMAGE:stable"

# Check if a new image is available
RUNNING=$(docker inspect --format '{{.Image}}' conversx-api 2>/dev/null || true)
docker pull "$IMAGE" > /dev/null
LATEST=$(docker image inspect --format '{{.Id}}' "$IMAGE")

# Nothing changed — exit quietly
[ "$RUNNING" = "$LATEST" ] && exit 0

echo "[deploy] New image detected: $LATEST"

# Tag the running image for rollback
[ -n "$RUNNING" ] && docker tag "$RUNNING" "$GHCR_IMAGE:rollback"

# Run migrations before swapping (must be backward-compatible: expand/contract)
docker compose -f /opt/conversx/infra/docker-compose.yml \
  run --rm api alembic -c alembic.ini upgrade head

# Bring up new containers
docker compose -f /opt/conversx/infra/docker-compose.yml \
  up -d --remove-orphans

# Health check loop — wait up to 60 s
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz > /dev/null; then
    echo "[deploy] OK — new image live"
    exit 0
  fi
  sleep 2
done

# Health check failed — roll back
echo "[deploy] Health check failed — rolling back" >&2
if [ -n "$RUNNING" ]; then
  IMAGE_TAG=rollback \
    docker compose -f /opt/conversx/infra/docker-compose.yml up -d
fi
exit 1
