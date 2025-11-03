#!/bin/bash
# Skim Bot Startup Script - Ensures IBeam Client Portal API is ready before starting

set -e

echo "=== Skim Bot Startup ==="
echo "Waiting for IBeam Client Portal API to be ready..."

# Configuration
IB_HOST="${IB_HOST:-ibeam}"
IB_PORT="${IB_PORT:-5000}"
MAX_WAIT=600  # 10 minutes max wait (IBeam needs time for 2FA)
WAIT_INTERVAL=10

elapsed=0

# Wait for IBeam Client Portal API to be available and authenticated
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -k -s "https://$IB_HOST:$IB_PORT/v1/api/tickle" | grep -q "authenticated"; then
        echo "IBeam Client Portal API is authenticated and ready at $elapsed seconds"
        echo "IBeam should be ready now!"
        break
    fi

    echo "Waiting for IBeam authentication... ($elapsed/$MAX_WAIT seconds)"
    echo "Note: You may need to approve 2FA on your IBKR Mobile app"
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
done

if [ $elapsed -ge $MAX_WAIT ]; then
    echo "ERROR: IBeam Client Portal API did not become ready within $MAX_WAIT seconds"
    echo "Check IBeam logs: docker-compose logs ibeam"
    echo "You may need to restart IBeam and approve 2FA: docker-compose restart ibeam"
    exit 1
fi

# Start cron and tail logs
echo "Starting cron daemon..."
cron

echo "Tailing logs..."
exec tail -f /var/log/cron.log /app/logs/skim_*.log 2>/dev/null || tail -f /var/log/cron.log
