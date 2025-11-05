#!/bin/bash
# Skim Bot Startup Script

set -e

echo "=== Skim Bot Startup ==="

# Check if using OAuth - if so, no Gateway needed!
if [ -n "${OAUTH_CONSUMER_KEY}" ]; then
    echo "Using OAuth 1.0a authentication"
    echo "OAuth connects directly to IBKR API - no Gateway needed!"
    echo "Starting bot immediately..."
else
    echo "Using session-based authentication - waiting for IBeam Gateway..."

    # Configuration
    IB_HOST="${IB_HOST:-ibeam}"
    IB_PORT="${IB_PORT:-5000}"
    MAX_WAIT=600  # 10 minutes max wait
    WAIT_INTERVAL=10
    elapsed=0

    # Wait for IBeam Client Portal API to be available and authenticated
    while [ $elapsed -lt $MAX_WAIT ]; do
        if curl -k -s "https://$IB_HOST:$IB_PORT/v1/api/tickle" | grep -q "authenticated"; then
            echo "IBeam Client Portal API is authenticated and ready"
            break
        fi

        echo "Waiting for IBeam authentication... ($elapsed/$MAX_WAIT seconds)"
        echo "Note: You may need to approve 2FA on your IBKR Mobile app"
        sleep $WAIT_INTERVAL
        elapsed=$((elapsed + WAIT_INTERVAL))
    done

    if [ $elapsed -ge $MAX_WAIT ]; then
        echo "ERROR: Gateway did not become ready within $MAX_WAIT seconds"
        echo "Check IBeam logs: docker-compose logs ibeam"
        exit 1
    fi
fi

# Start cron and tail logs
echo "Starting cron daemon..."
cron

echo "Tailing logs..."
exec tail -f /var/log/cron.log /app/logs/skim_*.log 2>/dev/null || tail -f /var/log/cron.log
