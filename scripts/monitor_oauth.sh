#!/bin/bash
# Monitor OAuth connection health by running periodic tests
#
# Usage:
#   From host: ./scripts/monitor_oauth.sh [interval_seconds]
#   Default interval: 300 seconds (5 minutes)
#
# Example:
#   ./scripts/monitor_oauth.sh 60  # Test every 60 seconds

INTERVAL=${1:-300}  # Default 5 minutes
LOG_FILE="/app/logs/oauth_monitor.log"

echo "Starting OAuth connection monitor (testing every ${INTERVAL} seconds)"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    echo "----------------------------------------"
    date
    echo "----------------------------------------"

    # Run the OAuth connection test
    python /app/scripts/test_oauth_connection.py

    TEST_RESULT=$?

    if [ $TEST_RESULT -eq 0 ]; then
        echo "✓ Test passed - OAuth connection healthy" | tee -a "$LOG_FILE"
    else
        echo "✗ Test failed - OAuth connection issue detected" | tee -a "$LOG_FILE"
    fi

    echo ""
    echo "Next test in ${INTERVAL} seconds..."
    echo ""

    sleep "$INTERVAL"
done
