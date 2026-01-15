# Fix Import Dependency Cascade

## Problem

Deleting `trading/data/models.py` revealed widespread import dependencies. Breaking the import chain caused 15+ import errors across modules:

```
trading/brokers/__init__.py
  → infrastructure/brokers/protocols.py
    → trading/data/__init__.py
      → domain/models/__init__.py
```

## Root Causes

1. **Circular dependency risk**: Trading layer re-exports domain models, making it unclear where models "live"
2. **Implicit coupling**: Infrastructure layer imported from trading layer
3. **Monolithic exports**: Trading `__init__.py` exported everything from both domain and trading layers

## Current Structure (Problematic)

```
src/skim/
├── trading/
│   ├── brokers/
│   │   └── __init__.py          # Exports domain MarketData, OrderResult
│   └── data/
│       └── __init__.py           # Exports domain + trading models
└── infrastructure/
    └── brokers/
        ├── __init__.py           # Imports from trading/brokers
        └── protocols.py          # Imports from trading/data
```

## Proposed Solutions

### Option A: Direct Domain Exports (Recommended)

Infrastructure imports directly from domain, not through trading layer:

```python
# infrastructure/brokers/protocols.py
from skim.domain.models import MarketData, OrderResult, Position

# trading/brokers/__init__.py
from skim.domain.models import MarketData, OrderResult
from skim.infrastructure.brokers.ibkr import IBKRClient
from skim.infrastructure.brokers.protocols import (
    BrokerConnectionManager,
    GapScannerService,
    MarketDataProvider,
    OrderManager,
)

# trading/data/__init__.py
from skim.domain.models import Candidate, GapCandidate, NewsCandidate, MarketData, OrderResult, Position
from skim.infrastructure.database.historical import DailyPrice, HistoricalDataRepository, HistoricalPerformance
from .database import Database
from .repositories.orh_repository import ORHCandidateRepository
```

**Pros:**
- Eliminates indirect imports
- Clear ownership (domain vs trading vs infrastructure)
- Breaks dependency chain

**Cons:**
- Need to update multiple files
- Risk of breaking existing code that imports from trading layer

### Option B: Adapter Pattern for Trading Layer

Create trading-specific adapters that wrap domain models:

```python
# trading/data/adapters.py
from skim.domain.models import MarketData as DomainMarketData

class MarketData:
    """Trading layer adapter for domain MarketData"""
    def __init__(self, domain_data: DomainMarketData):
        self._domain = domain_data

    @property
    def ticker(self) -> str:
        return self._domain.ticker.symbol

    # ... delegate other properties
```

**Pros:**
- Clear separation of concerns
- Can add trading-specific behavior

**Cons:**
- More boilerplate
- Wrapping overhead
- Confusing to have two `MarketData` classes

### Option C: Consolidate Imports in Core Module

Create a single entry point for trading models:

```python
# trading/imports.py
"""Centralized trading imports - use this for domain + trading models"""
from skim.domain.models import *
from skim.domain.repositories import *
from skim.infrastructure.brokers.protocols import *
from skim.infrastructure.database.historical import *
from skim.trading.data.database import Database
from skim.trading.data.repositories.orh_repository import ORHCandidateRepository
```

**Pros:**
- Single import statement
- Easy to find all dependencies

**Cons:**
- Wildcard imports (violates PEP8)
- Hides actual dependencies
- Makes circular deps harder to spot

## Recommendation

**Option A (Direct Domain Exports)** - it's the cleanest solution and aligns with hexagonal architecture principles.

### Implementation Steps

1. [ ] Audit all imports from `trading.data` in codebase
2. [ ] Update `infrastructure/brokers/protocols.py` to import from `domain.models`
3. [ ] Update `trading/brokers/__init__.py` to import from `domain.models`
4. [ ] Update `trading/data/__init__.py` to import from `domain.models`
5. [ ] Run tests to find any remaining import issues
6. [ ] Fix any circular dependencies revealed
7. [ ] Document import rules in `AGENTS.md`

## Files to Audit

Run this to find all imports:

```bash
grep -r "from skim.trading.data" src/ tests/
grep -r "from skim.trading.brokers" src/ tests/
grep -r "from skim.infrastructure.brokers" src/ tests/
```

Expected files to update:
- `src/skim/infrastructure/brokers/protocols.py`
- `src/skim/trading/brokers/__init__.py`
- `src/skim/trading/data/__init__.py`
- Any test files with indirect imports
