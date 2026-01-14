# Skim - ASX Trading Bot & Analysis Platform

Automated ASX trading with historical analysis. Production-grade trading bot + research CLI.

## Quick Start

```bash
uv sync
```

## Trading Bot

```bash
uv run python -m skim.trading.core.bot scan     # Find gap candidates
uv run python -m skim.trading.core.bot trade    # Execute breakouts
uv run python -m skim.trading.core.bot manage   # Monitor positions
uv run python -m skim.trading.core.bot status   # Health check
```

## Analysis CLI

```bash
uv run skim-analyze top 2024 --json
uv run skim-analyze gaps 2024 --limit 10 --json
```

## Testing

```bash
uv run pytest
uv run ruff check src tests
```

## Documentation

- [ARCHITECTURE](docs/ARCHITECTURE.md) - System design
- [DEVELOPMENT](docs/DEVELOPMENT.md) - Setup & deployment
