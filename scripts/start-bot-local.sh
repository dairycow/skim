#!/bin/bash
# Local development script for Skim Trading Bot

set -e

# Check if Docker daemon is already running
if docker info > /dev/null 2>&1; then
    echo "Docker daemon is already running!"
else
    echo "Docker daemon not running, starting Docker Desktop..."
    open /Applications/Docker.app
    
    # Wait for Docker Desktop to be ready
    echo "Waiting for Docker daemon to be ready..."
    until docker info > /dev/null 2>&1; do
        echo "Docker not ready yet, waiting..."
        sleep 2
    done
    echo "Docker daemon is ready!"
fi

echo "Building and starting bot locally..."
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
