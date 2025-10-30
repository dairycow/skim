#!/bin/bash
# Skim Bot Startup Script - Ensures IB Gateway is ready before starting

set -e

echo "=== Skim Bot Startup ==="
echo "Waiting for IB Gateway to be ready..."

# Configuration
IB_HOST="${IB_HOST:-ibgateway}"
IB_PORT="${IB_PORT:-4002}"
MAX_WAIT=300  # 5 minutes max wait
WAIT_INTERVAL=5

elapsed=0

# Wait for IB Gateway TCP port to be available
while [ $elapsed -lt $MAX_WAIT ]; do
    if timeout 2 bash -c "echo > /dev/tcp/$IB_HOST/$IB_PORT" 2>/dev/null; then
        echo "IB Gateway TCP port is available at $elapsed seconds"

        # Additional delay to ensure API is fully initialized
        # IB Gateway can take 30-60 seconds after TCP port opens to be API-ready
        echo "Waiting additional 60 seconds for IB Gateway API initialization..."
        sleep 60

        echo "IB Gateway should be ready now!"
        break
    fi

    echo "Waiting for IB Gateway TCP port... ($elapsed/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
done

if [ $elapsed -ge $MAX_WAIT ]; then
    echo "ERROR: IB Gateway did not become ready within $MAX_WAIT seconds"
    exit 1
fi

# Start cron and tail logs
echo "Starting cron daemon..."
cron

echo "Tailing logs..."
exec tail -f /var/log/cron.log /app/logs/skim_*.log 2>/dev/null || tail -f /var/log/cron.log
