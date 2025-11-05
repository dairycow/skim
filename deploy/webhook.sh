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

# OAuth connects directly to IBKR - no Gateway health check needed
echo "OAuth authentication - connecting directly to IBKR Client Portal API"

# Show status
echo
echo "Deployment complete!"
echo
echo "Container status:"
docker-compose ps

echo
echo "View logs with:"
echo "  docker-compose logs -f bot"
echo
echo "Check bot status:"
echo "  docker-compose exec bot python /app/bot.py status"
