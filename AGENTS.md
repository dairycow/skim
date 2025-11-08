# AGENTS.md

- This is a modern Python project defined by `pyproject.toml`.
- uv is used as the unified toolchain.
- Pre-commit hooks are configured for automated quality assurance.

## EXTREMELY IMPORTANT
- Before using the edit tool YOU MUST follow the Test-Driven Development RED -> GREEN -> REFACTOR cycle.

## Development Workflow

### Pre-commit Hooks
The project uses pre-commit hooks with UV for automated quality checks:
- `uv run ruff check src tests` - Linting
- `uv run ruff format --check src tests` - Code formatting
- `uv run pytest tests/unit/ tests/integration/` - Testing (runs on pre-push)

### Installation
```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files
```

### Quality Assurance
Always run these commands before committing:
```bash
uv run ruff check src tests
uv run ruff format src tests
uv run pytest tests/unit/ tests/integration/
```