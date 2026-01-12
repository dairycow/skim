# Skim - ASX Trading Bot & Analysis Platform

Monorepo containing ASX trading automation and historical analysis tools.

## Structure

This is a workspace-style monorepo with three modules:

- **trading/** - Production trading bot (strict standards)
- **analysis/** - Historical data analysis CLI (relaxed standards)
- **shared/** - Shared utilities (strict standards)

## Features

### Trading Bot
- Multi-strategy architecture with strategy-specific candidate repositories
- ORH breakout strategy (Opening Range High)
- Easy to add new trading strategies
- Cron-scheduled trading workflow
- SQLite data persistence
- Discord webhook notifications
- Lightweight deployment

### Analysis CLI
- Load and analyze ASX stock data
- Find top performers, gaps, momentum bursts
- Pattern analysis and consolidation detection
- Company information lookup
- Historical announcement scraping

## Documentation

- **[ARCHITECTURE](docs/ARCHITECTURE.md)** - System design, Strategy pattern, and trading workflow
- **[DEVELOPMENT](docs/DEVELOPMENT.md)** - Local setup, testing, deployment, configuration
- **[INTEGRATIONS](docs/INTEGRATIONS.md)** - Discord webhooks and IBKR API setup
- **[SECURITY](docs/SECURITY.md)** - Security and secrets management

## Quick Start

### Install Dependencies

```bash
uv sync
```

### Trading Bot Commands

```bash
uv run python -m skim.trading.core.bot scan              # Run strategy scan
uv run python -m skim.trading.core.bot trade             # Execute trades
uv run python -m skim.trading.core.bot manage            # Manage positions
```

### Analysis CLI Commands

```bash
# Install analysis dependencies
uv pip install -e ".[analysis]"

# Run interactive analysis
uv run skim-analyze

# Non-interactive usage
uv run skim-analyze top 2024 --json
uv run skim-analyze gaps 2024 --limit 10 --json
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

