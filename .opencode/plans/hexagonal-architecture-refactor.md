# Hexagonal Architecture Refactor - Remaining Work

## Overview

The initial refactoring phases completed the core architectural alignment:
- Created domain models (MarketData, OrderResult, ORHCandidateData)
- Updated infrastructure protocols to use domain types
- Decoupled StrategyContext from trading layer
- Fixed broker implementations to use domain models

**Status**: Core domain → infrastructure boundary is now clean. No circular dependencies.

**Remaining Work**: Migrate trading layer files from `trading.data.models` to `domain.models`, then remove parallel implementations.

---

## Phase 7: Database Schema Migration

### Problem
`trading.data.models` contains SQLModel database tables that parallel domain models. The repository layer maps between these two worlds.

### Solution Options

#### Option A: Gradual Migration (Recommended)
Create adapters that map domain models to SQLModel persistence. Keeps database schema stable.

#### Option B: Direct SQLModel Integration
Make domain models inherit SQLModel table. Breaking change, requires data migration.

#### Option C: Separate Persistence Layer
Create persistence models in `infrastructure/database/trading/` that map to domain models in repositories.

**Recommended: Option C** - Follows hexagonal architecture principles (infrastructure handles persistence details).

---

## Phase 8: Repository Implementation

### Current State
- `orh_repository.py` implements a generic protocol but uses `trading.data.models` types
- Returns `GapStockInPlay`, `NewsStockInPlay`, `TradeableCandidate` instead of domain types

### Required Changes

#### Step 8.1: Create Persistence Models
Create `infrastructure/database/trading/models.py`:
```python
# Persistence models (SQLModel tables)
class CandidateTable(SQLModel, table=True):
    __tablename__ = "candidates"
    ticker: str = Field(primary_key=True)
    scan_date: str
    status: str
    strategy_name: str
    created_at: str

class ORHCandidateTable(SQLModel, table=True):
    __tablename__ = "orh_candidates"
    ticker: str = Field(primary_key=True, foreign_key="candidates.ticker")
    gap_percent: float | None
    conid: int | None
    headline: str | None
    announcement_type: str
    announcement_timestamp: str | None
    or_high: float | None
    or_low: float | None
    sample_date: str | None

class PositionTable(SQLModel, table=True):
    __tablename__ = "positions"
    id: int | None = Field(default=None, primary_key=True)
    ticker: str
    quantity: int
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str
    exit_price: float | None
    exit_date: str | None
    created_at: str
```

#### Step 8.2: Update Database Class
Modify `trading/data/database.py`:
- Import persistence models from `infrastructure/database/trading/models.py`
- Keep method signatures, but use persistence models internally
- Return domain types where appropriate

#### Step 8.3: Create Mappers
Create `infrastructure/database/trading/mappers.py`:
```python
def map_table_to_candidate(table: CandidateTable) -> Candidate:
    """Map database table to domain Candidate"""
    return Candidate(
        ticker=Ticker(table.ticker),
        scan_date=datetime.fromisoformat(table.scan_date),
        status=table.status,
        strategy_name=table.strategy_name,
        created_at=datetime.fromisoformat(table.created_at),
    )

def map_candidate_to_table(candidate: Candidate) -> CandidateTable:
    """Map domain Candidate to database table"""
    return CandidateTable(
        ticker=candidate.ticker.symbol,
        scan_date=candidate.scan_date.isoformat(),
        status=candidate.status,
        strategy_name=candidate.strategy_name,
        created_at=candidate.created_at.isoformat(),
    )
```

#### Step 8.4: Update ORHCandidateRepository
Modify `trading/data/repositories/orh_repository.py`:
- Use persistence models instead of `trading.data.models`
- Use mappers to convert between domain and persistence
- Implement `CandidateRepository` protocol fully:
  - Add `save(candidate: Candidate)` method
  - Update return types to `list[Candidate]`
  - Update `get_tradeable()` to return `list[Candidate]` with `orh_data` populated

---

## Phase 9: Strategy Layer Migration

### Files to Update

#### 9.1 `trading/scanners/gap_scanner.py`
- Change import: `from skim.domain.models import GapCandidate`
- Return `GapCandidate` instead of `GapStockInPlay`
- Update type hints and return statements

#### 9.2 `trading/strategies/orh_breakout/trader.py`
- Change import: `from skim.domain.models import Position`
- Use domain `Position` with `Price` objects
- Update methods that work with positions

#### 9.3 `trading/monitor.py`
- Change import: `from skim.domain.models import Position`
- Update to work with domain Position type

#### 9.4 `application/events/handlers.py`
- Change imports to use `GapCandidate`, `NewsCandidate` from domain
- Update event handling to work with domain types

---

## Phase 10: Cleanup

### 10.1 Delete Parallel Implementations
Remove files after all references migrated:
- `trading/data/models.py` - All models moved to domain/infrastructure
- `trading/data/repositories/base.py` - Protocol replaced by domain protocol

### 10.2 Update Trading Brokers __init__.py
Change `trading/brokers/__init__.py`:
```python
# Before (WRONG)
from skim.trading.data.models import MarketData, OrderResult

# After (CORRECT)
from skim.domain.models import MarketData, OrderResult
```

### 10.3 Validate Architecture
Run architecture validation:
```bash
# Check domain doesn't import from trading
grep -r "from skim.trading" src/skim/domain/

# Check infrastructure doesn't import from trading.data.models
grep -r "from skim.trading.data.models" src/skim/infrastructure/

# Both should return no results
```

---

## Phase 11: Database Migration (If Using Option B)

### Migration Strategy
If choosing Option B (SQLModel integration with domain models):

1. Add SQLModel to domain models:
```python
from sqlmodel import Field, SQLModel

@dataclass
class Candidate(SQLModel, table=True):
    __tablename__ = "candidates"
    ticker: str = Field(primary_key=True)
    scan_date: str
    status: str
    strategy_name: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
```

2. Run data migration:
```python
# migration script
import sqlite3

conn = sqlite3.connect('skim.db')
cursor = conn.cursor()

# Create new schema
SQLModel.metadata.create_all(engine)

# Migrate data
cursor.execute("INSERT INTO candidates SELECT * FROM old_candidates")
cursor.execute("INSERT INTO orh_candidates SELECT * FROM old_orh_candidates")

conn.commit()
```

3. Drop old tables after validation

---

## Testing Strategy

### Unit Tests
- `tests/domain/test_models.py` - Already passing ✓
- `tests/trading/unit/test_repositories.py` - Update to test with domain types
- `tests/trading/unit/test_scanners.py` - Update scanner return types

### Integration Tests
- `tests/trading/integration/` - Verify database operations work with new models

### Manual Testing
- Run bot commands to verify functionality:
  ```bash
  uv run python -m skim.trading.core.bot scan
  uv run python -m skim.trading.core.bot trade
  uv run python -m skim.trading.core.bot status
  ```

---

## Risk Assessment

### High Risk Items
1. **Database schema changes** - Data loss risk, requires backup
2. **Position tracking** - Production data integrity
3. **Live trading** - Ensure no breaks in trading logic

### Mitigation Strategies
1. Test in development environment first
2. Create database backup before schema changes
3. Deploy during market close (no active trades)
4. Have rollback plan ready

---

## Execution Order

1. **Phase 8** (Repository Implementation) - No user-facing changes
2. **Phase 9** (Strategy Layer) - Internal code changes
3. **Phase 10** (Cleanup) - Remove parallel code
4. **Testing** - Comprehensive test run
5. **Validation** - Architecture checks

**Estimated Time**: 2-3 hours
**Test Time**: 1 hour
**Total**: 3-4 hours

---

## Success Criteria

- ✅ No imports from `trading.data.models` in domain or infrastructure layers
- ✅ All repositories use domain types in public APIs
- ✅ All tests pass (domain + trading + integration)
- ✅ `trading/data/models.py` and `trading/data/repositories/base.py` deleted
- ✅ Bot commands work end-to-end
- ✅ No circular dependencies in architecture

---

## Post-Refactor Benefits

1. **Clear Separation**: Domain logic independent of infrastructure
2. **Testability**: Can test domain without database
3. **Swapability**: Easy to change brokers, databases
4. **Maintainability**: Single source of truth for models
5. **Extensibility**: Add new strategies without touching core
