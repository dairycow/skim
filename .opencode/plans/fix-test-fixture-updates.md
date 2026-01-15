# Fix Test Fixture Updates

## Problem

Tests were tightly coupled to old models (`trading.data.models`). After deleting this module, all fixtures that created plain strings/floats for model fields broke.

## Example of Breakage

**Old fixture (broken):**
```python
@pytest.fixture
def sample_gap_candidate():
    return GapStockInPlay(
        ticker="BHP",  # Plain string
        scan_date="2025-11-03",  # Plain string
        gap_percent=5.0,  # Plain float
        conid=8644,
    )
```

**New requirement (working):**
```python
@pytest.fixture
def sample_gap_candidate():
    return GapCandidate(
        ticker=Ticker("BHP"),  # Value object
        scan_date=datetime(2025, 11, 3),  # datetime object
        gap_percent=5.0,
        conid=8644,
    )
```

## Root Causes

1. **Tight coupling**: Tests imported concrete model classes
2. **No factory pattern**: Created objects manually with primitive types
3. **Mixed semantics**: Some tests used domain types, some used trading types
4. **No test base classes**: Duplicated fixture logic across test files

## Current State

After refactor, `tests/trading/unit/conftest.py` was updated to:
- Import domain models directly
- Use `Ticker` and `Price` value objects
- Create proper `datetime` objects
- Import `datetime` inside fixtures (not at module level)

But there are still 33 test files that haven't been audited.

## Proposed Solutions

### Option A: Factory Fixture Pattern (Recommended)

Create a factory module for test data:

```python
# tests/factories.py
"""Test data factories using factory_boy or manual creation"""

from datetime import datetime
from skim.domain.models import GapCandidate, NewsCandidate, Position, Ticker, Price

class CandidateFactory:
    """Factory for creating test candidates"""

    @staticmethod
    def gap_candidate(
        ticker: str = "BHP",
        scan_date: datetime | None = None,
        gap_percent: float = 5.0,
        conid: int | None = 8644,
    ) -> GapCandidate:
        return GapCandidate(
            ticker=Ticker(ticker),
            scan_date=scan_date or datetime.now(),
            gap_percent=gap_percent,
            conid=conid,
        )

    @staticmethod
    def news_candidate(
        ticker: str = "BHP",
        scan_date: datetime | None = None,
        headline: str = "Results Released",
    ) -> NewsCandidate:
        return NewsCandidate(
            ticker=Ticker(ticker),
            scan_date=scan_date or datetime.now(),
            headline=headline,
        )

class PositionFactory:
    """Factory for creating test positions"""

    @staticmethod
    def position(
        ticker: str = "BHP",
        quantity: int = 100,
        entry_price: float = 46.50,
        stop_loss: float = 43.00,
    ) -> Position:
        now = datetime.now()
        return Position(
            ticker=Ticker(ticker),
            quantity=quantity,
            entry_price=Price(value=entry_price, timestamp=now),
            stop_loss=Price(value=stop_loss, timestamp=now),
            entry_date=now,
            status="open",
        )
```

**Usage in tests:**
```python
from tests.factories import CandidateFactory

def test_something():
    candidate = CandidateFactory.gap_candidate(gap_percent=7.5)
    # Tests only change what they care about
```

**Pros:**
- Centralized test data creation
- Consistent value object usage
- Easy to change defaults globally
- Reduces test fixture boilerplate

**Cons:**
- Adds new file/module
- Learning curve for team

### Option B: Base Test Class with Helper Methods

```python
# tests/base.py

class DomainTestBase:
    """Base class with domain model helpers"""

    def make_ticker(self, symbol: str = "BHP") -> Ticker:
        return Ticker(symbol)

    def make_price(self, value: float) -> Price:
        return Price(value=value, timestamp=datetime.now())

    def make_datetime(self, *args, **kwargs) -> datetime:
        if not args and not kwargs:
            return datetime.now()
        return datetime(*args, **kwargs)
```

**Usage in tests:**
```python
class TestGapScanner(DomainTestBase):
    def test_scan(self):
        candidate = GapCandidate(
            ticker=self.make_ticker("RIO"),
            scan_date=self.make_datetime(2025, 11, 3),
            gap_percent=5.0,
        )
```

**Pros:**
- No new module dependency
- Pythonic OOP pattern
- Easy to override in subclasses

**Cons:**
- Requires all test classes to inherit
- Still boilerplate in test methods

### Option C: Pytest Auto-Use Fixtures

```python
# tests/conftest.py
import pytest
from datetime import datetime
from skim.domain.models import Ticker, Price

@pytest.fixture(autouse=True)
def provide_domain_helpers(request):
    """Add helper methods to all tests"""

    class Helpers:
        @staticmethod
        def ticker(symbol: str = "BHP") -> Ticker:
            return Ticker(symbol)

        @staticmethod
        def price(value: float) -> Price:
            return Price(value=value, timestamp=datetime.now())

    request.node.helpers = Helpers()
```

**Usage in tests:**
```python
def test_scan(request):
    ticker = request.node.helpers.ticker("RIO")
    candidate = GapCandidate(ticker=ticker, ...)
```

**Pros:**
- Available in all tests automatically
- No inheritance needed

**Cons:**
- Non-standard pattern
- LSP/type checkers might complain

## Recommendation

**Option A (Factory Fixture Pattern)** with pytest-factoryboy if desired:

```bash
uv add --dev pytest-factoryboy
```

### Implementation Steps

1. [ ] Create `tests/factories.py` with `CandidateFactory`
2. [ ] Add `PositionFactory` to `tests/factories.py`
3. [ ] Create `MarketDataFactory` if needed
4. [ ] Update `tests/trading/unit/conftest.py` to use factories
5. [ ] Audit and update all test files that create domain objects
6. [ ] Run all tests to verify
7. [ ] Add documentation to `AGENTS.md` about test data patterns

## Files to Audit

Find all direct object creation in tests:

```bash
grep -r "GapCandidate(" tests/
grep -r "NewsCandidate(" tests/
grep -r "Position(" tests/
grep -r "Ticker(" tests/
grep -r "Price(" tests/
```

Expected test files to update:
- `tests/trading/unit/brokers/conftest.py` - Broker test fixtures
- `tests/trading/unit/strategies/orh_breakout/test_trader.py` - Trader tests
- `tests/trading/integration/` - Integration tests
- Any other files creating domain objects directly

## Example Migration

**Before:**
```python
# tests/trading/unit/test_scanner.py
def test_gap_scan():
    candidate = GapCandidate(
        ticker="BHP",
        scan_date="2025-11-03",
        gap_percent=5.0,
        conid=8644,
    )
    # test logic
```

**After:**
```python
# tests/trading/unit/test_scanner.py
from tests.factories import CandidateFactory

def test_gap_scan():
    candidate = CandidateFactory.gap_candidate()
    # test logic
```
