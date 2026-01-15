# Fix Pre-commit Hook Iterations

## Problem

Pre-commit hooks failed multiple times during refactor, requiring 3-4 iterations to pass all checks. This slowed down development workflow.

## Failed Hook Sequence

**Iteration 1:**
```
ruff check (trading).....................................................Failed
- I001 [*] Import block is un-sorted or un-formatted
- F401 [*] Unused imports
```

**Iteration 2:**
```
ruff check (trading).....................................................Failed
- F401 [*] Unused import: map_position_to_table
```

**Iteration 3:**
```
ruff check (trading).....................................................Failed
- I001 [*] Import block is un-sorted or un-formatted (in conftest.py)
```

**Iteration 4:**
```
pytest (trading).........................................................Failed
- ImportError: cannot import name 'MarketData' from 'skim.domain.models'
```

## Root Causes

1. **Late-breaking imports**: Linting revealed import issues only at commit time
2. **Incremental fixes**: Fixing one issue revealed others
3. **No pre-commit during dev**: Linting/formatting not checked during editing
4. **Import cascade**: Changing one import broke multiple files
5. **Unused imports**: Auto-import or copy-paste left unused code

## Current Pre-commit Config

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.407
    hooks:
      - id: pyright
        additional_dependencies:
          - pyright@1.1.407
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
```

## Proposed Solutions

### Option A: Fast Linting in Editor (Recommended)

Configure IDE to run linters on save:

**VS Code:**
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit"
  },
  "ruff.lint.run": "onSave",
  "ruff.format.run": "onSave",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

**PyCharm:**
- Settings → Tools → External Tools → Add
- Name: "Ruff Check"
- Program: `ruff`
- Arguments: `check $FileDir$ --fix`
- Keymap: Ctrl+R, C (optional)

**Pros:**
- Immediate feedback during editing
- No pre-commit surprises
- Catches issues early

**Cons:**
- IDE-specific config
- Doesn't catch CI-only issues

### Option B: Pre-commit Fix Mode

Configure hooks to auto-fix more aggressively:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff-check
        args: [--fix, --exit-zero]  # Continue even if errors
      - id: ruff-format
  - repo: local
    hooks:
      - id: pytest-quick
        name: pytest-quick
        entry: uv run pytest --tb=no -q
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]  # Run before other checks
```

**Pros:**
- Auto-fixes import issues
- Quick test run catches import errors early

**Cons:**
- Pre-commit slower (runs tests)
- Auto-fix might make unwanted changes

### Option C: Pre-commit Stage Grouping

Stage hooks to run in logical order:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff-check
        stages: [pre-commit]  # First
        args: [--fix]
      - id: ruff-format
        stages: [pre-commit]  # First
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.407
    hooks:
      - id: pyright
        stages: [pre-commit]  # Second (after linting)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        stages: [pre-commit]  # Second (after linting)
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        stages: [manual]  # Only run manually, not on every commit
```

**Pros:**
- Logical ordering (fix before type check)
- Faster commits (no tests on every commit)
- Can run tests manually when needed

**Cons:**
- Might miss test failures during commits
- Requires discipline to run tests

### Option D: Makefile Commands

Create convenient make commands:

```makefile
# Makefile
.PHONY: lint test commit

lint:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

test:
	uv run pytest

commit: lint test
	git add -A
	git commit -m "$(MSG)"
```

**Usage:**
```bash
make commit MSG="refactor: add feature"
```

**Pros:**
- Single command
- Runs checks in correct order
- No surprise failures

**Cons:**
- Another layer to maintain
- Team needs to learn new workflow

## Recommendation

**Option A (Fast Linting in Editor)** + **Option C (Stage Grouping)** for pre-commit.

This gives:
1. Immediate feedback during editing
2. Logical hook ordering
3. Fast commits (tests only when needed)
4. CI still runs full test suite

### Implementation Steps

1. [ ] Configure VS Code `settings.json` for Ruff on-save
2. [ ] Update `.pre-commit-config.yaml` to stage hooks
3. [ ] Add `--exit-zero` to ruff-check
4. [ ] Move pytest hook to `stages: [manual]`
5. [ ] Create Makefile for convenience commands
6. [ ] Document workflow in `AGENTS.md`
7. [ ] Test with sample commits

## VS Code Configuration

Add to `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "ruff.enable": true,
  "ruff.lint.enable": true,
  "ruff.lint.run": "onType",
  "ruff.format.enable": true,
  "ruff.organizeImports": true
}
```

## Pre-commit Configuration

```yaml
repos:
  # Format and lint
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff-check
        name: ruff check
        stages: [pre-commit]
        args: [--fix, --exit-zero]  # Auto-fix, don't fail
      - id: ruff-format
        name: ruff format
        stages: [pre-commit]

  # Type check (after linting)
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.407
    hooks:
      - id: pyright
        name: pyright
        stages: [pre-commit]
        args: []
        additional_dependencies:
          - pyright@1.1.407

  # Tests (manual only)
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest
        language: system
        stages: [manual]
        pass_filenames: false

  # Env check
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff-check
        name: check .env.example
        files: ^\.env\.example$
        stages: [pre-commit]
```

## Makefile

```makefile
.PHONY: lint format test commit clean

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
```

## Files to Change

- `.pre-commit-config.yaml` - Update hooks and stages
- `.vscode/settings.json` - Add Ruff on-save config
- `Makefile` - Add convenience commands
- `AGENTS.md` - Document new workflow

## Documentation Update

Add to `AGENTS.md`:

```markdown
## Development Workflow

### During Development
- Ruff runs on-save in your editor (auto-fixes imports and formatting)
- Pyright runs on-type checking in your editor
- Fix errors as they appear

### Before Committing
Option 1: Use pre-commit (runs linting only, not tests)
```bash
git add .
git commit -m "message"  # Pre-commit runs automatically
```

Option 2: Use make commands
```bash
make commit MSG="refactor: add feature"  # Lints and commits
```

### Running Tests
Run tests manually when needed:
```bash
make test                    # Run all tests
uv run pytest -x            # Run until first failure
uv run pytest tests/trading  # Run specific tests
```
```
