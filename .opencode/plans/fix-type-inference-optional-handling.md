# Fix Type Inference and Optional Handling

## Problem

LSP errors when accessing attributes on potentially None objects in mappers, particularly with `orh_data` which can be `None` in the domain model.

## Example Error

```python
# LSP complains here:
orh_candidate.gap_percent = candidate.orh_data.gap_percent  # orh_data might be None

# Also problematic:
orh_data.or_high  # LSP says "or_high" is not a known attribute of "None"
```

## Root Causes

1. Domain model `orh_data: ORHCandidateData | None = None` allows None
2. LSP can't infer that `__post_init__` guarantees non-None after initialization
3. Mappers assume `orh_data` exists without type guards

## Current Workaround

Domain model uses `__post_init__` to set defaults:

```python
def __post_init__(self):
    if self.orh_data is None:
        self.orh_data = ORHCandidateData(...)
```

But LSP doesn't understand this pattern.

## Proposed Solutions

### Option A: Non-Optional orh_data (Recommended)

Make `orh_data` non-optional with default dataclass factory:

```python
orh_data: ORHCandidateData = field(default_factory=ORHCandidateData)
```

**Pros:**
- No type guards needed
- Cleaner domain model
- LSP understands non-optional type

**Cons:**
- All candidates have `orh_data` even if not needed
- Need to check meaningful data via flags

### Option B: Type Guards with assert_cast

Use type assertions in mappers:

```python
from typing import assert_type, cast

orh_data = cast(ORHCandidateData, candidate.orh_data)
orh_candidate.gap_percent = orh_data.gap_percent
```

**Pros:**
- Keeps optional semantics
- Explicit about assumptions

**Cons:**
- Runtime overhead (assertions)
- Still feels like a workaround

### Option C: Type Narrowing with TypeGuard

Create helper function:

```python
from typing import TypeGuard

def has_orh_data(candidate: Candidate) -> TypeGuard[Candidate]:
    return candidate.orh_data is not None
```

**Pros:**
- Type-safe narrowing
- Idiomatic Python 3.10+

**Cons:**
- Need to call before every access
- Boilerplate in mapper code

## Recommendation

**Option A (Non-Optional orh_data)** with field flags:

```python
@dataclass
class ORHCandidateData:
    gap_percent: float | None = None
    conid: int | None = None
    headline: str | None = None
    # ... other fields

    @property
    def has_gap_data(self) -> bool:
        return self.gap_percent is not None

    @property
    def has_news_data(self) -> bool:
        return self.headline is not None

@dataclass
class Candidate:
    orh_data: ORHCandidateData = field(default_factory=ORHCandidateData)
```

This eliminates `None` while preserving semantic information about which data is populated.

## Tasks

1. [ ] Update domain model `Candidate` to use non-optional `orh_data`
2. [ ] Add properties to `ORHCandidateData` for checking data availability
3. [ ] Remove `__post_init__` logic that sets defaults
4. [ ] Update mappers to remove type guards
5. [ ] Run LSP to verify no errors
6. [ ] Run tests to ensure no regressions

## Files to Change

- `src/skim/domain/models/candidate.py` - Domain models
- `src/skim/infrastructure/database/trading/mappers.py` - Remove type guards
- `src/skim/trading/data/repositories/orh_repository.py` - Simplify access patterns
