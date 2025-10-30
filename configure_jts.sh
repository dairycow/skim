#!/bin/bash
# Configure IB Gateway jts.ini to trust Docker network IPs

set -e

JTS_INI_PATH="${JTS_INI_PATH:-/root/Jts/jts.ini}"
# Detect actual Docker network subnet or use default
if [ -z "$DOCKER_SUBNET" ]; then
    DOCKER_SUBNET=$(docker network inspect skim_skim-network -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "172.18.0.0/16")
fi

echo "Using Docker subnet: $DOCKER_SUBNET"

echo "=== Configuring IB Gateway Trusted IPs ==="

# Wait for jts.ini to be created by IB Gateway
MAX_WAIT=180
WAIT_INTERVAL=5
elapsed=0

while [ ! -f "$JTS_INI_PATH" ] && [ $elapsed -lt $MAX_WAIT ]; do
    echo "Waiting for $JTS_INI_PATH to be created... ($elapsed/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    elapsed=$((elapsed + WAIT_INTERVAL))
done

if [ ! -f "$JTS_INI_PATH" ]; then
    echo "WARNING: $JTS_INI_PATH not found after $MAX_WAIT seconds"
    echo "IB Gateway may need to initialize first. This is normal on first run."
    exit 0
fi

echo "Found $JTS_INI_PATH"

# Backup original file
cp "$JTS_INI_PATH" "${JTS_INI_PATH}.bak"

# Check if trustedIPs already exists
if grep -q "trustedIPs=" "$JTS_INI_PATH"; then
    echo "trustedIPs setting found, updating..."

    # Extract current trusted IPs
    CURRENT_IPS=$(grep "trustedIPs=" "$JTS_INI_PATH" | cut -d'=' -f2)

    # Check if Docker subnet is already included
    if echo "$CURRENT_IPS" | grep -q "$DOCKER_SUBNET"; then
        echo "Docker subnet $DOCKER_SUBNET already in trustedIPs"
    else
        echo "Adding Docker subnet to existing trustedIPs"
        # Append Docker subnet to existing IPs
        NEW_IPS="${CURRENT_IPS};${DOCKER_SUBNET}"
        sed -i "s|trustedIPs=.*|trustedIPs=${NEW_IPS}|" "$JTS_INI_PATH"
        echo "Updated trustedIPs: $NEW_IPS"
    fi
else
    echo "No trustedIPs setting found, adding new entry..."

    # Check if [IBGateway] section exists
    if grep -q "\[IBGateway\]" "$JTS_INI_PATH"; then
        # Add trustedIPs under [IBGateway] section
        sed -i "/\[IBGateway\]/a trustedIPs=${DOCKER_SUBNET}" "$JTS_INI_PATH"
    else
        # Create [IBGateway] section with trustedIPs
        echo "" >> "$JTS_INI_PATH"
        echo "[IBGateway]" >> "$JTS_INI_PATH"
        echo "trustedIPs=${DOCKER_SUBNET}" >> "$JTS_INI_PATH"
    fi

    echo "Added trustedIPs: $DOCKER_SUBNET"
fi

echo "Configuration complete!"
echo "Backup saved to: ${JTS_INI_PATH}.bak"

# Display relevant config
echo ""
echo "Current IB Gateway trusted IPs configuration:"
grep -A 5 "\[IBGateway\]" "$JTS_INI_PATH" || echo "No [IBGateway] section found"
