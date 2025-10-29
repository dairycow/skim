#!/bin/bash
#
# Skim Trading Bot - GitOps Deployment Script
# Run this on your DigitalOcean droplet to deploy/update the bot
#

set -e  # Exit on error

echo "=== Skim Trading Bot - Deployment ==="
echo "Timestamp: $(date)"
echo

# Navigate to deployment directory
cd /opt/skim

# Pull latest changes from git
echo "Pulling latest changes from git..."
git fetch origin
git reset --hard origin/claude/asx-trading-bot-setup-011CUaapBZE3mo2kEGwriSKK

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down || true

# Build and start containers
echo "Building and starting containers..."
docker-compose up -d --build

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
