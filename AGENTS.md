# AGENTS

## Project Overview

Skim: ASX trading automation with historical analysis. Hexagonal architecture with domain-driven design.

- **trading/** - Production bot (strict standards)
- **analysis/** - Research CLI (relaxed standards)
- **shared/** - Historical data service (strict standards)

ORH breakout strategy. Cron-driven phases. Python 3.13+, uv, pytest, ruff.

## Commands

```bash
uv run pytest                              # All tests
uv run ruff check src tests                # Lint
uv run ruff format src tests               # Format
uv run pre-commit run --all-files          # Pre-commit
```

## Trading Bot

```bash
uv run python -m skim.trading.core.bot purge_candidates
uv run python -m skim.trading.core.bot scan
uv run python -m skim.trading.core.bot trade
uv run python -m skim.trading.core.bot manage
uv run python -m skim.trading.core.bot status
```

## Analysis CLI

```bash
uv run skim-analyze top 2024 --json
uv run skim-analyze gaps 2024 --limit 10 --json
```

## Style

- 80 chars max, double quotes, 4 spaces
- Type hints: `str | None`, not `Optional[str]`
- Classes: PascalCase, functions: snake_case, constants: UPPER_SNAKE_CASE
- Google-style docstrings

## Architecture

```
src/skim/
├── domain/           # Business logic (strategies, models, protocols)
├── application/      # Use cases (events, services, commands)
├── infrastructure/   # External integrations (IBKR, database)
├── trading/          # Bot orchestrator, brokers
├── analysis/         # Research CLI
└── shared/           # Historical data
```

## Adding Strategies

1. Create `src/skim/trading/strategies/<name>/<name>.py`
2. Add `@register_strategy("name")` decorator
3. Create repository in `src/skim/trading/data/repositories/`
4. Tests in `tests/domain/`

Auto-registered via decorator. StrategyContext injected with all dependencies.

## Testing

- `@pytest.mark.unit` - Fast, mocked
- `@pytest.mark.integration` - Requires IBKR credentials
- `@pytest.mark.manual` - Not run in CI

## Database

- SQLite: `./data/skim.db` (dev), `/opt/skim/data/skim.db` (prod)
- OAuth keys: `oauth_keys/` directory
- Config: `.env` file

## Deployment

- GitOps: push to main
- Cron: see `crontab`
- Logs: `./logs/` (dev), `/opt/skim/logs/` (prod)
