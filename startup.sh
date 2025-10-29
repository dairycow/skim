#!/bin/bash
# Skim Bot Startup Script - Ensures IB Gateway is ready before starting

set -e

echo "=== Skim Bot Startup ==="
echo "Waiting for IB Gateway to be ready..."

# Configuration
IB_HOST="${IB_HOST:-ibgateway}"
IB_PORT="${IB_PORT:-4002}"
MAX_WAIT=180  # 3 minutes max wait
WAIT_INTERVAL=5

elapsed=0

# Wait for IB Gateway TCP port to be available
while [ $elapsed -lt $MAX_WAIT ]; do
    if timeout 2 bash -c "echo > /dev/tcp/$IB_HOST/$IB_PORT" 2>/dev/null; then
        echo "IB Gateway TCP port is available"

        # Additional delay to ensure API is fully initialized
        echo "Waiting additional 10 seconds for IB Gateway API initialization..."
        sleep 10

        echo "IB Gateway is ready!"
        break
    fi

    echo "Waiting for IB Gateway... ($elapsed/$MAX_WAIT seconds)"
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
