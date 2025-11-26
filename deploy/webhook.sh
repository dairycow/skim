#!/bin/bash
# GitOps deployment for Skim Trading Bot - deploys main branch only

set -e

cd /opt/skim

echo "Deploying main branch..."
git fetch origin main
git reset --hard origin/main

echo "Updating dependencies..."
/opt/skim/.local/bin/uv sync --frozen

echo "Installing sudoers configuration..."
sudo cp deploy/sudoers-skim /etc/sudoers.d/skim-deploy
sudo chmod 440 /etc/sudoers.d/skim-deploy

echo "Installing crontab..."
sudo cp crontab /etc/cron.d/skim-trading-bot
sudo chmod 644 /etc/cron.d/skim-trading-bot
sudo chown root:root /etc/cron.d/skim-trading-bot

echo "Restarting cron daemon..."
sudo systemctl restart cron

echo "Deployment complete! Running health check..."
if /opt/skim/.venv/bin/python -m skim.core.bot status > /dev/null 2>&1; then
    echo "Bot is healthy and running"
    STATUS="success"
else
    echo "Bot health check failed - check logs: tail -f /opt/skim/logs/*.log"
    STATUS="failed"
fi

echo "Deployment completed at $(date)"

# Send Discord notification
if [ -f .env ]; then
    source .env
    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        COMMIT=$(git log -1 --pretty=format:%h)
        curl -X POST "$DISCORD_WEBHOOK_URL" -H "Content-Type: application/json" -d "{\"content\":\"Deploy $STATUS: $COMMIT\"}"
    else
        echo "DISCORD_WEBHOOK_URL not set"
    fi
else
    echo ".env file not found"
fi

[ "$STATUS" = "failed" ] && exit 1
exit 0
