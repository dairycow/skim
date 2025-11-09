# Setup Guide

This guide covers environment setup, prerequisites, and deployment instructions for the Skim trading bot.

## Prerequisites

### Infrastructure
- **Server**: DigitalOcean Ubuntu droplet (1 GB RAM minimum)
- **Software**: Docker & Docker Compose installed
- **Account**: Interactive Brokers paper trading account with OAuth 1.0a credentials

### Local Development
- Python 3.12+
- uv (unified Python toolchain)
- Git

## Quick Start

### Production Deployment
```bash
# 1. Clone repository
git clone https://github.com/your-repo/skim.git
cd skim

# 2. Configure environment (see Configuration section)
cp .env.example .env
# Edit .env with your credentials

# 3. Deploy with Docker Compose
docker-compose up -d

# 4. Verify deployment
docker-compose logs -f bot
```

### Local Development Setup
```bash
# 1. Clone and install dependencies
git clone https://github.com/your-repo/skim.git
cd skim
uv sync

# 2. Install pre-commit hooks
uv run pre-commit install

# 3. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 4. Run locally
uv run python -m skim.core.bot status
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

#### Trading Settings
```bash
PAPER_TRADING=true          # Use paper trading (recommended)
GAP_THRESHOLD=3.0           # Minimum gap percentage
MAX_POSITION_SIZE=1000      # Maximum position size
MAX_POSITIONS=5             # Maximum concurrent positions
DB_PATH=/app/data/skim.db   # Database path
```

#### OAuth 1.0a Authentication
```bash
# Generate OAuth credentials at: https://www.interactivebrokers.com/portal
OAUTH_CONSUMER_KEY=your_consumer_key
OAUTH_ACCESS_TOKEN=your_access_token
OAUTH_ACCESS_TOKEN_SECRET=your_encrypted_access_token_secret
OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem
OAUTH_DH_PRIME=your_dh_prime_hex_string
```

#### Discord Webhook (Optional)
```bash
# Create webhook at: https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

### OAuth Key Setup

1. **Generate RSA Keys**:
```bash
openssl genrsa -out private_signature.pem 2048
openssl genrsa -out private_encryption.pem 2048
```

2. **Upload to Server** (production):
```bash
scp -r oauth_keys root@your-server:/opt/skim/
```

3. **Set Permissions**:
```bash
chmod 600 /opt/skim/oauth_keys/*.pem
```

### IBKR OAuth Setup

1. Log into [Interactive Brokers Portal](https://www.interactivebrokers.com/portal)
2. Navigate to **Settings > API > Access**
3. Enable **OAuth 1.0a** 
4. Generate and note:
   - Consumer Key
   - Access Token
   - Access Token Secret
   - DH Prime (hex string)

## Deployment Options

### Option 1: Docker Compose (Recommended)
```bash
# Production deployment
docker-compose up -d --build

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

### Option 2: Manual Deployment
```bash
# Install dependencies
uv sync

# Run bot manually
uv run python -m skim.core.bot scan
uv run python -m skim.core.bot monitor
uv run python -m skim.core.bot execute
```

## Verification

### Check Bot Status
```bash
# Docker
docker exec skim-bot python -m skim.core.bot status

# Local
uv run python -m skim.core.bot status
```

### Check OAuth Authentication
```bash
# Docker logs
docker-compose logs bot | grep -i "oauth\|connected"

# Local logs
uv run python -m skim.core.bot status 2>&1 | grep -i "oauth"
```

### Verify Database
```bash
# Check database file exists
ls -la /app/data/skim.db  # Production
ls -la data/skim.db        # Local
```

## Resource Requirements

### Production (OAuth only)
- **RAM**: 1 GB minimum (256-512 MB for bot)
- **Storage**: 25 GB SSD minimum
- **CPU**: 1 vCPU minimum

### Cost Optimization
With OAuth 1.0a (no IB Gateway):
- **Before**: 2-4 GB RAM (~$12-24/month)
- **After**: 1 GB RAM (~$6/month)
- **Savings**: 50-75% cost reduction

## Troubleshooting

### Common Issues

#### OAuth Authentication Failed
```bash
# Check credentials in .env
cat .env | grep OAUTH

# Verify key files exist
ls -la /opt/skim/oauth_keys/

# Check bot logs
docker-compose logs bot | grep -i "error\|oauth"
```

#### Missing Dependencies
```bash
# Rebuild container
docker-compose down
docker-compose up -d --build

# Local: reinstall dependencies
uv sync
```

#### Database Issues
```bash
# Check database permissions
ls -la /app/data/
chmod 666 /app/data/skim.db
```

### Getting Help

- Check logs: `docker-compose logs bot`
- Verify configuration: `cat .env`
- Test OAuth: `uv run python -m skim.core.bot status`
- Review [trading workflow](TRADING_WORKFLOW.md) for cron issues

## Next Steps

After successful setup:

1. **Monitor**: Check logs and status regularly
2. **Configure**: Adjust trading parameters in `.env`
3. **Automate**: Set up GitOps deployment (see [GITOPS_NOTES.md](GITOPS_NOTES.md))
4. **Test**: Run paper trading before live trading

For detailed trading workflow, see [TRADING_WORKFLOW.md](TRADING_WORKFLOW.md).