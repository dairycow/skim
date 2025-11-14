# Skim - ASX Pivot Trading Bot

Automated ASX trading bot that connects directly to Interactive Brokers via OAuth 1.0a.

## Quick Start

### Prerequisites
- Python 3.12+
- Interactive Brokers paper trading account with OAuth credentials
- Docker & Docker Compose (for production)

### Local Development
```bash
# Clone and install
git clone https://github.com/your-repo/skim.git
cd skim
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your OAuth credentials

# Run bot
uv run python -m skim.core.bot status
```

### Production Deployment
```bash
# Deploy with Docker Compose
docker-compose up -d

# Verify status
docker-compose logs -f bot
```

## System Overview

Skim is a lightweight, cron-scheduled trading bot that:
- Scans ASX market for gap stocks at market open (10:00 AEDT)
- Tracks opening range (OR) for 10 minutes
- Executes orders on opening range high (ORH) breakouts
- Manages positions with automated stop-loss and profit-taking
- Reports daily P&L and position status

### Architecture Highlights
- **Direct IBKR API**: Custom OAuth 1.0a client (no Gateway needed)
- **Lightweight**: 256-512 MB RAM usage
- **Cron-based**: Automated workflow scheduling
- **Data Layer**: SQLite for candidates, positions, and trades
- **Notifications**: Discord webhook integration

### Technology Stack
- Python 3.12 with minimal dependencies
- SQLite database
- Docker containerization
- OAuth 1.0a authentication
- ASX announcements API

## Installation

### OAuth Setup
1. Generate OAuth credentials at [IBKR Portal](https://www.interactivebrokers.com/portal)
2. Navigate to Settings → API → Access
3. Enable OAuth 1.0a and note:
   - Consumer Key
   - Access Token
   - Access Token Secret
   - DH Prime (hex string)

### RSA Keys
```bash
# Generate signature and encryption keys
openssl genrsa -out oauth_keys/private_signature.pem 2048
openssl genrsa -out oauth_keys/private_encryption.pem 2048
chmod 600 oauth_keys/*.pem
```

### Environment Configuration
```bash
# Copy example config
cp .env.example .env

# Essential variables
PAPER_TRADING=true
OAUTH_CONSUMER_KEY=your_key
OAUTH_ACCESS_TOKEN=your_token
OAUTH_ACCESS_TOKEN_SECRET=your_secret
OAUTH_DH_PRIME=your_dh_prime_hex
```

## Basic Usage

### Manual Commands
```bash
# Check status and positions
uv run python -m skim.core.bot status

# Scan for gap stocks
uv run python -m skim.core.bot scan_ibkr_gaps

# Track opening range breakouts
uv run python -m skim.core.bot track_or_breakouts

# Execute ORH breakout orders
uv run python -m skim.core.bot execute_orh_breakouts

# Manage open positions
uv run python -m skim.core.bot manage_positions
```

### Docker Commands
```bash
# Run in Docker
docker-compose exec bot /app/.venv/bin/python -m skim.core.bot status

# View logs
docker-compose logs -f bot

# Restart bot
docker-compose restart bot
```

## Trading Workflow

The bot runs on a cron schedule (UTC times):

1. **00:00:30** - Scan IBKR for gap stocks ≥3%
2. **00:10:30** - Track opening range for 10 minutes
3. **00:12:00** - Execute orders on ORH breakouts
4. ***/5 (market hours)** - Manage positions (stop-loss, profit-taking)
5. **05:30** - Generate daily status report

All times are during ASX market hours (Mon-Fri).

## Configuration

### Trading Parameters
- `GAP_THRESHOLD`: Minimum gap % to consider (default: 3.0)
- `MAX_POSITION_SIZE`: Maximum position in AUD (default: 1000)
- `MAX_POSITIONS`: Maximum concurrent positions (default: 5)
- `STOP_LOSS_PERCENTAGE`: Stop loss % (default: low of day)

### Scanner Settings
Configure in `src/skim/core/config.py`:
- Volume filter: 50,000 shares
- Price filter: $0.50
- OR duration: 10 minutes
- Gap fill tolerance: $1.0

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed configuration options.

## Data Storage

### SQLite Tables
- **candidates**: Stocks identified during scans
- **positions**: Active trading positions
- **trades**: All buy/sell transactions

### File Locations
- Database: `/app/data/skim.db`
- Logs: `/app/logs/skim_*.log`
- OAuth keys: `/opt/skim/oauth_keys/*.pem`

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and trading workflow
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local setup, testing, deployment
- **[INTEGRATIONS.md](INTEGRATIONS.md)** - Discord webhooks and IBKR API
- **[SECURITY.md](SECURITY.md)** - Security and secrets management

## Support

For issues or questions:
- Check bot logs: `docker-compose logs bot`
- Review documentation in `docs/`
- Verify OAuth credentials in `.env`
- Test connection: `uv run python -m skim.core.bot status`

## Resource Requirements

### Production (OAuth only)
- **RAM**: 1 GB minimum (256-512 MB for bot)
- **Storage**: 25 GB SSD minimum
- **CPU**: 1 vCPU minimum
- **Cost**: ~$6/month (DigitalOcean droplet)

### Cost Savings
With OAuth 1.0a (no IB Gateway):
- Before: 2-4 GB RAM (~$12-24/month)
- After: 1 GB RAM (~$6/month)
- Savings: 50-75% cost reduction
