# CLAUDE.md

## Project Overview

Skim: ASX trading automation with historical analysis. Production trading bot + research CLI.

## Architecture

Hexagonal architecture with three layers:

```
src/skim/
├── domain/           # Business logic (strategies, models, protocols)
├── application/      # Use cases (events, services, commands)
├── infrastructure/   # External integrations (IBKR, database)
├── trading/          # Production bot (orchestrator, brokers)
├── analysis/         # Research CLI
└── shared/           # Historical data service
```

## Essential Commands

```bash
uv run pytest                    # All tests
uv run pytest tests/trading/     # Trading unit tests
uv run ruff check src tests      # Linting
uv run ruff format src tests     # Formatting
```

## Trading Bot Commands

```bash
uv run python -m skim.trading.core.bot purge_candidates
uv run python -m skim.trading.core.bot scan
uv run python -m skim.trading.core.bot trade
uv run python -m skim.trading.core.bot manage
uv run python -m skim.trading.core.bot status
```

## Adding Strategies

1. Create strategy in `src/skim/trading/strategies/<name>/`
2. Add `@register_strategy("name")` decorator to strategy class
3. Create repository in `src/skim/trading/data/repositories/`
4. Tests in `tests/domain/`

Strategy is auto-discovered and registered via the decorator.

## Configuration

- `.env` file (copy from `.env.example`)
- `src/skim/trading/core/config.py` for trading config
- OAuth keys in `oauth_keys/` directory

## Testing

- `@pytest.mark.unit` - Fast, mocked tests
- `@pytest.mark.integration` - Requires IBKR credentials
- `@pytest.mark.manual` - Not run in CI

## Deployment

- GitOps: push to main
- Cron schedules in `crontab`
- Logs: `./logs/` (dev), `/opt/skim/logs/` (prod)
- Data: `./data/skim.db` (dev), `/opt/skim/data/skim.db` (prod)
