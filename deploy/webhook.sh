#!/bin/bash
#
# Skim Trading Bot - GitOps Deployment Script
# Run this on your DigitalOcean droplet to deploy/update the bot
#
# Usage:
#   ./deploy/webhook.sh                    # Deploy from main branch
#   DEPLOY_BRANCH=develop ./deploy/webhook.sh  # Deploy from specific branch
#

set -e  # Exit on error

echo "=== Skim Trading Bot - Deployment ==="
echo "Timestamp: $(date)"
echo

# Navigate to deployment directory
cd /opt/skim

# Pull latest changes from git
echo "Pulling latest changes from git..."
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
echo "Deploying branch: $DEPLOY_BRANCH"
git fetch origin
git reset --hard origin/$DEPLOY_BRANCH

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down || true

# Build and start containers
echo "Building and starting containers..."
docker-compose up -d --build

# Wait for IBeam to be healthy
echo "Waiting for IBeam to be healthy..."
timeout=300
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps ibeam | grep -q "healthy"; then
        echo "IBeam is healthy"
        break
    fi
    echo "Waiting for IBeam... ($elapsed/$timeout seconds)"
    sleep 10
    elapsed=$((elapsed + 10))
done

if [ $elapsed -ge $timeout ]; then
    echo "ERROR: IBeam did not become healthy within $timeout seconds"
    exit 1
fi

# Note: Trusted IPs configuration not needed with IBind + IBeam setup
echo "IBind handles authentication directly through Client Portal API"

# Show status
echo
echo "Deployment complete!"
echo
echo "Container status:"
docker-compose ps

echo
echo "View logs with:"
echo "  docker-compose logs -f bot"
echo "  docker-compose logs -f ibgateway"
echo
echo "Check bot status:"
echo "  docker-compose exec bot python /app/bot.py status"
