# AGENTS

## Project Overview
Skim: Automated ASX ORH breakout bot using IBKR OAuth1. Phases driven by cron—see `crontab` for timings. Modern Python (pyproject, 3.13+), uv for all python/pytest/ruff/pre-commit. Use Australian English; no emojis; delegate to subagents when possible.

## Essential Commands

### Testing
- Run all tests: `uv run pytest`
- Run specific test file: `uv run pytest tests/unit/test_config.py`
- Run specific test function: `uv run pytest tests/unit/test_config.py::TestTradingParameters::test_default_trading_parameters`
- Run only unit tests (fast, mocked): `uv run pytest tests/unit/ -n auto --log-level=WARNING`
- Run integration tests (real IBKR): `uv run pytest tests/integration/ -m integration`
- Run with coverage: `uv run pytest tests/unit/ -n auto --cov=src --cov-report=term-missing`

### Code Quality
- Lint: `uv run ruff check src tests`
- Format: `uv run ruff format src tests`
- Pre-commit all: `uv run pre-commit run --all-files`
- Pre-commit specific: `uv run pre-commit run ruff-check --all-files`

### Bot Execution
- Purge candidates: `uv run python -m skim.core.bot purge_candidates`
- Scan gaps: `uv run python -m skim.core.bot scan_gaps`
- Scan news: `uv run python -m skim.core.bot scan_news`
- Track opening ranges: `uv run python -m skim.core.bot track_ranges`
- Trade breakouts: `uv run python -m skim.core.bot trade`
- Manage positions: `uv run python -m skim.core.bot manage`

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
- Use absolute imports from project root: `from skim.core.config import Config`
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
- Phases are independent: core modules do not call each other
- States: Candidates (watching→entered→closed); Positions (open→closed)
- Protocol-based abstractions in brokers/protocols.py for testability
- Core orchestrator: src/skim/core/bot.py
- Use async/await for IBKR client operations
- Database and models in data/; persistence handled by Database class

### Deployment & Logging
- GitOps to prod via main branch
- Logs: ./logs (dev) or /opt/skim/logs (prod)
- Loguru for logging (logger = logging.getLogger(__name__) in modules)
- Log critical events at INFO level, verbose at DEBUG level
- Detect-secrets for secret detection in pre-commit
