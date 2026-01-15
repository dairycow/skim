# Fix Strategy Name Propagation

## Problem

When saving candidates through mappers, the `strategy_name` field wasn't being set correctly. This caused `purge_candidates()` filtering by `strategy_name` to fail, leaving orphaned records.

## Root Cause

The `map_candidate_to_table()` mapper only copied basic fields:

```python
def map_candidate_to_table(candidate: Candidate) -> CandidateTable:
    return CandidateTable(
        ticker=candidate.ticker.symbol,
        scan_date=candidate.scan_date.isoformat(),
        status=candidate.status,
        strategy_name=candidate.strategy_name,  # This was often ""
        created_at=candidate.created_at.isoformat(),
    )
```

But when creating `GapCandidate` or `NewsCandidate`, the `strategy_name` wasn't explicitly set, defaulting to empty string `""` in the domain model:

```python
@dataclass
class Candidate:
    strategy_name: str = field(default="")  # ❌ Default is empty string
```

In the repository, we had to manually set it:

```python
if not base_candidate:
    base_candidate = map_candidate_to_table(candidate)
    base_candidate.strategy_name = self.STRATEGY_NAME  # ❌ Manual override
    session.add(base_candidate)
```

This was fragile and easy to miss.

## Impact

1. **Orphaned records**: `purge_candidates("orh_breakout")` wouldn't delete candidates with `strategy_name=""`
2. **Data inconsistency**: Same candidate could have different `strategy_name` values
3. **Test failures**: `test_purge_candidates_all` failed because candidates weren't being deleted
4. **Debugging difficulty**: Silent failures in purge operations

## Proposed Solutions

### Option A: Strategy Name Class Attribute (Recommended)

Store strategy name as a class attribute on candidate classes:

```python
@dataclass
class GapCandidate(Candidate):
    """Gap scanner candidate"""

    STRATEGY_NAME: str = "orh_breakout"  # Class-level constant
    gap_percent: float = field(default=_UNSET)
    conid: int | None = field(default=None)

    def __post_init__(self):
        if self.gap_percent is _UNSET:
            raise ValueError("gap_percent is required")
        if self.strategy_name == "":  # If not explicitly set
            self.strategy_name = self.STRATEGY_NAME  # Use class constant
        # ... rest of __post_init__
```

Then mappers and repositories use:

```python
# Mapper
def map_candidate_to_table(candidate: Candidate) -> CandidateTable:
    return CandidateTable(
        # ... other fields
        strategy_name=candidate.strategy_name or candidate.__class__.STRATEGY_NAME,
        # ...
    )

# Repository
def save_gap_candidate(self, candidate: GapCandidate) -> None:
    with self.db.get_session() as session:
        base_candidate = session.exec(...).first()

        if not base_candidate:
            base_candidate = map_candidate_to_table(candidate)
            # No manual override needed - mapper handles it
            session.add(base_candidate)
```

**Pros:**
- Self-documenting (strategy name with candidate type)
- Auto-propagation in `__post_init__`
- Repository code cleaner
- No manual overrides needed

**Cons:**
- Requires changes to domain models
- Tight coupling between candidates and strategies

### Option B: Strategy Enum

Define strategy names as enum:

```python
from enum import Enum

class Strategy(str, Enum):
    """Strategy name constants"""
    ORH_BREAKOUT = "orh_breakout"
    GAP_ONLY = "gap_only"
    NEWS_ONLY = "news_only"

@dataclass
class Candidate:
    strategy_name: Strategy = field(default=Strategy.ORH_BREAKOUT)
```

Then repository uses:

```python
def purge_candidates(self, strategy_name: Strategy | None = None) -> int:
    if strategy_name:
        conditions.append(col(CandidateTable.strategy_name) == strategy_name.value)
```

**Pros:**
- Type-safe strategy names
- Prevents typos
- IDE autocomplete
- Can add metadata to strategies

**Cons:**
- Requires enum definition
- Need `.value` when accessing strings
- Changes type signature of `strategy_name`

### Option C: Mixin Classes

Create strategy-specific mixins:

```python
class ORHCandidateMixin:
    """Mixin for ORH breakout candidates"""
    STRATEGY_NAME = "orh_breakout"

@dataclass
class GapCandidate(ORHCandidateMixin, Candidate):
    """Gap scanner candidate"""
    gap_percent: float = field(default=_UNSET)

    def __post_init__(self):
        if self.strategy_name == "":
            self.strategy_name = self.STRATEGY_NAME
        # ... rest of logic
```

**Pros:**
- Mixin can add strategy-specific methods
- Reusable across strategies
    - Clean separation

**Cons:**
- Multiple inheritance complexity
- Method resolution order (MRO) considerations
- Overkill for just strategy name

### Option D: Repository-Level Strategy Injection

Pass strategy name to repository:

```python
class ORHCandidateRepository:
    STRATEGY_NAME = "orh_breakout"  # Repository owns the strategy name

    def save_candidate(self, candidate: Candidate) -> None:
        # Override strategy name here
        if candidate.strategy_name == "":
            candidate.strategy_name = self.STRATEGY_NAME

        with self.db.get_session() as session:
            base_candidate = map_candidate_to_table(candidate)
            session.add(base_candidate)
```

**Pros:**
- Repository owns strategy assignment
- Domain models stay pure
- Central place for strategy logic

**Cons:**
- Repository modifies domain objects
- Violates immutability principle
- Harder to test without repository

## Recommendation

**Option A (Strategy Name Class Attribute)** - it keeps strategy information with the candidate type (cohesion) and makes the relationship explicit.

### Implementation Steps

1. [ ] Add `STRATEGY_NAME` class attribute to `GapCandidate`
2. [ ] Add `STRATEGY_NAME` class attribute to `NewsCandidate`
3. [ ] Update `Candidate.__post_init__()` to use class attribute as default
4. [ ] Update `map_candidate_to_table()` to handle empty strategy_name
5. [ ] Remove manual `strategy_name` override from `ORHCandidateRepository`
6. [ ] Update `purge_candidates()` to use enum or const
7. [ ] Add unit tests for strategy name propagation
8. [ ] Run full test suite

## Test Coverage Needed

```python
def test_gap_candidate_has_strategy_name():
    candidate = GapCandidate(ticker=Ticker("BHP"), gap_percent=5.0)
    assert candidate.strategy_name == "orh_breakout"

def test_news_candidate_has_strategy_name():
    candidate = NewsCandidate(ticker=Ticker("CBA"), headline="Results")
    assert candidate.strategy_name == "orh_breakout"

def test_purge_respects_strategy_name():
    # Create candidates with strategy name
    # Purge by strategy name
    # Verify only matching candidates deleted
```

## Files to Change

- `src/skim/domain/models/candidate.py` - Add `STRATEGY_NAME` attributes
- `src/skim/infrastructure/database/trading/mappers.py` - Update mapper logic
- `src/skim/trading/data/repositories/orh_repository.py` - Remove manual overrides
- `src/skim/trading/data/database.py` - Update `purge_candidates()` if needed
- `tests/trading/unit/test_orh_repository.py` - Add strategy name tests
