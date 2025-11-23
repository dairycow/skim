# Python 3.13 Upgrade Design

**Date:** 2025-11-23
**Status:** Approved

## Overview

Upgrade project from Python 3.12+ to Python 3.13+ to match the deployed VM environment. This includes updating all dependencies to their latest versions and cleaning up redundant dependency configurations.

## Changes

### 1. Python Version & Configuration Cleanup

**Python Version Updates:**
- Update `requires-python` from `">=3.12"` to `">=3.13"` in pyproject.toml
- Update `tool.ruff.target-version` from `"py312"` to `"py313"` in pyproject.toml

**Dependency Structure Cleanup:**
- Remove the entire `[project.optional-dependencies]` section
- Keep `[dependency-groups]` as the single source of truth for dev dependencies
- Eliminates duplication and aligns with modern uv tooling standards (PEP 735)

**Rationale:** The `[dependency-groups]` section is the newer standard that uv uses and already contains more recent versions. Keeping both sections creates confusion about which dependencies are actually being used.

### 2. Dependency Updates

**Main Dependencies to Update:**
All dependencies in `[project.dependencies]` will be updated to their latest compatible versions:
- beautifulsoup4: 4.12.3 → latest
- httpx: 0.28.1 → latest
- loguru: 0.7.2 → latest
- lxml: 5.3.0 → latest
- pycryptodome: 3.23.0 → latest
- python-dotenv: 1.0.1 → latest
- pydantic: 2.10.5 → latest
- requests: 2.32.4 → latest
- pytz: 2024.1 → latest

**Approach:**
1. Use `uv` to automatically resolve latest compatible versions
2. Maintain exact version pinning (current style) for reproducible deployments
3. Let uv handle dependency resolution and Python 3.13 compatibility checking
4. Review uv.lock to verify all dependencies resolved successfully

**Rationale:** Pinning exact versions is appropriate for a trading bot where deployment consistency is critical.

### 3. Documentation & Testing

**Documentation Updates:**
Update Python version references in:
- docs/DEVELOPMENT.md
- docs/ARCHITECTURE.md
- Any CI/CD configurations
- README.md (if applicable)

Change all references from Python 3.12 to 3.13.

**Testing Strategy:**
1. Run full test suite: `pytest tests/`
2. Verify linting: `ruff check .`
3. Verify formatting: `ruff format --check .`
4. Check application runs: `skim --help`
5. Review any Python 3.13 deprecation warnings

**Build System:**
No changes needed. Current setuptools-based build system is minimal and appropriate.

## Implementation Steps

1. Update Python version requirements in pyproject.toml
2. Remove redundant [project.optional-dependencies] section
3. Update all main dependencies using uv
4. Update documentation files
5. Run test suite and verify all checks pass
6. Commit changes

## Success Criteria

- All tests pass with Python 3.13
- All dependencies resolve without conflicts
- Documentation accurately reflects Python 3.13 requirement
- No redundant dependency configurations remain
- Application runs successfully on Python 3.13
