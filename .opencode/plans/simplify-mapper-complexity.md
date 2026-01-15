# Simplify Mapper Complexity

## Problem

Bidirectional conversion between domain and persistence models was error-prone due to:

1. **Value object conversions**: `Ticker` ↔ string, `Price` ↔ float
2. **Timestamp handling**: Domain uses `datetime`, persistence uses ISO strings
3. **Optional fields**: `orh_data` required defaulting
4. **Multiple mappers**: Each direction needed separate logic

## Root Causes

1. Domain models use rich value objects (`Ticker`, `Price`)
2. Persistence uses primitive types (strings, floats)
3. No abstraction layer for common conversion patterns
4. Duplicated logic across multiple mappers

## Current Mapper Implementation

```python
def map_table_to_candidate(table: CandidateTable, orh_table: ORHCandidateTable | None = None) -> Candidate:
    orh_data = None
    if orh_table:
        orh_data = ORHCandidateData(
            gap_percent=orh_table.gap_percent,
            conid=orh_table.conid,
            # ... many more fields
            or_high=orh_table.or_high or 0.0,  # Fallback needed
            or_low=orh_table.or_low or 0.0,
        )

    return Candidate(
        ticker=Ticker(table.ticker),  # Conversion needed
        scan_date=datetime.fromisoformat(table.scan_date),  # Conversion needed
        # ... more conversions
        orh_data=orh_data,
    )

def map_candidate_to_table(candidate: Candidate) -> CandidateTable:
    return CandidateTable(
        ticker=candidate.ticker.symbol,  # Reverse conversion
        scan_date=candidate.scan_date.isoformat(),  # Reverse conversion
        # ... more reverse conversions
    )
```

**Pain Points:**
- Repetitive `datetime.isoformat()` / `datetime.fromisoformat()`
- Repetitive `Ticker()` wrapping/unwrapping
- Repetitive `Price()` wrapping/unwrapping
- Manual `or 0.0` fallbacks for None values

## Proposed Solutions

### Option A: Value Object Serialization Protocol (Recommended)

Add `to_persistence()` and `from_persistence()` methods to value objects:

```python
class Ticker:
    symbol: str

    @classmethod
    def from_persistence(cls, value: str) -> "Ticker":
        return cls(symbol=value)

    def to_persistence(self) -> str:
        return self.symbol


class Price:
    value: float
    timestamp: datetime

    @classmethod
    def from_persistence(cls, value: float) -> "Price":
        return cls(value=value, timestamp=datetime.now())

    def to_persistence(self) -> float:
        return self.value
```

Then mappers become:

```python
def map_table_to_candidate(table: CandidateTable, orh_table: ORHCandidateTable | None = None) -> Candidate:
    orh_data = None
    if orh_table:
        orh_data = ORHCandidateData(**orh_table.model_dump())

    return Candidate(
        ticker=Ticker.from_persistence(table.ticker),
        scan_date=datetime.fromisoformat(table.scan_date),
        # ... clean, no manual conversions
    )
```

**Pros:**
- Encapsulates conversion logic in value objects
- Mappers become declarative
- Single source of truth for conversions
- Testable in isolation

**Cons:**
- Requires changes to domain value objects
- Adds methods to pure domain layer

### Option B: Generic Mapper Mixins

Create reusable mapper functions:

```python
from datetime import datetime

def map_datetime(dt_str: str | None) -> datetime | None:
    """Map ISO string to datetime"""
    return datetime.fromisoformat(dt_str) if dt_str else None

def map_datetime_reverse(dt: datetime | None) -> str | None:
    """Map datetime to ISO string"""
    return dt.isoformat() if dt else None

def map_float_or_none(value: float | None, default: float = 0.0) -> float:
    """Map float with None fallback"""
    return value if value is not None else default

def map_price(price: Price | None) -> float | None:
    """Map Price value object to float"""
    return price.value if price else None
```

Then mappers use helpers:

```python
def map_table_to_candidate(table: CandidateTable) -> Candidate:
    return Candidate(
        ticker=Ticker(table.ticker),  # Still need conversion
        scan_date=map_datetime(table.scan_date),  # Cleaner
        # ...
    )
```

**Pros:**
- No changes to domain models
- Reusable across all mappers
- Centralized conversion logic

**Cons:**
- Still some boilerplate
- Helper functions scattered

### Option C: Pydantic/SQLModel Hybrid

Use SQLModel as domain models directly (not recommended for hexagonal):

```python
from sqlmodel import Field, SQLModel

class Candidate(SQLModel, table=True):
    ticker: str = Field(primary_key=True)
    scan_date: datetime = Field(default_factory=datetime.now)
    # ... persistence fields directly in domain
```

**Pros:**
- No mappers needed
- Automatic database schema

**Cons:**
- **Violates hexagonal architecture**
- Domain coupled to persistence details
- Can't test domain without SQLModel
- Loses value object semantics

## Recommendation

**Option A (Value Object Serialization Protocol)** - this aligns with DDD principles and keeps the hexagonal architecture intact.

### Implementation Steps

1. [ ] Add `from_persistence()` class method to `Ticker`
2. [ ] Add `to_persistence()` method to `Ticker`
3. [ ] Add `from_persistence()` class method to `Price`
4. [ ] Add `to_persistence()` method to `Price`
5. [ ] Update `map_table_to_candidate()` to use new methods
6. [ ] Update `map_candidate_to_table()` to use new methods
7. [ ] Add unit tests for serialization methods
8. [ ] Run full test suite to verify no regressions

## Test Coverage Needed

```python
def test_ticker_serialization():
    ticker = Ticker(symbol="BHP")
    assert ticker.to_persistence() == "BHP"
    assert Ticker.from_persistence("BHP") == ticker

def test_price_serialization():
    price = Price(value=46.50, timestamp=datetime.now())
    assert price.to_persistence() == 46.50
    # from_persistence creates with current timestamp

def test_mapper_uses_serialization():
    # Verify mapper uses new methods
    table = CandidateTable(ticker="BHP", ...)
    candidate = map_table_to_candidate(table)
    assert candidate.ticker.symbol == "BHP"
```

## Files to Change

- `src/skim/domain/models/ticker.py` - Add serialization methods
- `src/skim/domain/models/price.py` - Add serialization methods
- `src/skim/infrastructure/database/trading/mappers.py` - Use serialization
- `tests/domain/test_value_objects.py` - Add serialization tests (create if needed)
