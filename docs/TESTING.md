# Testing Guide

This guide covers testing strategies, test structure, and quality assurance for the Skim trading bot.

## Test Structure

```
tests/
├── conftest.py           # Shared pytest fixtures and environment setup
├── fixtures/              # Test data and mocks
│   ├── ibkr_responses/   # IBKR API response samples
│   └── rsa_keys/          # Test RSA keys
├── unit/                   # Unit tests (fast, everything mocked)
│   ├── test_database.py   # Database operations
│   ├── test_models.py     # Data models
│   ├── test_scanners.py   # Market scanners
│   ├── test_strategy.py   # Trading strategy
│   └── brokers/
│       └── test_ibkr_oauth.py  # OAuth authentication
├── integration/            # Integration tests with real services
│   ├── oauth/             # OAuth authentication tests
│   ├── client/            # Client operation tests
│   └── workflow/          # End-to-end workflow tests
└── docs/                  # Test documentation and results
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1 second per test)
- **Mocking**: All external dependencies mocked
- **Examples**: Database operations, model validation, strategy logic

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions
- **Speed**: Medium (1-5 seconds per test)
- **Mocking**: HTTP requests mocked, real database
- **Examples**: End-to-end workflows, API integrations

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions with real services
- **Speed**: Medium to Slow (requires network calls)
- **Mocking**: Minimal mocking (real credentials required)
- **Examples**: OAuth flow, IBKR API calls, end-to-end workflows

## Running Tests

### All Tests
```bash
# Run entire test suite
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/skim --cov-report=html
```

### By Category
```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Integration tests (requires credentials)
uv run pytest tests/integration/ -v
```

### Specific Tests
```bash
# Run specific test file
uv run pytest tests/unit/test_database.py

# Run specific test function
uv run pytest tests/unit/test_database.py::test_create_candidate

# Run tests matching pattern
uv run pytest -k "test_oauth"
```

## Test Markers

### Available Markers
```python
@pytest.mark.unit        # Unit tests (fast, everything mocked)
@pytest.mark.integration # Integration tests (requires real credentials)
```

### Running with Markers
```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run all tests (unit + integration)
uv run pytest
```

## Test Configuration

### Pytest Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
norecursedirs = []
markers = [
    "integration: marks tests as integration tests (requires real credentials)",
    "unit: marks tests as unit tests (fast, everything mocked)",
]
```

### Environment Setup for Tests
```bash
# Test environment file
cp .env.example .env.test

# Set test-specific values
echo "PAPER_TRADING=true" >> .env.test
echo "DB_PATH=:memory:" >> .env.test
echo "LOG_LEVEL=DEBUG" >> .env.test
```

## Writing Tests

### Unit Test Example
```python
import pytest
from unittest.mock import Mock, patch
from skim.data.database import Database
from skim.data.models import Candidate

@pytest.mark.unit
class TestDatabase:
    def test_create_candidate(self):
        """Test creating a candidate in database."""
        # Arrange
        db = Database()
        candidate_data = {
            "symbol": "BHP",
            "gap_percentage": 3.5,
            "status": "watching"
        }
        
        # Act
        candidate = db.create_candidate(candidate_data)
        
        # Assert
        assert candidate.symbol == "BHP"
        assert candidate.gap_percentage == 3.5
        assert candidate.status == "watching"
```

### Integration Test Example
```python
import pytest
import os
from skim.brokers.ibkr_client import IBKRClient

@pytest.mark.integration
class TestIBKRClient:
    def test_real_connection(self):
        """Test real connection to IBKR API."""
        # Arrange
        if not all([
            os.getenv("OAUTH_CONSUMER_KEY"),
            os.getenv("OAUTH_ACCESS_TOKEN"),
        ]):
            pytest.skip("IBKR credentials not available")
        
        client = IBKRClient()
        
        # Act
        accounts = client.get_accounts()
        
        # Assert
        assert isinstance(accounts, list)
        assert len(accounts) > 0
```

## Test Data and Fixtures

### Using Fixtures
```python
import pytest
from skim.data.models import Candidate

@pytest.fixture
def sample_candidate():
    """Create a sample candidate for testing."""
    return Candidate(
        symbol="BHP",
        gap_percentage=3.5,
        status="watching",
        announcement_title="Price Sensitive Announcement"
    )

def test_candidate_creation(sample_candidate):
    """Test candidate creation with fixture."""
    assert sample_candidate.symbol == "BHP"
    assert sample_candidate.gap_percentage == 3.5
```

### Mock Data
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_ibkr_response():
    """Mock IBKR API response."""
    return {
        "id": 12345,
        "symbol": "BHP",
        "status": "Filled",
        "filled_quantity": 100,
        "filled_price": 45.50
    }

def test_order_placement(mock_ibkr_response):
    """Test order placement with mocked response."""
    # Test implementation
    pass
```

## Test Database

### In-Memory Database
```python
import pytest
from skim.data.database import Database

@pytest.fixture
def test_db():
    """Create in-memory database for testing."""
    db = Database(database_path=":memory:")
    db.create_tables()
    yield db
    db.close()

def test_database_operations(test_db):
    """Test database operations with test database."""
    # Test implementation
    pass
```

### Test Fixtures Directory
```
tests/fixtures/
├── ibkr_responses/
│   ├── account_list.json
│   ├── contract_search_bhp.json
│   ├── lst_success.json
│   └── order_placed.json
└── rsa_keys/
    ├── test_signature_key.pem    # Test RSA key for OAuth signatures
    ├── test_encryption_key.pem   # Test RSA key for token decryption
    └── README.md                 # RSA keys security documentation
```

**Important**: The RSA keys in `tests/fixtures/rsa_keys/` are test-only keys that are safe to commit to version control. See [`tests/fixtures/rsa_keys/README.md`](../tests/fixtures/rsa_keys/README.md) for detailed security information.

## Mocking External Services

### HTTP Mocking with `responses`
```python
import responses
import pytest

@responses.activate
def test_ibkr_scanner():
    """Test IBKR scanner with mocked responses."""
    from skim.scanners.ibkr_gap_scanner import IBKRGapScanner
    scanner = IBKRGapScanner(paper_trading=True)
    
    # Mock connection and scan results
    with patch.object(scanner, 'is_connected', return_value=True):
        results = scanner.scan_for_gaps(min_gap=3.0)
    
    # Verify mock data structure (actual implementation will use real IBKR data)
    assert isinstance(results, list)
```

### OAuth Mocking
```python
from unittest.mock import patch, Mock

@patch('skim.brokers.ibkr_oauth.requests.post')
def test_oauth_signature_generation(mock_post):
    """Test OAuth signature generation."""
    mock_post.return_value.json.return_value = {
        "session_id": "test_session",
        "access_token": "test_token"
    }
    
    # Test implementation
    pass
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v2
      - run: uv sync
      - run: uv run pytest tests/unit/ tests/integration/
      - run: uv run pytest --cov=src/skim
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest tests/unit/ tests/integration/
        language: system
        pass_filenames: false
        always_run: true
```

## Test Coverage

### Coverage Configuration
```toml
[tool.coverage.run]
source = ["src/skim"]
omit = ["tests/*", "**/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Coverage Reports
```bash
# Generate coverage report
uv run pytest --cov=src/skim --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Coverage threshold
uv run pytest --cov=src/skim --cov-fail-under=80
```

## Performance Testing

### Timing Tests
```python
import time
import pytest

def test_scanner_performance():
    """Test scanner performance under time limit."""
    from skim.scanners.ibkr_gap_scanner import IBKRGapScanner
    scanner = IBKRGapScanner(paper_trading=True)
    
    start_time = time.time()
    with patch.object(scanner, 'is_connected', return_value=True):
        gaps = scanner.scan_for_gaps(min_gap=3.0)
    end_time = time.time()
    
    execution_time = end_time - start_time
    assert execution_time < 5.0  # Should complete within 5 seconds
    assert len(gaps) > 0
```

### Load Testing
```python
import pytest
from concurrent.futures import ThreadPoolExecutor

def test_concurrent_database_access():
    """Test database under concurrent load."""
    db = Database()
    
    def create_candidate(i):
        return db.create_candidate({
            "symbol": f"TEST{i}",
            "gap_percentage": 3.0,
            "status": "watching"
        })
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_candidate, i) for i in range(100)]
        results = [f.result() for f in futures]
    
    assert len(results) == 100
```

## Debugging Tests

### Debug Mode
```bash
# Run with debugger
uv run pytest --pdb

# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# Run with maximum verbosity
uv run pytest -vv -s
```

### Test Logging
```python
import logging
import pytest

@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    logging.basicConfig(level=logging.DEBUG)

def test_with_logging():
    """Test with debug logging."""
    logging.debug("Starting test")
    # Test implementation
    logging.debug("Test completed")
```

## Best Practices

### Test Organization
1. **One assertion per test** when possible
2. **Descriptive test names** that explain what is being tested
3. **Arrange-Act-Assert** pattern
4. **Independent tests** that don't rely on each other
5. **Mock external dependencies** consistently

### Test Data Management
1. **Use fixtures** for reusable test data
2. **Clean up resources** in teardown
3. **Use factories** for complex object creation
4. **Avoid hardcoded values** in tests
5. **Test edge cases** and error conditions

### Mocking Strategy
1. **Mock at boundaries** (HTTP, database, external APIs)
2. **Use realistic mock data** that matches real responses
3. **Verify mock calls** when testing interactions
4. **Don't over-mock** - test real logic when possible
5. **Use dependency injection** for better testability

## Troubleshooting

### Common Issues

#### Test Database Errors
```bash
# Check database permissions
chmod 666 test.db

# Use in-memory database for tests
DB_PATH=:memory:
```

#### Import Errors
```bash
# Ensure PYTHONPATH includes src
export PYTHONPATH=$PWD/src:$PYTHONPATH

# Or use pytest configuration
python_paths = ["src"]
```

#### Mock Not Working
```bash
# Check patch path
# Should be: module.ClassName.method
@patch('skim.brokers.ibkr_client.requests.post')

# Not:
@patch('requests.post')
```

#### OAuth Test Failures
```bash
# Check environment variables
env | grep OAUTH

# Verify key files exist
ls -la oauth_keys/

# Test with real credentials manually
uv run python -c "from skim.brokers.ibkr_oauth import IBKROAuth; print(IBKROAuth().authenticate())"
```

For additional testing guidance, see the [Development Guide](DEVELOPMENT.md).