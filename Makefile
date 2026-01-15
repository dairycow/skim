.PHONY: lint format test check commit clean

# Lint and format code
lint:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# Just format
format:
	uv run ruff format src/ tests/

# Run tests
test:
	uv run pytest

# Run full check (lint + test)
check: lint test

# Commit with checks
commit: lint
	git add -A
	git status
	@read -p "Enter commit message: " MSG; \
	git commit -m "$${MSG}"; \
	git status

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
