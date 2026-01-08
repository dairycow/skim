# CLAUDE.md

## Project Overview

Skim is an automated ASX trading bot that implements an Opening Range High (ORH) breakout strategy. It connects directly to Interactive Brokers via OAuth 1.0a, runs on cron schedules, and uses SQLite for persistence.

## Essential Commands

### Running Tests
```bash
uv run pytest
```

### Code Quality
```bash
# Run all pre-commit checks
uv run pre-commit run --all-files

# Linting only
uv run ruff check src tests

# Formatting
uv run ruff format src tests
```

### Running Bot Commands
```bash
# Execute individual bot workflows
uv run python -m skim.core.bot scan          # Find gap candidates
uv run python -m skim.core.bot track_ranges  # Sample ORH/ORL
uv run python -m skim.core.bot trade         # Execute breakouts
uv run python -m skim.core.bot manage        # Monitor positions
```

## Architecture Overview

### Core Trading Workflow

The bot operates in four distinct phases (all times AEDT):

1. **Scan** (10:00 AM): Find candidates with gaps and announcements
2. **Track Ranges** (10:05 AM): Sample and store ORH/ORL values
3. **Trade** (10:05 AM - 4:00 PM, every 5 min): Execute breakout entries
4. **Manage** (10:05 AM - 4:00 PM, every 5 min): Monitor positions and stops

### Module Responsibilities

**Core Modules** (src/skim/):
- `scanner.py` - Identifies gap candidates with announcements
- `range_tracker.py` - Samples and stores opening range highs/lows
- `trader.py` - Executes breakout entries with stops
- `monitor.py` - Checks positions and triggers stop losses
- `core/bot.py` - Thin orchestrator that dispatches to modules

**Service Layer** (src/skim/brokers/):
- `ibkr_client.py` - IBKR OAuth 1.0a integration
- `ibkr_market_data.py` - Real-time price data
- `ibkr_orders.py` - Order execution
- `ibkr_scanner.py` - Stock scanner integration

**Data Layer** (src/skim/data/):
- `database.py` - SQLite persistence (generic operations only)
- `repositories/` - Strategy-specific candidate repositories
  - `base.py` - CandidateRepository protocol (generic interface)
  - `orh_repository.py` - ORH strategy implementation
- `models.py` - Data models (Candidate, Position, ORHCandidate)

### Status Transitions

**Candidates**: watching → entered → closed
**Positions**: open → closed

## Development Practices

### Toolchain
- **Always use `uv`** for running Python commands and pytest
- This is a modern Python project defined by `pyproject.toml`
- Python 3.13+ required

### Test-Driven Development (RED → GREEN → REFACTOR)
1. Write tests BEFORE implementation
2. Confirm tests fail (RED)
3. Implement until tests pass (GREEN)
4. Refactor while keeping tests green
5. Do NOT modify tests during implementation

### Test Markers
- `@pytest.mark.unit` - Fast tests, everything mocked
- `@pytest.mark.integration` - Requires real IBKR credentials
- `@pytest.mark.manual` - Not run in CI

### Pre-commit Hooks

If pre-commit hooks identify issues, address or document them immediately.

## Critical Implementation Notes

### Broker Integration
- OAuth 1.0a authentication with IBKR (not Gateway)
- Requires OAuth keys in `oauth_keys/` directory
- Paper trading mode controlled by `PAPER_TRADING` env var

### Configuration
- All config in `.env` file (copy from `.env.example`)
- Scanner settings in `src/skim/core/config.py` (ScannerConfig dataclass)
- Critical env vars: `OAUTH_CONSUMER_KEY`, `OAUTH_ACCESS_TOKEN`, `OAUTH_ACCESS_TOKEN_SECRET`, `OAUTH_DH_PRIME`

### Data Persistence
- SQLite database at `./data/skim.db` (dev) or `/opt/skim/data/skim.db` (prod)
- Database survives deployments
- No manual migrations needed (schema auto-created)

### Phase Separation
Each workflow phase (scan, track_ranges, trade, manage) is independent and testable. Modules do NOT call each other - the bot orchestrator dispatches work.

### Testing Strategy
- Unit tests: Mock all IBKR calls using `responses` library
- Integration tests: Require real credentials, marked `@pytest.mark.integration`
- Use `tests/fixtures/` for mock data
- Use `tests/conftest.py` for shared fixtures

## Common Development Tasks

### Adding New Trading Logic
1. Identify which module handles the logic (scanner/trader/monitor)
2. Write tests in `tests/unit/test_<module>.py`
3. Implement in `src/skim/<module>.py`
4. Update `core/bot.py` if adding new workflow phase

### Modifying Scanner Criteria
1. Update `ScannerConfig` in `src/skim/core/config.py`
2. Update tests in `tests/unit/test_scanner.py`
3. Modify `Scanner` class in `src/skim/scanner.py`

### Adding New Trading Strategies
1. Create repository in `src/skim/data/repositories/<strategy>_repository.py` implementing `CandidateRepository` protocol
2. Create strategy table in `src/skim/data/models.py` for strategy-specific data
3. Implement strategy in `src/skim/strategies/<strategy>.py`
4. Register in `src/skim/core/bot.py` _register_strategies() method

### Adding New Broker Features
1. Add method to appropriate service in `src/skim/brokers/`
2. Update protocol in `src/skim/brokers/protocols.py` if needed
3. Write tests in `tests/unit/brokers/test_<service>.py`
4. Mock responses using `responses` library

## Deployment

### Production Environment
- Runs on cron schedules (see `crontab` file)
- GitOps: Push to main triggers automated deployment
- Persistent data: `/opt/skim/data/`, `/opt/skim/logs/`, `/opt/skim/oauth_keys/`
- Uses sudoers for zero-downtime deployments

### Log Locations
- Development: `./logs/*.log`
- Production: `/opt/skim/logs/*.log`
- Cron logs: `/opt/skim/logs/cron.log`
