#!/bin/bash
# Diagnostic script to troubleshoot IBeam Client Portal connection issues

echo "=== IBeam Client Portal Connection Diagnostics ==="
echo ""

echo "1. Container Status:"
docker-compose ps
echo ""

echo "2. IBeam Logs (last 30 lines):"
docker-compose logs --tail=30 ibeam
echo ""

echo "3. IBeam Authentication Status:"
curl -k -s https://ibeam:5000/v1/api/tickle 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Cannot connect to IBeam API"
echo ""

echo "4. IBeam Account Information:"
curl -k -s https://ibeam:5000/v1/api/portfolio/accounts 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Cannot retrieve account info"
echo ""

echo "5. Client Portal API connectivity test from bot:"
docker exec skim-bot curl -k -s https://ibeam:5000/v1/api/tickle | head -5 2>/dev/null || echo "Bot cannot connect to IBeam API"
echo ""

echo "6. Bot container logs (last 20 lines):"
docker-compose logs --tail=20 bot
echo ""

echo "=== Diagnostic Complete ==="
echo ""
echo "Common issues:"
echo "- If tickle returns 'not authenticated': Approve 2FA on IBKR Mobile app"
echo "- If accounts API fails: IBeam authentication expired, restart container"
echo "- If bot cannot connect: Check network connectivity between containers"
echo "- If Client Portal API is down: Restart IBeam: docker-compose restart ibeam"
