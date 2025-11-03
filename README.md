# Skim - ASX Pivot Trading Bot

Production-ready ASX pivot trading bot with modern layered architecture. Uses Client Portal API for Interactive Brokers paper trading. Optimized for iPhone deployment via Termius + DigitalOcean.

## Strategy Overview

1. Scan ASX market using TradingView scanner API for momentum stocks with gaps >2%
2. Filter candidates to only include stocks with price-sensitive ASX announcements today
3. Monitor for gaps ≥3% at market open
4. Enter on breakout above opening range high
5. Stop loss at low of day
6. Sell half position on day 3
7. Trail remaining with 10-day SMA

## Quick Start (iPhone Deployment)

### Prerequisites

- DigitalOcean Ubuntu 24.04 droplet
- Docker & Docker Compose installed on droplet
- Interactive Brokers paper trading account
- IBKR Mobile app installed on your phone (for 2FA authentication)
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
vim .env  # Edit with your IB credentials
```

### Step 2: Configure Environment Variables

Edit `.env` with your Interactive Brokers credentials:

```bash
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password
PAPER_TRADING=true
```

CRITICAL: Ensure `PAPER_TRADING=true` for safety.

### Step 2.5: Authentication Setup

This bot uses IBeam for automated Client Portal authentication with manual 2FA approval.

**Important**: IBeam requires weekly manual authentication via IBKR Mobile:
1. IBKR Mobile app installed on your phone
2. Mobile authentication enabled in IB Account Management
3. Your phone ready to approve login requests (~weekly)

When IBeam starts, it will automate login and prompt for phone approval. Sessions last ~1 week.

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
docker-compose exec bot skim status

# Verify paper account (should see DU prefix)
docker-compose logs bot | grep "Connected to account"
```

## Detailed Setup

IBeam manages Client Portal authentication automatically. The bot connects via REST API.

### Step 1: Start IBeam (Client Portal Gateway)

```bash
docker-compose up -d ibeam
```

Wait for IBeam to initialize and prompt for authentication:
```bash
docker-compose logs -f ibeam
```

**You'll see**: "Please log in to authenticate" - approve the push notification on your IBKR Mobile app.

### Step 2: Verify IBeam Authentication

Once authenticated, IBeam will show:
```bash
docker-compose logs ibeam | grep -i "authenticated\|success"
```

The session will remain valid for ~1 week before requiring re-authentication.

### Step 3: Start the Bot

```bash
# Start the bot
docker-compose up -d bot

# Watch bot logs
docker-compose logs -f bot
```

### Step 4: Verify Connection

```bash
# Check bot logs for successful connection
docker-compose logs bot | grep "Connected to account"

# You should see:
# "PAPER TRADING MODE - Account: DU..."
# "Client Portal connection established"
```

### Step 5: Run Diagnostic

```bash
chmod +x scripts/diagnose.sh
./scripts/diagnose.sh
```

## Troubleshooting

### Connection Timeout
- IBeam may not be fully authenticated
- Check: `docker-compose logs ibeam`
- Wait for "authenticated successfully" message
- Approve push notification on IBKR Mobile if prompted

### "Not Connected" Error
- IBeam authentication may have expired
- Check: `docker-compose logs ibeam | grep -i "auth\|session"`
- Restart IBeam: `docker-compose restart ibeam`
- Approve new push notification on IBKR Mobile

### Client ID Already in Use
- Change in `.env`:
  ```
  IB_CLIENT_ID=2
  ```
- Restart: `docker-compose restart bot`

### Authentication Issues
- IBeam authentication failed or expired
- Check: `docker-compose logs ibeam | grep -i "auth\|login\|error"`
- Common issues:
  - Push notification not approved on phone
  - IBKR Mobile app not logged in
  - Mobile authentication not enabled in IB portal
- Fix: Restart IBeam and approve new push notification

## Normal Operation

After initial setup, the bot will:
1. Wait for IBeam authentication
2. Connect automatically using lazy initialization
3. Run scheduled tasks via cron
4. Reconnect automatically if connection drops

## Daily Operations (via Termius)

### Check Bot Status

```bash
cd /opt/skim
docker-compose exec bot skim status
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
docker-compose exec bot skim scan

# Monitor for gaps
docker-compose exec bot skim monitor

# Execute orders
docker-compose exec bot skim execute

# Manage positions
docker-compose exec bot skim manage_positions
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
docker-compose restart ibeam
```

### Stop Trading

```bash
docker-compose stop bot
```

### Backup Database

```bash
cp data/skim.db data/skim_backup_$(date +%Y%m%d).db
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
├── src/                    # Source code (refactored package structure)
│   └── skim/
│       ├── __init__.py
│       ├── core/           # Core orchestration layer
│       │   ├── __init__.py
│       │   ├── config.py   # Configuration management
│       │   └── bot.py      # Main trading bot orchestrator
│       ├── data/           # Data layer (database, models)
│       │   ├── __init__.py
│       │   ├── database.py # Database operations
│       │   └── models.py   # Data models (Candidate, Position, Trade)
│       ├── scanners/       # Market scanning layer
│       │   ├── __init__.py
│       │   ├── tradingview.py     # TradingView API scanner
│       │   └── asx_announcements.py  # ASX announcements scraper
│       ├── brokers/        # Broker interface layer
│       │   ├── __init__.py
│       │   ├── ib_interface.py    # IB Protocol definition
│       │   └── ibind_client.py    # IBind Client Portal implementation
│       └── strategy/       # Trading strategy layer
│           ├── __init__.py
│           ├── entry.py            # Entry logic and filters
│           ├── exit.py             # Exit logic (stop loss, trailing)
│           └── position_manager.py # Position sizing and limits
├── docker-compose.yml      # Service orchestration
├── Dockerfile              # Bot container definition
├── pyproject.toml          # Python dependencies and tool config
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

### Component Layers

**Core Layer** (`skim.core`)
- `config.py`: Environment configuration and validation
- `bot.py`: Thin orchestrator coordinating all components

**Strategy Layer** (`skim.strategy`)
- `entry.py`: Entry signals (gap detection, breakout confirmation, announcement filtering)
- `exit.py`: Exit signals (stop loss, half-exit, trailing stops)
- `position_manager.py`: Position sizing and risk management

**Brokers Layer** (`skim.brokers`)
- `ib_interface.py`: Abstract broker interface for testing
- `ibind_client.py`: Client Portal API implementation with IBind

**Scanners Layer** (`skim.scanners`)
- `tradingview.py`: TradingView API for momentum scanning
- `asx_announcements.py`: ASX website scraping for price-sensitive announcements

**Data Layer** (`skim.data`)
- `models.py`: Immutable data models (Position, Candidate, Trade)
- `database.py`: SQLite operations and schema management

### Data Flow

1. **Scan**: TradingView API → ASX announcements → Filter intersection → Store candidates
2. **Monitor**: Check gap thresholds → Mark triggered candidates
3. **Execute**: Calculate position size → Place market orders → Create positions
4. **Manage**: Check exit signals → Execute exits → Update positions

### Data Sources

**TradingView Scanner API**
- Used for real-time ASX market scanning
- Public endpoint: https://scanner.tradingview.com/australia/scan
- Scans for momentum stocks with gaps (change_from_open)
- No API key required
- Returns ticker, close price, and gap percentage

**Interactive Brokers Client Portal API**
- Used for order execution and position management via IBind
- Real-time market data for entry/exit decisions
- Paper trading mode for safe testing
- REST API with automated authentication via IBeam

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

### Edit Code from iPhone

```bash
# Use vim editor in Termius
cd /opt/skim
vim src/skim/core/bot.py  # Edit main bot orchestrator
vim src/skim/scanners/tradingview.py  # Edit scanner logic
# etc.

# Save changes (Ctrl+O, Enter, Ctrl+X)

# Rebuild and restart
docker-compose up -d --build
```

### Test Individual Methods

```bash
# Each method can be called independently
docker-compose exec bot skim scan
docker-compose exec bot skim monitor
docker-compose exec bot skim execute
docker-compose exec bot skim manage_positions
docker-compose exec bot skim status
```

### Package Structure

The bot is now organized as a proper Python package:

- `skim.core`: Configuration and orchestration
- `skim.data`: Database operations and data models
- `skim.scanners`: Market data scanners (TradingView, ASX)
- `skim.brokers`: Broker interface (Interactive Brokers)
- `skim.strategy`: Trading strategy logic

This modular structure makes the code more maintainable and testable while keeping the same CLI interface and deployment workflow.

## Configuration

Key environment variables in `.env`:

- `IB_USERNAME` / `IB_PASSWORD`: IB credentials
- `PAPER_TRADING`: Safety flag (true/false)
- `IB_HOST`: Client Portal host (default: ibeam)
- `IB_PORT`: Client Portal port (default: 5000)
- `IB_CLIENT_ID`: Client ID for connections (default: 1)
- `GAP_THRESHOLD`: Gap % to trigger entry (default: 3.0)
- `MAX_POSITION_SIZE`: Max shares per position (default: 1000)
- `MAX_POSITIONS`: Max concurrent positions (default: 5)
- `DB_PATH`: SQLite database path (default: /app/data/skim.db)

## Testing

The bot includes comprehensive unit tests with pytest:

### Run Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=skim

# Run specific test file
pytest tests/unit/test_entry.py
```

### Test Structure

- `tests/conftest.py`: Shared fixtures (mock IB client, test database, sample data)
- `tests/unit/`: Unit tests for each component
- Mock external dependencies (HTTP, IB API) for fast, reliable testing

## Development Setup

### Local Development

```bash
# Clone and setup
git clone https://github.com/dairycow/skim.git
cd skim

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package and dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run bot locally (requires .env file)
skim status
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

## Support

For issues or questions:
- Check logs: `docker-compose logs bot`
- Review database: `sqlite3 data/skim.db`
- Verify IB connection: `docker-compose logs ibeam`

## License

MIT License - See LICENSE file

---

Built with Claude Code + Termius + DigitalOcean.
