# Skim - ASX Pivot Trading Bot

Production-ready ASX pivot trading bot with modern layered architecture. Uses OAuth 1.0a authentication to connect directly to Interactive Brokers API - no Gateway needed! Optimized for iPhone deployment via Termius + DigitalOcean.

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
- OAuth 1.0a credentials generated from IBKR portal
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

### Step 2: Generate OAuth Credentials

Follow the IBind OAuth guide to generate credentials:
https://github.com/Voyz/ibind/wiki/OAuth-1.0a

You'll need to:
1. Generate consumer key from IBKR portal
2. Create RSA keys for signature and encryption
3. Generate DH parameters
4. Extract DH prime from dhparam.pem

### Step 3: Configure Environment Variables

Edit `.env` with your OAuth credentials:

```bash
# OAuth Configuration
OAUTH_CONSUMER_KEY=your_consumer_key
OAUTH_ACCESS_TOKEN=your_access_token
OAUTH_ACCESS_TOKEN_SECRET=your_access_token_secret
OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem
OAUTH_DH_PRIME=your_dh_prime_hex_string

# Trading Configuration
PAPER_TRADING=true
```

CRITICAL: Ensure `PAPER_TRADING=true` for safety.

### Step 4: Upload OAuth Keys

Copy your generated .pem files to the server:

```bash
# On your local machine
scp -r /path/to/oauth_keys root@your-droplet:/opt/skim/
```

### Step 5: Deploy

```bash
# Start the bot service
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f bot
```

### Step 6: Verify OAuth Authentication

```bash
# Validate OAuth configuration
docker-compose exec bot python /app/scripts/validate_oauth.py

# Test OAuth connection (recommended - comprehensive check)
docker-compose exec bot python /app/scripts/test_oauth_connection.py

# Check bot status
docker-compose exec bot skim status

# Verify paper account (should see DU prefix) and OAuth authentication
docker-compose logs bot | grep -i "oauth\|connected to account"

# You should see:
# "Initializing IBind client with OAuth 1.0a authentication"
# "PAPER TRADING MODE - Account: DU..."
```

### Step 7: Monitor OAuth Connection (Optional)

Run periodic health checks to ensure OAuth connection stays healthy:

```bash
# Monitor connection every 5 minutes (default)
docker-compose exec bot /app/scripts/monitor_oauth.sh

# Monitor every 60 seconds
docker-compose exec bot /app/scripts/monitor_oauth.sh 60

# Run single connection test
docker-compose exec bot python /app/scripts/test_oauth_connection.py
```

## Troubleshooting

### OAuth Authentication Failed (401 Unauthorized)
- Run validation script: `docker-compose exec bot python /app/scripts/validate_oauth.py`
- Test connection: `docker-compose exec bot python /app/scripts/test_oauth_connection.py`
- Check consumer key is correct and matches your paper trading account
- Verify all OAuth credentials in `.env` match what IBKR generated
- Ensure .pem key files are readable: `ls -la /opt/skim/oauth_keys/`
- Check DH prime was extracted correctly (should be a long hex string with no spaces/colons)
- Verify paths in `.env` match actual .pem file locations

### "Invalid Consumer" Error
- Consumer key may be for live trading instead of paper trading
- Generate new OAuth credentials specifically for your paper account
- Check IBKR portal to ensure OAuth is enabled for paper trading

### Module Not Found Errors
- Rebuild container: `docker-compose up -d --build`
- Verify package is installed: `docker-compose exec bot pip show skim`

### Database Errors
- Check database path exists: `docker-compose exec bot ls -la /app/data/`
- Verify database file permissions
- Try recreating database: `rm data/skim.db` (will lose data!)

## Normal Operation

After initial setup, the bot will:
1. Authenticate via OAuth 1.0a directly with IBKR API
2. Connect automatically (no Gateway needed!)
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

**Interactive Brokers API (via OAuth 1.0a)**
- Used for order execution and position management via IBind
- Real-time market data for entry/exit decisions
- Paper trading mode for safe testing
- Direct REST API connection with OAuth 1.0a - no Gateway needed!

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

**OAuth Authentication:**
- `OAUTH_CONSUMER_KEY`: Consumer key from IBKR
- `OAUTH_ACCESS_TOKEN`: Access token from IBKR
- `OAUTH_ACCESS_TOKEN_SECRET`: Access token secret from IBKR
- `OAUTH_SIGNATURE_PATH`: Path to signature .pem file
- `OAUTH_ENCRYPTION_PATH`: Path to encryption .pem file
- `OAUTH_DH_PRIME`: DH prime hex string

**Trading Configuration:**
- `PAPER_TRADING`: Safety flag (true/false)
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
- Verify OAuth authentication in logs

## License

MIT License - See LICENSE file

---

Built with Claude Code + Termius + DigitalOcean.
