# Agent Task: Strategy Constructor Simplifier
## Phase: 1.2
## Priority: HIGH

### Objective
Refactor `ORHBreakoutStrategy` to take a single `StrategyContext` parameter instead of 9 individual dependencies.

### Reference Files
- `src/skim/trading/strategies/orh_breakout/orh_breakout.py` (current, 370 lines)
- `src/skim/trading/strategies/base.py` (Strategy interface)
- `src/skim/trading/core/bot.py` (strategy instantiation)

### New Structure
```
src/skim/domain/strategies/
├── __init__.py
├── base.py          # Updated Strategy interface (event-driven)
├── context.py       # NEW: StrategyContext dataclass
└── registry.py      # NEW: Strategy registry
```

### Tasks

#### 1. Create `domain/strategies/context.py`
Define `StrategyContext` dataclass with all dependencies:

```python
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skim.trading.brokers.protocols import MarketDataProvider, OrderManager, GapScannerService
    from skim.trading.repositories import CandidateRepository
    from skim.trading.notifications import NotificationService
    from skim.trading.core.config import StrategyConfig
    from skim.shared.historical import HistoricalDataService

@dataclass
class StrategyContext:
    """Context object providing all services a strategy needs"""
    
    market_data: MarketDataProvider
    order_service: OrderManager
    scanner_service: GapScannerService
    repository: CandidateRepository
    notifier: NotificationService
    config: StrategyConfig
    historical_service: HistoricalDataService | None = None
```

#### 2. Create `domain/strategies/registry.py`
Create `StrategyRegistry` class with:
- `register(name, factory)` method
- `get(name, context)` method
- `list_available()` method
- `@register_strategy(name)` decorator

#### 3. Update `domain/strategies/base.py`
Update Strategy interface for event-driven approach:
- Define `EventType` enum
- Define `Event` dataclass
- Define `Signal` dataclass
- Update `Strategy` ABC with:
  - `name` property
  - `on_event(event: Event) -> list[Signal]` method

#### 4. Refactor `ORHBreakoutStrategy`
- Change constructor to `__init__(self, context: StrategyContext)`
- Update internal references: `self.ctx.market_data`, etc.
- Keep existing business logic

#### 5. Update `trading/core/bot.py`
- Create `StrategyContext` when instantiating strategy
- Pass context instead of individual dependencies

#### 6. Update Tests
- Mock `StrategyContext` instead of 9 individual parameters
- Update strategy instantiation tests

### Acceptance Criteria
- [ ] Strategy constructor takes single `StrategyContext` parameter
- [ ] All dependencies accessible via context
- [ ] No functionality lost
- [ ] All tests pass
- [ ] `domain/strategies/` package created

### Steps to Complete
1. Read `orh_breakout.py` to understand all dependencies used
2. Create `context.py` with StrategyContext dataclass
3. Create `registry.py` with StrategyRegistry
4. Update `base.py` for event-driven interface
5. Refactor `ORHBreakoutStrategy.__init__()`
6. Update `bot.py` strategy instantiation
7. Update tests
8. Run tests to verify
9. Commit with message: `refactor(strategy): simplify constructor with StrategyContext`

### Notes
- This is a breaking change to the strategy interface
- Consider deprecation path for old interface
- The context object makes testing easier (just mock one object)
