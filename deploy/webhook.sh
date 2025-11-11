#!/bin/bash
# GitOps deployment for Skim Trading Bot - deploys main branch only

set -e

cd /opt/skim

echo "Deploying main branch..."
git fetch origin && git reset --hard origin/main
docker-compose down
docker-compose build --no-cache bot
docker-compose up -d

echo "Deployment complete! Running status check..."
docker-compose ps

# Clean up old Docker resources (images older than 24 hours)
echo "Cleaning up old Docker resources..."
docker image prune -f --filter "until=24h"

# Wait for container to be ready, then check bot status
sleep 10
if docker-compose exec bot /app/.venv/bin/python -m skim.core.bot status > /dev/null 2>&1; then
    echo "Bot started successfully"
else
    echo "Bot failed to start - check logs: docker-compose logs bot"
fi
