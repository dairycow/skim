# Test Execution Efficiency Plan

## Current Performance Metrics

- **Execution time**: 32.2 seconds
- **Total tests**: 395
- **Average per test**: ~80ms
- **Target execution time**: <15 seconds
- **Target improvement**: 50-70% reduction

---

## Performance Analysis

### Identified Bottlenecks

#### 1. Logging Overhead (10-15 seconds potential savings)

**Problem**: Excessive logging during test runs

**Evidence from test output**:
```
2025-11-21 12:11:58.665 | INFO     | skim.core.config:from_env:171 - Configuration loaded:
2025-11-21 12:11:58.665 | INFO     | skim.core.config:from_env:172 -   Client ID: 1
2025-11-21 12:11:58.665 | INFO     | skim.core.config:from_env:173 -   Paper Trading: True
... (20+ lines of config logging per test setup)
```

Each test setup logs the entire configuration, causing significant I/O overhead.

**Impact**: Each test that initialises config adds 10-50ms of logging overhead

**Savings potential**: 5-10 seconds (15-30% improvement)

---

#### 2. Single-Threaded Execution (15-20 seconds potential savings)

**Current approach**: Sequential test execution on single core

**Available optimisation**: Multi-core parallelisation with pytest-xdist

**Hardware capability**: Modern systems have 4-8+ cores available

**Potential speedup**: 4-8x on 4-8 core systems, realistic 2-4x after overhead

**Savings potential**: 10-20 seconds (30-60% improvement)

---

#### 3. Fixture Setup Complexity (3-5 seconds potential savings)

**Problem**: Heavy fixtures recreated per test

**Examples from conftest.py**:
- `ibkr_client_mock_oauth`: Creates real IBKRClient, manipulates environment per test
- `mock_bot_config`: Recreates config per test
- `test_db`: Creates in-memory SQLite per test (acceptable)

**Current scope analysis**:
- Most fixtures: function scope (default)
- `ibkr_client`: module scope (efficient)
- `oauth_config`: module scope (efficient)

**Optimisation opportunities**:
1. Move more fixtures to session scope
2. Cache environment manipulation
3. Use class-scoped fixtures for related test groups

**Savings potential**: 2-5 seconds (6-15% improvement)

---

#### 4. Coverage Calculation Overhead (2-4 seconds potential savings)

**Problem**: Coverage tracking adds per-line overhead

**Current usage**: All tests calculate coverage

**Optimisation**: Split into two hooks with different coverage requirements

**Savings potential**: 1-3 seconds (3-9% improvement when skipped)

---

### Test File Size Analysis

Largest test files (potential targets for parallelisation focus):

| File | Size | Tests | Avg/Test |
|------|------|-------|----------|
| test_bot.py | 1382 lines | ~80 | 17.3 lines |
| test_scanners.py | 1410 lines | ~90 | 15.7 lines |
| test_cron_schedule.py | 571 lines | ~40 | 14.3 lines |
| test_bot_exit_strategy_integration.py | 320 lines | ~15 | 21.3 lines |
| test_bot_position_manager_integration.py | 262 lines | ~13 | 20.2 lines |

These 5 files represent ~50% of test lines but should parallelize efficiently.

---

## Optimisation Strategies

### Strategy 1: Reduce Logging Overhead (Quick Win)

**Priority**: HIGH
**Effort**: 5 minutes
**Expected improvement**: 5-10 seconds

**Implementation**:

1. Add logging suppression to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "-v --tb=short --log-level=WARNING"
```

2. Alternatively, use environment variable in pre-commit hook:

```yaml
- id: pytest-coverage
  entry: uv run pytest tests/unit/ --cov=src --cov-fail-under=80 --log-level=WARNING
```

**Why it works**: 
- Suppresses INFO/DEBUG log messages from config loading
- Keeps WARNING/ERROR for debugging failures
- Reduces file I/O significantly during test setup

**Testing impact**: None - only affects output verbosity

---

### Strategy 2: Parallelise Tests with pytest-xdist (Quick Win)

**Priority**: HIGH
**Effort**: 10 minutes
**Expected improvement**: 10-20 seconds (40-60% on multi-core)

**Implementation**:

1. Add `pytest-xdist` to dev dependencies in `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    # ... existing dependencies
    "pytest-xdist>=3.5.0",
]
```

2. Update pre-commit hook:

```yaml
- id: pytest-coverage
  entry: uv run pytest tests/unit/ -n auto --cov=src --cov-fail-under=80 --cov-report=term-missing --log-level=WARNING
```

3. Alternative (specific core count):

```yaml
entry: uv run pytest tests/unit/ -n 4 --cov=src --cov-fail-under=80
```

**Configuration options**:
- `-n auto`: Automatically detect available cores
- `-n 4`: Use exactly 4 workers
- `-n 8`: Use exactly 8 workers

**Why it works**:
- Distributes independent tests across CPU cores
- Each worker runs tests in parallel
- I/O bound operations (setup) happen in parallel

**Testing impact**:
- Some tests may need `@pytest.mark.serial` if they share state
- Database tests should use separate in-memory instances (already do via `test_db` fixture)

**Realistic improvement** (on 4-core system):
- Sequential: 32 seconds
- With parallelisation: 12-18 seconds
- After logging reduction: 8-12 seconds

---

### Strategy 3: Optimise Fixture Scope (Medium Effort)

**Priority**: MEDIUM
**Effort**: 15-20 minutes
**Expected improvement**: 2-5 seconds

**Current fixtures in conftest.py**:

```python
# Function scope (recreated per test) - PROBLEMATIC
@pytest.fixture
def ibkr_client_mock_oauth():
    # Manipulates environment, creates real client
    # Takes 10-50ms per test

# Module scope (efficient) - GOOD
@pytest.fixture(scope="module")
def oauth_config():
    # Loaded once per module

# Function scope (acceptable)
@pytest.fixture
def test_db():
    # In-memory SQLite is fast
```

**Optimisation actions**:

1. **Move to session scope** (safest):
   ```python
   @pytest.fixture(scope="session")
   def ibkr_client_mock_oauth():
       # Setup once, reuse across all tests
       # Clear state between tests if needed
   ```

2. **Cache environment setup**:
   ```python
   @pytest.fixture(scope="session")
   def oauth_env():
       # Set up environment once
       # Restore after all tests
   ```

3. **Use class scope for related tests**:
   ```python
   @pytest.fixture(scope="class")
   def mock_trading_bot(mock_bot_config):
       # Reuse across test methods in same class
   ```

**Expected improvements**:
- `ibkr_client_mock_oauth`: 100+ tests × 20ms = 2 seconds saved
- `oauth_env`: 50+ tests × 10ms = 0.5 seconds saved
- Total potential: 2-5 seconds

**Risks**:
- Shared state between tests (mitigate: clear state or use isolation)
- Test interdependencies (mitigate: ensure each test is independent)

---

### Strategy 4: Split Coverage & Non-Coverage Hooks (Low Effort)

**Priority**: MEDIUM
**Effort**: 5 minutes
**Expected improvement**: 1-3 seconds

**Current setup**:
- All tests run with coverage tracking every commit

**Optimised setup**:

```yaml
# Fast unit tests - on every commit
- id: pytest-unit-fast
  name: pytest unit tests (fast)
  entry: uv run pytest tests/unit/ -n auto --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [commit]

# Coverage check - on pre-push only
- id: pytest-coverage
  name: pytest with coverage
  entry: uv run pytest tests/unit/ -n auto --cov=src --cov-fail-under=80 --cov-report=term-missing --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [pre-push]
```

**Why it helps**:
- Pre-commit (on every commit): 8-12 seconds without coverage
- Pre-push (before pushing): 12-18 seconds with coverage validation
- Developers get faster feedback during development

---

### Strategy 5: Fixture Data Caching (Advanced)

**Priority**: LOW
**Effort**: 20-30 minutes
**Expected improvement**: 1-2 seconds

**Approach**:

1. Cache mock responses:
   ```python
   @pytest.fixture(scope="session")
   def mock_responses_cache():
       # Load fixture files once
       return {
           "lst_success": load_fixture("lst_success.json"),
           "session_init": load_fixture("session_init_success.json"),
       }
   ```

2. Reuse across tests instead of reloading

**Savings**: Eliminates file I/O for fixture loading (~1-2 seconds total)

---

## Recommended Implementation Roadmap

### Phase 1: Quick Wins (15 minutes total)

1. **Add logging suppression** (5 min)
   - Edit `pyproject.toml`
   - Add `--log-level=WARNING` to addopts

2. **Install pytest-xdist** (5 min)
   - Add to `pyproject.toml` dev dependencies
   - Run `uv sync`

3. **Update pre-commit config** (5 min)
   - Add `-n auto` flag to pytest hooks
   - Test locally

**Expected result after Phase 1**: 15-20 seconds

### Phase 2: Fixture Optimisation (20 minutes)

1. **Move fixtures to appropriate scopes**:
   - `ibkr_client_mock_oauth` → session or class scope
   - `oauth_env` → session scope

2. **Test for regressions**:
   - Run full test suite
   - Verify no shared state issues

3. **Profile improvements**:
   - Measure with `pytest --durations=10`

**Expected result after Phase 2**: 10-15 seconds

### Phase 3: Fine-tuning (Optional)

1. **Cache fixture data** (if still slow)
2. **Profile specific slow tests**
3. **Optimise individual test setup**

---

## Expected Performance Timeline

| Phase | Actions | Time | Cumulative |
|-------|---------|------|-----------|
| Baseline | Current setup | 32s | 32s |
| Phase 1 | Logging + xdist | -12s | 20s |
| Phase 2 | Fixture optimisation | -5s | 15s |
| Phase 3 | Fine-tuning (optional) | -3s | 12s |

**Overall improvement**: 60% reduction (32s → 12s)

---

## Pre-commit Configuration Examples

### Minimal Changes (Just Logging)

```yaml
- id: pytest-coverage
  name: pytest coverage
  entry: uv run pytest tests/unit/ --cov=src --cov-fail-under=80 --cov-report=term-missing --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [pre-push]
```

### Recommended (Logging + Parallelisation)

```yaml
- id: pytest-unit
  name: pytest unit tests
  entry: uv run pytest tests/unit/ -n auto --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false

- id: pytest-coverage
  name: pytest with coverage
  entry: uv run pytest tests/unit/ -n auto --cov=src --cov-fail-under=80 --cov-report=term-missing --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [pre-push]
```

### Optimal (Split hooks with different stages)

```yaml
- id: pytest-unit-fast
  name: pytest unit tests (fast)
  entry: uv run pytest tests/unit/ -n auto --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [commit]

- id: pytest-coverage
  name: pytest coverage (comprehensive)
  entry: uv run pytest tests/unit/ -n auto --cov=src --cov-fail-under=80 --cov-report=term-missing --log-level=WARNING
  language: system
  types: [python]
  pass_filenames: false
  stages: [pre-push]
```

---

## Validation & Monitoring

### Before Implementation

```bash
cd /Users/hf/repos/skim
uv run pytest tests/unit/ -n auto --cov=src --cov-fail-under=80 --cov-report=term-missing --durations=10
```

### Track Performance

Use pytest-benchmark or similar for future monitoring:

```bash
# View slowest tests
uv run pytest tests/unit/ --durations=10

# Profile specific test file
uv run pytest tests/unit/test_bot.py --durations=10
```

---

## Notes

- All optimisations are backwards compatible
- No code changes needed for logging/parallelisation
- Fixture changes require careful testing for shared state
- pytest-xdist works best with independent tests
- Coverage calculation has inherent overhead (unavoidable)

---

## Success Criteria

- [ ] Test execution time reduced to 15-20 seconds
- [ ] All tests still passing
- [ ] Coverage remains at 80%+
- [ ] No shared state issues between parallel tests
- [ ] Developer experience improved with faster feedback
