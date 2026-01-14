# Agent Task: Migration & Cleanup
## Phase: 6
## Priority: MEDIUM

### Objective
Migrate ORH strategy to new architecture, update all tests, and clean up deprecated code.

### Reference Files
- All files modified in Phases 1-5
- `tests/trading/` - existing tests

### Tasks

#### 6.1 Migrate ORH Strategy to Event-Driven

##### 6.1.1 Update `ORHBreakoutStrategy`
Refactor to use event-driven interface:

```python
from domain.strategies import Strategy, Event, EventType, Signal
from domain.models import Ticker, Price
from application.events import EventBus

class ORHBreakoutStrategy(Strategy):
    """Opening Range High breakout strategy - event-driven"""
    
    def __init__(self, context: StrategyContext) -> None:
        """Initialize with context"""
        self.ctx = context
        # Initialize strategy-specific components
    
    @property
    def name(self) -> str:
        return "orh_breakout"
    
    async def on_event(self, event: Event) -> list[Signal]:
        """Process events and return trading signals"""
        if event.type == EventType.GAP_SCAN_RESULT:
            return self._process_gap_scan(event.data)
        elif event.type == EventType.NEWS_SCAN_RESULT:
            return self._process_news_scan(event.data)
        elif event.type == EventType.MARKET_DATA:
            return self._process_market_data(event.data)
        return []
    
    def _process_gap_scan(self, data: dict) -> list[Signal]:
        """Process gap scan results, return signals"""
        # Implementation
        pass
    
    def _process_news_scan(self, data: dict) -> list[Signal]:
        """Process news scan results, return signals"""
        # Implementation
        pass
    
    def _process_market_data(self, data: dict) -> list[Signal]:
        """Process market data, return signals"""
        # Implementation
        pass
```

##### 6.1.2 Register Strategy
```python
from domain.strategies import register_strategy

@register_strategy("orh_breakout")
class ORHBreakoutStrategy(Strategy):
    # ... implementation
```

#### 6.2 Update All Tests

##### 6.2.1 Unit Tests
- Mock new abstractions (StrategyContext, EventBus, etc.)
- Test each component in isolation
- Update `tests/trading/test_ibkr_client.py` for new structure

##### 6.2.2 Integration Tests
- Use DI container for test setup
- Test full workflows
- Verify event-driven flow works

##### 6.2.3 New Test Files
- `tests/domain/test_models.py` - Test domain models
- `tests/application/test_event_bus.py` - Test event bus
- `tests/application/test_trading_service.py` - Test trading service
- `tests/shared/test_container.py` - Test DI container

##### 6.2.4 Test Coverage Target
- Achieve >85% coverage on trading/shared modules
- No test dependencies on implementation details

#### 6.3 Remove Deprecated Code

##### 6.3.1 Remove Duplicate Code
- Old database implementations
- Duplicate market data models
- Duplicate purge logic
- Old strategy interface (if unused)

##### 6.3.2 Update Imports
- All code uses new abstractions
- Remove unused imports
- Clean up import statements

##### 6.3.3 Clean Up File Structure
- Remove empty `__pycache__` directories
- Remove deprecated files
- Ensure file structure matches plan

#### 6.4 Update Documentation

##### 6.4.1 Update AGENTS.md
- Update commands to use new CLI
- Add new commands if any
- Update architecture references

##### 6.4.2 Update README
- Add architecture overview
- Add new development patterns
- Update quick start guide

##### 6.4.3 Add Architecture Documentation
- Create `docs/architecture.md`
- Document hexagonal architecture
- Document event-driven flow
- Document DI container usage

### Acceptance Criteria
- [ ] ORH strategy is fully event-driven
- [ ] No direct service calls from strategy
- [ ] Test coverage >85% (trading/shared)
- [ ] All tests pass
- [ ] No code duplication
- [ ] All imports resolve to correct locations
- [ ] Documentation updated

### Steps to Complete
1. Refactor ORHBreakoutStrategy to event-driven
2. Register strategy in registry
3. Update all unit tests
4. Create new integration tests
5. Remove deprecated code
6. Update all imports
7. Update documentation
8. Run full test suite
9. Commit with message: `feat(migration): migrate to event-driven architecture`

### Notes
- This is the final phase that brings everything together
- Thorough testing is critical before merge
- Consider feature flags for gradual rollout
- Document breaking changes for users
