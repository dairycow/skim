# AGENTS

## Project Overview
Skim: Monorepo with ASX trading automation and historical analysis tools.

- **trading/** - Production trading bot (strict standards, full coverage)
- **analysis/** - Historical data analysis CLI (relaxed standards)
- **shared/** - Shared utilities (strict standards, full coverage)

Current strategy: ORH breakout. Phases driven by cron—see `crontab` for timings. Modern Python (pyproject, 3.13+), uv for all python/pytest/ruff/pre-commit. Use Australian English; no emojis; delegate to subagents when possible.

## Essential Commands

### Testing
- Run all tests: `uv run pytest`
- Run trading unit tests: `uv run pytest tests/trading/ -n auto --log-level=WARNING`
- Run with coverage: `uv run pytest tests/trading/ -n auto --cov=src/skim/trading --cov-report=term-missing`

### Code Quality
- Lint trading: `uv run ruff check src/skim/trading tests/trading`
- Lint analysis: `uv run ruff check src/skim/analysis --fix`
- Lint shared: `uv run ruff check src/skim/shared`
- Format trading: `uv run ruff format src/skim/trading tests/trading`
- Format analysis: `uv run ruff format src/skim/analysis`
- Pre-commit all: `uv run pre-commit run --all-files`

### Trading Bot Execution
- Purge candidates: `uv run python -m skim.trading.core.bot purge_candidates`
- Scan (full strategy scan): `uv run python -m skim.trading.core.bot scan`
- Trade breakouts: `uv run python -m skim.trading.core.bot trade`
- Manage positions: `uv run python -m skim.trading.core.bot manage`
- Health check: `uv run python -m skim.trading.core.bot status`

### Analysis CLI
- Interactive mode: `uv run skim-analyze`
- Top performers: `uv run skim-analyze top 2024 --json`
- Find gaps: `uv run skim-analyze gaps 2024 --limit 10 --json`

## Code Style Guidelines

### Formatting
- Line length: 80 characters (strict)
- Quote style: double quotes for all strings
- Indent: spaces (4 spaces)
- Imports: isort with `known-first-party = ["skim"]`

### Type Annotations
- Always include type hints for function parameters and return values
- Use modern union syntax: `str | None` (not `Optional[str]`)
- Use `from __future__ import annotations` for forward references
- Use `TYPE_CHECKING` import block for protocol type hints to avoid circular imports

### Naming Conventions
- Classes: PascalCase (e.g., `ScannerConfig`, `IBKRClient`)
- Functions/methods: snake_case (e.g., `get_db_path`, `execute_breakouts`)
- Constants: UPPER_SNAKE_CASE (e.g., `BASE_URL`, `REALM`)
- Private attributes: leading underscore (e.g., `_consumer_key`, `_connected`)
- Protocol interfaces: no prefix, just abstract methods (e.g., `MarketDataProvider`)

### Imports
- Standard library first, third-party second, local imports last
- Group related imports with blank lines between groups
- Use absolute imports from project root: `from skim.trading.core.config import Config`
- For type-only imports, use `from typing import TYPE_CHECKING` pattern

### Error Handling
- Create custom exception classes inheriting from a base exception
- Prefix exceptions with module name (e.g., `IBKRAuthenticationError`, `IBKRConnectionError`)
- Always document raises in docstrings with full exception class names
- Use specific exceptions, never bare `except:`

### Docstrings
- Use Google-style docstrings (triple quotes)
- Classes: summary only
- Functions: Args/Returns/Raises sections
- Private methods: docstring optional

### Data Models
- Use `@dataclass` for simple data containers
- Use `@dataclass` with frozen=True for immutable config
- Add `@classmethod` factory methods like `from_db_row(cls, row: dict)` for DB mapping
- Use `@property` for derived attributes (e.g., `is_open`)

### Testing Patterns
- TDD: Write tests first, see them fail, commit tests, implement, refactor
- Never change tests during implementation phase
- Use `pytest.mark.unit` for fast mocked tests
- Use `pytest.mark.integration` for tests requiring external services
- Use `pytest.mark.manual` for tests requiring real IBKR credentials (skip CI)
- Mock external dependencies in unit tests using `mocker.MagicMock()`
- Use pytest fixtures in conftest.py for shared test data
- Test function names: `test_<what>_<condition>_<expected>`
- Session-scoped fixtures for immutable data (config, sample objects)
- Function-scoped fixtures for mutable state (database, clients)

### Database & Configuration
- SQLite at ./data/skim.db (local) or /opt/skim/data/skim.db (prod)
- Environment variables in .env; never commit .env file
- OAuth keys in oauth_keys/ (private_signature.pem, private_encryption.pem)
- Use `get_db_path()` and `get_oauth_key_paths()` for path resolution
- Log configuration values on load at DEBUG level

### Architecture & State
- Monorepo with trading (production), analysis (research), and shared (common) modules
- Strategy pattern: TradingBot delegates to strategy implementations
- Strategies: Independent, self-contained implementations in src/skim/trading/strategies/
- CandidateRepository protocol for strategy-specific candidate management
- Each strategy owns its candidate data through dedicated repository
- Database handles generic operations only (positions, candidate status updates)
- States: Candidates (watching→entered→closed); Positions (open→closed)
- Protocol-based abstractions in brokers/protocols.py for testability
- Core orchestrator: src/skim/trading/core/bot.py (multi-strategy dispatcher)
- Shared services: IBKRClient, Database, Discord (injected into strategies)
- Use async/await for IBKR client operations
- Database and models in data/; persistence handled by Database class
- New strategies create their own repository and table in src/skim/trading/data/repositories/

### Deployment & Logging
- GitOps to prod via main branch
- Logs: ./logs (dev) or /opt/skim/logs (prod)
- Loguru for logging (logger = logging.getLogger(__name__) in modules)
- Log critical events at INFO level, verbose at DEBUG level
- Detect-secrets for secret detection in pre-commit
