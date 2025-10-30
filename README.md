# Skim - ASX Pivot Trading Bot

Production-ready ASX pivot trading bot for paper trading on Interactive Brokers. Optimized for iPhone deployment via Termius + DigitalOcean.

## Strategy Overview

1. Scan ASX market using TradingView scanner API for momentum stocks
2. Monitor for gaps >3% at market open
3. Enter on breakout above opening range high
4. Stop loss at low of day
5. Sell half position on day 3
6. Trail remaining with 10-day SMA

## Quick Start (iPhone Deployment)

### Prerequisites

- DigitalOcean Ubuntu 24.04 droplet
- Docker & Docker Compose installed on droplet
- Interactive Brokers paper trading account
- Termius app on iPhone
- Git configured

### Step 1: Initial Setup on Droplet

SSH into your droplet via Termius:

```bash
# Create deployment directory
sudo mkdir -p /opt/skim
sudo chown $USER:$USER /opt/skim
cd /opt/skim

# Clone repository
git clone https://github.com/dairycow/skim.git .

# Create .env file from template
cp .env.example .env
nano .env  # Edit with your IB credentials
```

### Step 2: Configure Environment Variables

Edit `.env` with your Interactive Brokers credentials:

```bash
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password
TRADING_MODE=paper
PAPER_TRADING=true
```

CRITICAL: Ensure `TRADING_MODE=paper` and `PAPER_TRADING=true` for safety.

### Step 2.5: Authentication Setup

This bot uses IBKR Mobile push notifications for 2FA authentication in headless mode.

Ensure you have:
1. IBKR Mobile app installed on your phone
2. Mobile authentication enabled in IB Account Management
3. Your phone ready to approve login requests

When IB Gateway starts, you'll receive a push notification on your phone to approve the login.

### Step 3: Deploy

```bash
# Start the services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f bot
```

### Step 4: Verify Paper Trading

```bash
# Check bot status
docker-compose exec bot python /app/bot.py status

# Verify paper account (should see DU prefix)
docker-compose logs bot | grep "Connected to account"
```

## Detailed Setup

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
docker exec ibgateway test -f /home/ibgateway/Jts/jts.ini && echo "jts.ini exists" || echo "jts.ini not found"

# If it exists, view it
docker exec ibgateway cat /home/ibgateway/Jts/jts.ini
```

If jts.ini doesn't exist yet, IB Gateway hasn't completed first login. Check logs:
```bash
docker-compose logs ibgateway | grep -i "login\|error\|2fa"
```

### Step 5: Configure Trusted IPs

#### Option A: Automated Configuration (Recommended)

Once jts.ini exists in the container, run:
```bash
./scripts/apply_trusted_ips.sh
```

This script will:
- Check if jts.ini exists in the container
- Auto-detect your Docker network subnet (e.g., 172.18.0.0/16)
- Copy jts.ini out, modify it, and copy it back
- Add Docker subnet to trustedIPs

#### Option B: Manual Configuration

```bash
# Copy jts.ini from container
docker cp ibgateway:/home/ibgateway/Jts/jts.ini ./jts.ini.temp

# Edit it - add under [IBGateway] section:
# trustedIPs=172.18.0.0/16
# (Use your actual Docker network subnet - check with: docker network inspect skim_skim-network)

# Copy it back
docker cp ./jts.ini.temp ibgateway:/home/ibgateway/Jts/jts.ini

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
chmod +x scripts/diagnose.sh
./scripts/diagnose.sh
```

## Troubleshooting

### Connection Timeout
- IB Gateway may not be fully started
- Check: `docker-compose logs ibgateway`
- Wait 2-3 minutes after "healthy" status

### "Not Connected" Error
- Trusted IPs not configured in container
- Check: `docker exec ibgateway cat /home/ibgateway/Jts/jts.ini | grep trustedIPs`
- Should show: `trustedIPs=172.18.0.0/16` (or your Docker network subnet)
- If missing, run: `./scripts/apply_trusted_ips.sh`

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

## Daily Operations (via Termius)

### Check Bot Status

```bash
cd /opt/skim
docker-compose exec bot python /app/bot.py status
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f bot

# Last 100 lines
docker-compose logs --tail=100 bot

# View log files
tail -f logs/skim_*.log
```

### Manual Operations

```bash
# Run scan manually
docker-compose exec bot python /app/bot.py scan

# Monitor for gaps
docker-compose exec bot python /app/bot.py monitor

# Execute orders
docker-compose exec bot python /app/bot.py execute

# Manage positions
docker-compose exec bot python /app/bot.py manage_positions
```

### Check Database

```bash
# View candidates
docker-compose exec bot sqlite3 /app/data/skim.db "SELECT * FROM candidates;"

# View open positions
docker-compose exec bot sqlite3 /app/data/skim.db "SELECT * FROM positions WHERE status IN ('open', 'half_exited');"

# View recent trades
docker-compose exec bot sqlite3 /app/data/skim.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

## Cron Schedule

The bot runs automatically on this schedule (UTC times):

- **10:30 UTC** (9:30 PM AEDT): Pre-market scan
- **23:00 UTC** (10:00 AM AEDT): Market open monitoring
- **23:15 UTC** (10:15 AM AEDT): Execute triggered orders
- **Every 5 min during market hours**: Position management
- **05:30 UTC** (4:30 PM AEDT): EOD status report

## Maintenance

### Update Bot Code

```bash
cd /opt/skim
git pull
docker-compose up -d --build
```

Or use the deployment script:

```bash
cd /opt/skim
./deploy/webhook.sh
```

### Restart Services

```bash
docker-compose restart bot
docker-compose restart ibgateway
```

### Stop Trading

```bash
docker-compose stop bot
```

### Backup Database

```bash
cp data/skim.db data/skim_backup_$(date +%Y%m%d).db
```

## Troubleshooting

### Bot Not Connecting to IB Gateway

```bash
# Check IB Gateway status
docker-compose logs ibgateway

# Restart IB Gateway
docker-compose restart ibgateway

# Wait 30 seconds, then restart bot
docker-compose restart bot
```

### Authentication Issues

If IB Gateway fails to authenticate:

```bash
# Check authentication logs
docker-compose logs ibgateway | grep -i "auth\|login"

# Common issues:
# - Push notification not approved on phone
# - IBKR Mobile app not installed or not logged in
# - Mobile authentication not enabled in IB portal
```

To fix authentication:
1. Ensure IBKR Mobile app is installed and logged in
2. Check IB Account Management > Security > Secure Login System
3. Enable "IBKR Mobile Authentication" if not already enabled
4. Restart IB Gateway: `docker-compose restart ibgateway`
5. Approve the push notification on your phone when prompted

### Database Locked

```bash
# Stop bot, backup database, restart
docker-compose stop bot
cp data/skim.db data/skim_backup.db
docker-compose start bot
```

### Check Cron Jobs

```bash
# Enter container
docker-compose exec bot bash

# View crontab
crontab -l

# Check cron logs
tail -f /var/log/cron.log
```

## Safety Features

1. **Paper Trading Checks**
   - Verifies IB account has 'DU' prefix (paper account)
   - Environment variable `PAPER_TRADING=true` required
   - Logs warnings if connecting to unexpected account

2. **Error Handling**
   - All IB API calls wrapped in try/except
   - Automatic reconnection logic
   - Never crashes - logs errors and continues

3. **Position Limits**
   - Max 5 concurrent positions (configurable)
   - Max 1000 shares per position (configurable)
   - $5000 max per position

## Architecture

```
skim/
├── bot.py                  # Main trading bot (single file)
├── docker-compose.yml      # Service orchestration
├── Dockerfile              # Bot container definition
├── requirements.txt        # Python dependencies
├── crontab                 # Scheduled tasks
├── .env                    # Environment variables (not in git)
├── .env.example            # Template for .env
├── data/                   # SQLite database (not in git)
├── logs/                   # Log files (not in git)
├── docs/                   # Documentation
│   ├── AGENTS.md
│   ├── GITOPS_NOTES.md
│   └── WEBHOOK_SETUP.md
├── scripts/                # Utility scripts
│   ├── startup.sh
│   ├── apply_trusted_ips.sh
│   └── diagnose.sh
└── deploy/
    └── webhook.sh          # Deployment script
```

### Data Sources

**TradingView Scanner API**
- Used for real-time ASX market scanning
- Public endpoint: https://scanner.tradingview.com/australia/scan
- Scans for momentum stocks with gaps (change_from_open)
- No API key required
- Returns ticker, close price, and gap percentage

**Interactive Brokers API**
- Used for order execution and position management
- Real-time market data for entry/exit decisions
- Paper trading mode for safe testing

## Database Schema

### candidates

Stocks flagged for potential entry:

- ticker, headline, scan_date, status, gap_percent, prev_close

### positions

Active and historical positions:

- id, ticker, quantity, entry_price, stop_loss, entry_date, status, half_sold, exit_date, exit_price

### trades

All executed trades:

- id, ticker, action, quantity, price, timestamp, position_id, pnl, notes

## Development

### Edit bot.py from iPhone

```bash
# Use nano editor in Termius
cd /opt/skim
nano bot.py

# Save changes (Ctrl+O, Enter, Ctrl+X)

# Rebuild and restart
docker-compose up -d --build
```

### Test Individual Methods

```bash
# Each method can be called independently
docker-compose exec bot python /app/bot.py scan
docker-compose exec bot python /app/bot.py monitor
docker-compose exec bot python /app/bot.py execute
docker-compose exec bot python /app/bot.py manage_positions
docker-compose exec bot python /app/bot.py status
```

## Configuration

Key environment variables in `.env`:

- `IB_USERNAME` / `IB_PASSWORD`: IB credentials
- `PAPER_TRADING`: Safety flag (true/false)
- `GAP_THRESHOLD`: Gap % to trigger entry (default: 3.0)
- `MAX_POSITION_SIZE`: Max shares per position (default: 1000)
- `MAX_POSITIONS`: Max concurrent positions (default: 5)

## Support

For issues or questions:
- Check logs: `docker-compose logs bot`
- Review database: `sqlite3 data/skim.db`
- Verify IB connection: `docker-compose logs ibgateway`

## License

MIT License - See LICENSE file

---

Built with Claude Code + Termius + DigitalOcean.
