# Development Guide

This guide covers local development setup, testing, and quality assurance workflows.

## Prerequisites

- Python 3.12+
- uv (unified Python toolchain)
- Git

## Setup

### Install Dependencies
```bash
# Clone repository
git clone https://github.com/your-repo/skim.git
cd skim

# Install dependencies and create virtual environment
uv sync

# Install pre-commit hooks (one-time setup)
uv run pre-commit install
```

### Development Workflow

The project uses UV-based pre-commit hooks for automated quality assurance:
- `uv run ruff check src tests` - Linting
- `uv run ruff format --check src tests` - Code formatting
- `uv run pytest tests/unit/ tests/integration/` - Testing (runs on pre-push)

### Running Quality Checks

Run all quality checks manually:
```bash
uv run pre-commit run --all-files
```

Or run individually:
```bash
# Linting
uv run ruff check src tests

# Code formatting
uv run ruff format src tests

# Testing
uv run pytest tests/unit/ tests/integration/
```

## Testing

### Test Structure
- `tests/unit/` - Fast unit tests with everything mocked
- `tests/integration/` - Integration tests with mocked HTTP only
- `tests/oauth_tests/` - Manual tests requiring real IBKR credentials

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov=src/skim

# Run manual OAuth tests (requires credentials)
uv run pytest tests/oauth_tests/ -m manual
```

### Test Markers
- `@pytest.mark.unit` - Unit tests (fast, everything mocked)
- `@pytest.mark.integration` - Integration tests (mocked HTTP only)
- `@pytest.mark.manual` - Manual tests requiring real credentials

## Code Quality

### Ruff Configuration
- Line length: 80 characters
- Target Python: 3.12
- Enabled rules: pycodestyle, Pyflakes, isort, pyupgrade, flake8-bugbear, flake8-comprehensions, flake8-simplify

### Pre-commit Hooks
The project enforces code quality through pre-commit hooks:
1. **Linting** - Catches code issues and style violations
2. **Formatting** - Ensures consistent code formatting
3. **Testing** - Runs test suite before pushing changes

## Making Changes

1. Create a feature branch
2. Make your changes following TDD (RED -> GREEN -> REFACTOR)
3. Run quality checks: `uv run pre-commit run --all-files`
4. Commit changes (pre-commit hooks will run automatically)
5. Push and create pull request

## Debugging

### Running the Bot Locally
```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run bot commands
uv run python -m skim.core.bot scan
uv run python -m skim.core.bot monitor
uv run python -m skim.core.bot execute
uv run python -m skim.core.bot manage_positions
uv run python -m skim.core.bot status
```

### Logging
Logs are written to `/app/logs/skim_*.log` in production and `logs/` locally during development.

## IDE Configuration

For VS Code, recommended extensions:
- Python
- Ruff
- Python Test Explorer

Configure `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black"
}
```