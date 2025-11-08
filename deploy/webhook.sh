#!/bin/bash
# GitOps deployment for Skim Trading Bot - deploys main branch only

set -e

cd /opt/skim

echo "Deploying main branch..."
git fetch origin && git reset --hard origin/main
docker-compose down
docker-compose up -d --build

echo "Deployment complete! Status:"
docker-compose ps
echo "Logs: docker-compose logs -f bot"
echo "Status: docker-compose exec bot python /app/bot.py status"
