# Skim - ASX Trading Bot

Automated ASX trading bot using a multi-strategy architecture with Strategy pattern. Connects directly to Interactive Brokers via OAuth 1.0a.

## Features

- Multi-strategy architecture with strategy-specific candidate repositories
- ORH breakout strategy (Opening Range High)
- Easy to add new trading strategies
- Cron-scheduled trading workflow
- SQLite data persistence
- Discord webhook notifications
- Lightweight deployment

## Documentation

- **[ARCHITECTURE](docs/ARCHITECTURE.md)** - System design, Strategy pattern, and trading workflow
- **[DEVELOPMENT](docs/DEVELOPMENT.md)** - Local setup, testing, deployment, configuration
- **[INTEGRATIONS](docs/INTEGRATIONS.md)** - Discord webhooks and IBKR API setup
- **[SECURITY](docs/SECURITY.md)** - Security and secrets management

## Quick Start

```bash
# Install dependencies
uv sync

# Run bot commands
uv run python -m skim.core.bot scan              # Run strategy scan
uv run python -m skim.core.bot trade             # Execute trades
uv run python -m skim.core.bot manage            # Manage positions
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

