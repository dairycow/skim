#!/bin/bash
# Diagnostic script to troubleshoot IB Gateway connection issues

echo "=== IB Gateway Connection Diagnostics ==="
echo ""

echo "1. Container Status:"
docker-compose ps
echo ""

echo "2. IB Gateway Logs (last 30 lines):"
docker-compose logs --tail=30 ibgateway
echo ""

echo "3. Checking jts.ini file:"
docker exec ibgateway cat /home/ibgateway/Jts/jts.ini 2>/dev/null || echo "ERROR: Cannot read jts.ini"
echo ""

echo "4. Checking for trusted IPs:"
docker exec ibgateway grep -i "trustedIPs" /home/ibgateway/Jts/jts.ini 2>/dev/null || echo "No trustedIPs found"
echo ""

echo "5. Network connectivity test from bot to IB Gateway:"
docker exec skim-bot bash -c "timeout 2 bash -c 'echo > /dev/tcp/ibgateway/4004' && echo 'TCP connection successful' || echo 'TCP connection failed'"
echo ""

echo "6. Bot container logs (last 20 lines):"
docker-compose logs --tail=20 bot
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "Common issues:"
echo "- If jts.ini doesn't exist: IB Gateway hasn't fully initialized yet"
echo "- If trustedIPs is missing: apply_trusted_ips.sh didn't run or failed"
echo "- If IB Gateway logs show 'rejected': IP not in trusted list"
echo "- If TimeoutError persists: IB Gateway may need restart or credentials issue"
