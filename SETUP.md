# Skim Bot - Initial Setup Guide

## First Time Setup

IB Gateway requires initial manual configuration before the bot can connect automatically.

### Step 1: Start IB Gateway

```bash
docker-compose up -d ibgateway
```

Wait for IB Gateway to fully initialize (check logs):
```bash
docker-compose logs -f ibgateway
```

### Step 2: Access IB Gateway VNC (if needed)

If you need to interact with IB Gateway GUI:
```bash
# Check if VNC is exposed (typically port 5900)
docker-compose logs ibgateway | grep VNC
```

### Step 3: Make First Connection from Bot

The first connection from the bot will prompt IB Gateway to create config files:

```bash
# Start the bot
docker-compose up -d bot

# Watch bot logs
docker-compose logs -f bot
```

You'll see connection attempts. IB Gateway should prompt to accept/reject the connection.

### Step 4: Check if jts.ini Exists in Container

```bash
# Check if jts.ini exists inside the ibgateway container
docker exec ibgateway test -f /root/Jts/jts.ini && echo "jts.ini exists" || echo "jts.ini not found"

# If it exists, view it
docker exec ibgateway cat /root/Jts/jts.ini
```

If jts.ini doesn't exist yet, IB Gateway hasn't completed first login. Check logs:
```bash
docker-compose logs ibgateway | grep -i "login\|error\|2fa"
```

### Step 5: Configure Trusted IPs

#### Option A: Automated Configuration (Recommended)

Once jts.ini exists in the container, run:
```bash
./apply_trusted_ips.sh
```

This script will:
- Check if jts.ini exists in the container
- Auto-detect your Docker network subnet (e.g., 172.18.0.0/16)
- Copy jts.ini out, modify it, and copy it back
- Add Docker subnet to trustedIPs

#### Option B: Manual Configuration

```bash
# Copy jts.ini from container
docker cp ibgateway:/root/Jts/jts.ini ./jts.ini.temp

# Edit it - add under [IBGateway] section:
# trustedIPs=172.18.0.0/16
# (Use your actual Docker network subnet - check with: docker network inspect skim_skim-network)

# Copy it back
docker cp ./jts.ini.temp ibgateway:/root/Jts/jts.ini

# Restart IB Gateway
docker-compose restart ibgateway
```

### Step 6: Verify Connection

```bash
# Check bot logs for successful connection
docker-compose logs bot | grep "Connected to account"

# You should see:
# "PAPER TRADING MODE - Account: DU..."
# "IB connection established successfully"
```

### Step 7: Run Diagnostic

```bash
chmod +x diagnose.sh
./diagnose.sh
```

## Troubleshooting

### Connection Timeout
- IB Gateway may not be fully started
- Check: `docker-compose logs ibgateway`
- Wait 2-3 minutes after "healthy" status

### "Not Connected" Error
- Trusted IPs not configured in container
- Check: `docker exec ibgateway cat /root/Jts/jts.ini | grep trustedIPs`
- Should show: `trustedIPs=172.18.0.0/16` (or your Docker network subnet)
- If missing, run: `./apply_trusted_ips.sh`

### Client ID Already in Use
- Change in `.env`:
  ```
  IB_CLIENT_ID=2
  ```
- Restart: `docker-compose restart bot`

### jts.ini Doesn't Exist
- IB Gateway hasn't completed first login
- Check credentials in `.env`
- Check 2FA isn't timing out

## Normal Operation

After initial setup, the bot will:
1. Wait for IB Gateway to be healthy
2. Connect automatically using lazy initialization
3. Run scheduled tasks via cron
4. Reconnect automatically if connection drops

## Maintenance

### View Logs
```bash
docker-compose logs -f bot
docker-compose logs -f ibgateway
```

### Restart Services
```bash
docker-compose restart bot
docker-compose restart ibgateway
```

### Clean Restart
```bash
docker-compose down
docker-compose up -d
```
