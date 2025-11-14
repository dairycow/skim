# Skim - ASX Pivot Trading Bot

Automated ASX trading bot that connects directly to Interactive Brokers via OAuth 1.0a.

## Quick Start

```bash
# Local development
git clone https://github.com/your-repo/skim.git
cd skim
uv sync
cp .env.example .env
# Edit .env with OAuth credentials
uv run python -m skim.core.bot status

# Production deployment
docker-compose up -d
docker-compose logs -f bot
```

## Documentation

- **[README](docs/README.md)** - Quick start, installation, basic usage
- **[ARCHITECTURE](docs/ARCHITECTURE.md)** - System design and trading workflow
- **[DEVELOPMENT](docs/DEVELOPMENT.md)** - Local setup, testing, deployment, configuration
- **[INTEGRATIONS](docs/INTEGRATIONS.md)** - Discord webhooks and IBKR API setup
- **[SECURITY](docs/SECURITY.md)** - Security and secrets management

## Features

- Direct OAuth 1.0a IBKR integration (no Gateway needed)
- ORH breakout strategy with automated entry/exit
- Cron-scheduled trading workflow
- SQLite data persistence
- Discord webhook notifications
- Lightweight deployment (256-512 MB RAM)

## Resource Requirements

- **RAM**: 1 GB minimum (256-512 MB for bot)
- **Storage**: 25 GB SSD
- **Cost**: ~$6/month (50-75% savings vs Gateway)
