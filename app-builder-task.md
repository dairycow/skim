# Agent Task: Application Layer Builder
## Phase: 4
## Priority: MEDIUM

### Objective
Build application layer with event bus, trading service, and command handlers.

### Reference Files
- `src/skim/trading/core/bot.py` (TradingBot class)
- `src/skim/trading/strategies/orh_breakout/orh_breakout.py` (strategy implementation)

### New Application Layer Structure
```
src/skim/application/
├── __init__.py
├── commands/          # (From Phase 1.3)
│   ├── __init__.py
│   ├── base.py
│   ├── scan.py
│   ├── trade.py
│   ├── manage.py
│   ├── purge.py
│   └── status.py
├── services/
│   ├── __init__.py
│   ├── trading_service.py   # Main orchestrator
│   ├── monitor_service.py   # Position monitoring
│   └── command_dispatcher.py # (From Phase 1.3)
└── events/
    ├── __init__.py
    ├── event_bus.py         # Central event bus
    └── handlers.py          # Event handlers
```

### Tasks

#### 4.1 Create Event Bus

##### 4.1.1 Create `application/events/event_bus.py`
```python
import asyncio
from typing import Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class EventType(Enum):
    MARKET_DATA = "market_data"
    GAP_SCAN_RESULT = "gap_scan"
    NEWS_SCAN_RESULT = "news_scan"
    OPENING_RANGE_TRACKED = "or_tracked"
    STOP_HIT = "stop_hit"
    SIGNAL_EMITTED = "signal"

@dataclass
class Event:
    """Event for event-driven architecture"""
    type: EventType
    data: dict | object
    timestamp: datetime = datetime.now()

class EventBus:
    """Central event bus for event-driven architecture"""
    
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._handlers: list[Callable] = []
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe handler to event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
    
    def add_handler(self, handler: Callable) -> None:
        """Add global handler (e.g., strategy)"""
        self._handlers.append(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers"""
        await self._event_queue.put(event)
    
    async def start(self) -> None:
        """Start event processing loop"""
        self._running = True
        while self._running:
            event = await self._event_queue.get()
            await self._process_event(event)
    
    async def _process_event(self, event: Event) -> None:
        """Process single event"""
        # Notify global handlers (strategies)
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler failed: {e}", exc_info=True)
        
        # Notify type-specific handlers
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler failed: {e}", exc_info=True)
    
    async def stop(self) -> None:
        """Stop event processing"""
        self._running = False
```

##### 4.1.2 Create `application/events/handlers.py`
```python
from .event_bus import Event, EventType

async def handle_gap_scan_result(event: Event) -> None:
    """Handle gap scan results"""
    # Process gap candidates
    pass

async def handle_news_scan_result(event: Event) -> None:
    """Handle news scan results"""
    # Process news candidates
    pass

async def handle_stop_hit(event: Event) -> None:
    """Handle stop loss triggers"""
    # Execute stop logic
    pass

# Map handlers to event types
DEFAULT_HANDLERS = {
    EventType.GAP_SCAN_RESULT: handle_gap_scan_result,
    EventType.NEWS_SCAN_RESULT: handle_news_scan_result,
    EventType.STOP_HIT: handle_stop_hit,
}
```

#### 4.2 Create Trading Service

##### 4.2.1 Create `application/services/trading_service.py`
```python
import asyncio
from typing import Protocol

from domain.strategies import Strategy, StrategyContext
from domain.models import Event, EventType, Signal
from infrastructure.database import BaseDatabase
from infrastructure.brokers import MarketDataProvider, OrderManager

class TradingService:
    """Main trading orchestrator using event-driven architecture"""
    
    def __init__(
        self,
        strategy: Strategy,
        event_bus: "EventBus",
        db: BaseDatabase,
        market_data: MarketDataProvider,
        orders: OrderManager,
        config: dict
    ) -> None:
        self.strategy = strategy
        self.events = event_bus
        self.db = db
        self.market_data = market_data
        self.orders = orders
        self.config = config
        
        # Subscribe strategy to events
        self.events.add_handler(strategy.on_event)
    
    async def scan(self) -> int:
        """Run scan phase - publish events"""
        # This would call gap scanner and news scanner
        # Then publish GAP_SCAN_RESULT and NEWS_SCAN_RESULT events
        gap_count = await self._run_gap_scan()
        news_count = await self._run_news_scan()
        return gap_count + news_count
    
    async def trade(self) -> int:
        """Execute signals from strategy"""
        # Get signals from strategy and execute orders
        signals = await self._get_pending_signals()
        executed = 0
        for signal in signals:
            await self.orders.place_order(
                ticker=str(signal.ticker),
                action=signal.action,
                quantity=signal.quantity
            )
            executed += 1
        return executed
    
    async def manage(self) -> int:
        """Monitor positions and handle stops"""
        # Check positions, publish STOP_HIT events if needed
        pass
    
    async def _run_gap_scan(self) -> int:
        """Run gap scanner and publish events"""
        # Implementation
        pass
    
    async def _run_news_scan(self) -> int:
        """Run news scanner and publish events"""
        # Implementation
        pass
    
    async def _get_pending_signals(self) -> list[Signal]:
        """Get pending signals from strategy"""
        # Implementation
        pass
```

#### 4.3 Wire Up Application Layer

##### 4.3.1 Create `application/__init__.py`
Export all public classes.

##### 4.3.2 Integrate with CLI (from Phase 1.3)
Update `trading/cli.py` to use TradingService and EventBus.

### Acceptance Criteria
- [ ] EventBus processes events asynchronously
- [ ] TradingService orchestrates via events
- [ ] Strategies emit signals through event bus
- [ ] Clear separation between orchestration and strategy logic
- [ ] All existing workflows work with new architecture

### Steps to Complete
1. Create EventBus class
2. Create event handlers
3. Create TradingService
4. Wire up in application/__init__.py
5. Integrate with CLI from Phase 1.3
6. Test end-to-end
7. Commit with message: `feat(application): add event bus and trading service`

### Notes
- This phase builds on Phase 1.3 (CLI) and Phase 2 (domain)
- Event handlers should be minimal - strategy does the work
- Consider performance implications of async event queue
