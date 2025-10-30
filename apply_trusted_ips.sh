#!/bin/bash
# Apply trusted IPs to existing jts.ini
# Run this AFTER IB Gateway has created jts.ini from first login

set -e

echo "=== Applying Trusted IPs to IB Gateway ==="
echo ""

# Check if container is running
if ! docker ps | grep -q ibgateway; then
    echo "ERROR: ibgateway container is not running"
    echo "Start it with: docker-compose up -d ibgateway"
    exit 1
fi

echo "Checking for jts.ini inside ibgateway container..."

# Check if jts.ini exists in container
if ! docker exec ibgateway test -f /home/ibgateway/Jts/jts.ini 2>/dev/null; then
    echo "ERROR: /home/ibgateway/Jts/jts.ini not found inside container"
    echo "IB Gateway needs to complete first login before this script can run"
    echo ""
    echo "Steps:"
    echo "1. Check IB Gateway logs: docker-compose logs ibgateway | tail -50"
    echo "2. Look for successful login message"
    echo "3. Check for 2FA timeout or credential errors"
    echo "4. Once logged in, jts.ini will be created"
    echo "5. Then run this script again"
    exit 1
fi

echo "Found jts.ini in container"
echo ""

# Copy jts.ini from container to local for editing
echo "Copying jts.ini from container..."
docker cp ibgateway:/home/ibgateway/Jts/jts.ini /tmp/jts.ini.temp

# Backup
cp /tmp/jts.ini.temp /tmp/jts.ini.backup.$(date +%Y%m%d_%H%M%S)
echo "Created backup"

# Detect the actual Docker network subnet
DOCKER_SUBNET=$(docker network inspect skim_skim-network -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)

if [ -z "$DOCKER_SUBNET" ]; then
    echo "WARNING: Could not detect docker network subnet, using default 172.18.0.0/16"
    DOCKER_SUBNET="172.18.0.0/16"
else
    echo "Detected Docker network subnet: $DOCKER_SUBNET"
fi

# Check if trustedIPs already exists
if grep -q "trustedIPs=" /tmp/jts.ini.temp; then
    echo "trustedIPs setting found"

    CURRENT_IPS=$(grep "trustedIPs=" /tmp/jts.ini.temp | cut -d'=' -f2)

    if echo "$CURRENT_IPS" | grep -q "$DOCKER_SUBNET"; then
        echo "Docker subnet $DOCKER_SUBNET already configured"
        echo "Current: $CURRENT_IPS"
        echo ""
        echo "No changes needed!"
        rm /tmp/jts.ini.temp
        exit 0
    else
        echo "Adding Docker subnet to existing trustedIPs"
        NEW_IPS="${CURRENT_IPS};${DOCKER_SUBNET}"
        sed -i.bak "s|trustedIPs=.*|trustedIPs=${NEW_IPS}|" /tmp/jts.ini.temp
        echo "Updated trustedIPs: $NEW_IPS"
    fi
else
    echo "No trustedIPs setting found, adding new entry"

    if grep -q "\[IBGateway\]" /tmp/jts.ini.temp; then
        # Add under [IBGateway] section
        sed -i.bak "/\[IBGateway\]/a trustedIPs=${DOCKER_SUBNET}" /tmp/jts.ini.temp
    else
        # Create [IBGateway] section
        echo "" >> /tmp/jts.ini.temp
        echo "[IBGateway]" >> /tmp/jts.ini.temp
        echo "trustedIPs=${DOCKER_SUBNET}" >> /tmp/jts.ini.temp
    fi

    echo "Added trustedIPs: $DOCKER_SUBNET"
fi

echo ""
echo "Copying updated jts.ini back to container..."
docker cp /tmp/jts.ini.temp ibgateway:/home/ibgateway/Jts/jts.ini

echo ""
echo "Configuration updated successfully!"
echo ""
echo "Current trustedIPs in container:"
docker exec ibgateway grep "trustedIPs" /home/ibgateway/Jts/jts.ini
echo ""
echo "Next steps:"
echo "1. Restart IB Gateway: docker-compose restart ibgateway"
echo "2. Wait for IB Gateway to be healthy (~2 minutes)"
echo "3. Check bot logs: docker-compose logs -f bot"
echo "4. Bot should now connect automatically"

# Cleanup
rm /tmp/jts.ini.temp /tmp/jts.ini.temp.bak 2>/dev/null || true
