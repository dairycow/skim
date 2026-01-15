# Architecture Refactor Quick Reference

## Current State (After Phases 1-6)

✅ **Completed**:
- Domain models: MarketData, OrderResult, ORHCandidateData
- Infrastructure protocols use domain types
- StrategyContext decoupled from trading layer
- Broker implementations use domain models
- 216 tests passing

⚠️ **Remaining**:
- 9 files still use `trading.data.models`
- Parallel persistence models in `trading/data/models.py`
- Parallel repository protocol in `trading/data/repositories/base.py`

---

## Files Still Using trading.data.models

| File | Usage | Priority |
|------|-------|----------|
| `trading/scanners/gap_scanner.py` | Returns GapStockInPlay | High |
| `trading/strategies/orh_breakout/trader.py` | Position, TradeableCandidate | High |
| `trading/monitor.py` | Position | Medium |
| `application/events/handlers.py` | GapStockInPlay, NewsStockInPlay | Medium |
| `trading/brokers/__init__.py` | MarketData, OrderResult | Low |
| `trading/data/database.py` | Candidate, Position (persistence) | N/A |
| `trading/data/repositories/orh_repository.py` | Multiple types | N/A |

---

## Three Approaches for Persistence Layer

### A. Adapters (Recommended)
```
Domain Models ←→ Adapters ←→ SQLModel Tables
```
- Pros: Stable schema, gradual migration
- Cons: Double mapping layer

### B. Direct SQLModel Integration
```
Domain Models (SQLModel) → Database
```
- Pros: Single model, less boilerplate
- Cons: Breaking change, data migration

### C. Separate Persistence Layer
```
Domain Models ←→ Repositories ←→ Persistence Models
```
- Pros: Clean architecture, flexibility
- Cons: More files, mapping complexity

---

## Decision Point

**For aggressive refactor**: Choose Option C
- Follows hexagonal architecture best practices
- Infrastructure owns persistence concerns
- Domain stays pure

**For minimal changes**: Choose Option A
- Least disruptive
- Quick to implement
- Future migration path remains open

---

## Next Steps

1. Review detailed plan: `hexagonal-architecture-refactor.md`
2. Choose persistence layer approach
3. Begin Phase 8 (Repository Implementation)
