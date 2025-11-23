#!/bin/bash
# GitOps deployment for Skim Trading Bot - deploys main branch only

set -e

cd /opt/skim

echo "Deploying main branch..."
git fetch origin main
git reset --hard origin/main

echo "Updating dependencies..."
/home/skim/.local/bin/uv sync --frozen

echo "Installing crontab..."
sudo cp crontab /etc/cron.d/skim-trading-bot
sudo chmod 644 /etc/cron.d/skim-trading-bot
sudo chown root:root /etc/cron.d/skim-trading-bot

echo "Reloading cron daemon..."
sudo systemctl reload cron

echo "Deployment complete! Running health check..."
if /opt/skim/.venv/bin/python -m skim.core.bot status > /dev/null 2>&1; then
    echo "Bot is healthy and running"
else
    echo "Bot health check failed - check logs: tail -f /opt/skim/logs/*.log"
    exit 1
fi

echo "Deployment completed successfully at $(date)"
