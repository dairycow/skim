# Skim Trading Bot - Test Suite

This directory contains the test suite for the Skim trading bot, including unit tests, integration tests, and manual tests.

## Test Structure

```
tests/
├── conftest.py                  # Shared pytest fixtures
├── fixtures/                    # Test data and mock responses
│   ├── rsa_keys/               # Test-only RSA keys (safe to commit)
│   └── ibkr_responses/         # Sanitized IBKR API responses
├── unit/                        # Fast, isolated unit tests
│   ├── test_database.py
│   ├── test_models.py
│   ├── test_scanners.py
│   ├── test_strategy.py
│   └── brokers/
│       ├── test_ibkr_oauth.py  # OAuth LST generation tests
│       └── test_ibkr_client.py # IBKR client tests
├── integration/                 # Integration tests (mocked HTTP)
│   ├── test_oauth_flow.py      # Full OAuth flow
│   └── test_order_lifecycle.py # Order placement workflow
└── manual/                      # Manual tests (require real credentials)
    └── ...                      # Not run in CI/CD

```

## Test Categories

### Unit Tests (`tests/unit/`)
- **What**: Tests for individual functions/methods in isolation
- **Mocking**: Everything external (HTTP, file I/O, random, time)
- **Speed**: Very fast (milliseconds)
- **Dependencies**: None (100% offline)
- **CI/CD**: ✅ Always run
- **Marker**: `@pytest.mark.unit`

**Example**:
```bash
pytest tests/unit/ -v
```

### Integration Tests (`tests/integration/`)
- **What**: Tests for complete workflows with multiple components
- **Mocking**: HTTP only (real crypto logic, mocked API responses)
- **Speed**: Fast (seconds)
- **Dependencies**: Test fixtures only
- **CI/CD**: ✅ Always run
- **Marker**: `@pytest.mark.integration`

**Example**:
```bash
pytest tests/integration/ -v
```

### Manual Tests (`tests/manual/`)
- **What**: End-to-end tests with real IBKR paper trading account
- **Mocking**: None (real API calls, real credentials)
- **Speed**: Slow (minutes, network latency)
- **Dependencies**: Real IBKR credentials, PEM keys, network access
- **CI/CD**: ❌ Never run (require secrets)
- **Marker**: `@pytest.mark.manual`

**Example**:
```bash
# Skipped by default
pytest tests/manual/ -v

# Run with marker
pytest -m manual
```

## Running Tests

### Install Test Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- `pytest` - Test framework
- `pytest-mock` - Mocking helpers
- `pytest-cov` - Coverage reports
- `responses` - HTTP mocking
- `freezegun` - Time mocking

### Run All Tests (Unit + Integration)

```bash
pytest
```

### Run Only Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Only Integration Tests

```bash
pytest tests/integration/ -v
```

### Run with Coverage

```bash
pytest --cov=src/skim --cov-report=html
```

Opens `htmlcov/index.html` with detailed coverage report.

### Run Specific Test File

```bash
pytest tests/unit/brokers/test_ibkr_oauth.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/brokers/test_ibkr_oauth.py::TestGenerateLST::test_generate_lst_success -v
```

## Test Fixtures

### OAuth Test Fixtures

Located in `tests/fixtures/`:

#### RSA Keys (`rsa_keys/`)
- `test_signature_key.pem` - Test RSA key for OAuth signatures
- `test_encryption_key.pem` - Test RSA key for token decryption
- **Safe to commit** - These are test-only keys, NOT production keys

#### IBKR API Responses (`ibkr_responses/`)
- `lst_success.json` - Successful LST generation response
- `session_init_success.json` - Session initialization response
- `account_list.json` - Account list response
- `contract_search_bhp.json` - Contract search for BHP stock
- `order_placed.json` - Order placement response

### Pytest Fixtures (`conftest.py`)

- `test_db` - In-memory SQLite database
- `sample_candidate` - Test candidate model
- `sample_position` - Test position model
- `sample_trade` - Test trade model
- `sample_market_data` - Test market data
- `mock_ibkr_client` - Mocked IBKR client
- **OAuth fixtures**:
  - `test_rsa_keys` - Paths to test RSA keys
  - `mock_oauth_env` - OAuth environment variables
  - `load_fixture` - Helper to load JSON fixtures
  - `mock_lst_response` - LST generation response
  - `mock_session_init_response` - Session init response
  - `mock_account_list_response` - Account list response
  - `mock_contract_search_bhp` - BHP contract search
  - `mock_order_placed_response` - Order placement response

## Mocking Strategy

### HTTP Requests - Use `responses` library

```python
import responses

@responses.activate
def test_api_call():
    responses.post(
        "https://api.ibkr.com/v1/api/endpoint",
        json={"result": "success"},
        status=200
    )
    # Your test code
```

### Time/Date - Use `freezegun`

```python
from freezegun import freeze_time

@freeze_time("2025-11-06 12:00:00")
def test_time_dependent():
    # datetime.now() will always return 2025-11-06 12:00:00
```

### Random - Use `mocker.patch`

```python
def test_random_behavior(mocker):
    mocker.patch("random.getrandbits", return_value=12345)
    # random.getrandbits() will always return 12345
```

### File I/O - Use `tmp_path` fixture

```python
def test_file_operations(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # Use test_file in your test
```

## Coverage Goals

- **Overall**: 80%+ coverage
- **`ibkr_oauth.py`**: 90%+ coverage
- **`ibkr_client.py`**: 85%+ coverage
- **Core bot logic**: 85%+ coverage

Check coverage:
```bash
pytest --cov=src/skim --cov-report=term --cov-fail-under=80
```

## CI/CD Integration

Tests run automatically on GitHub Actions:
- Triggered on every push and pull request
- Runs unit + integration tests only (no manual tests)
- Requires 80%+ code coverage to pass
- No IBKR credentials required

See `.github/workflows/test.yml` for configuration.

## Writing New Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    def test_success_case(self):
        # Arrange
        # Act
        # Assert
        pass

    def test_error_case(self):
        with pytest.raises(ExpectedError):
            # Code that should raise error
            pass
```

### Integration Test Template

```python
import pytest
import responses

@pytest.mark.integration
@responses.activate
def test_workflow(mock_oauth_env):
    # Mock HTTP responses
    responses.post("https://api.ibkr.com/...", json={...})

    # Test complete workflow
    # ...
```

## Best Practices

1. **Test file naming**: `test_<module>.py`
2. **Test function naming**: `test_<what>_<condition>_<expected>`
3. **Use markers**: `@pytest.mark.unit` or `@pytest.mark.integration`
4. **Mock external dependencies**: HTTP, file I/O, time, random
5. **Use fixtures**: Reuse common setup code
6. **Assert clearly**: One concept per test
7. **Test both success and failure paths**
8. **Keep tests isolated**: No shared state between tests

## Troubleshooting

### Test fails with "Test RSA key not found"
Ensure test keys are generated:
```bash
cd tests/fixtures/rsa_keys
openssl genrsa -out test_signature_key.pem 2048
openssl genrsa -out test_encryption_key.pem 2048
```

### Import errors
Install dev dependencies:
```bash
pip install -e ".[dev]"
```

### Coverage too low
Add tests for uncovered code:
```bash
pytest --cov=src/skim --cov-report=html
open htmlcov/index.html  # See which lines need coverage
```

## Security Note

**Never commit production credentials to version control!**

- Test RSA keys in `tests/fixtures/rsa_keys/` are safe (test-only)
- Real credentials belong in `.env` (gitignored)
- Manual tests in `tests/manual/` are gitignored if they contain secrets
- CI/CD tests run without any real credentials

## Questions?

See:
- [pytest documentation](https://docs.pytest.org/)
- [responses documentation](https://github.com/getsentry/responses)
- [freezegun documentation](https://github.com/spulec/freezegun)
