# Agent Task: Domain Builder
## Phase: 2
## Priority: HIGH

### Objective
Build the domain layer with pure Python models, event-driven strategy interface, and repository protocols.

### Reference Files
- `src/skim/trading/data/models.py` (existing models)
- `src/skim/trading/strategies/base.py` (existing interface)
- `src/skim/trading/data/repositories/base.py` (existing protocols)

### New Domain Layer Structure
```
src/skim/domain/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── ticker.py      # Ticker value object
│   ├── price.py       # Price value object
│   ├── position.py    # Position domain model
│   ├── candidate.py   # Candidate domain model
│   ├── signal.py      # Signal domain model
│   └── event.py       # Event domain model
├── strategies/
│   ├── __init__.py
│   ├── base.py        # Event-driven Strategy interface
│   ├── context.py     # StrategyContext (from Phase 1.2)
│   └── registry.py    # Strategy registry (from Phase 1.2)
└── repositories/
    ├── __init__.py
    ├── base.py        # Generic repository protocol
    ├── candidate.py   # CandidateRepository protocol
    └── position.py    # PositionRepository protocol
```

### Tasks

#### 2.1 Create Unified Domain Models

##### 2.1.1 Create `domain/models/ticker.py`
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Ticker:
    """Value object for ticker symbol"""
    symbol: str
    
    def __post_init__(self):
        if not self.symbol:
            raise ValueError("Ticker symbol cannot be empty")
    
    def __str__(self) -> str:
        return self.symbol
```

##### 2.1.2 Create `domain/models/price.py`
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Price:
    """Value object for price data"""
    value: float
    timestamp: datetime
    
    @property
    def is_valid(self) -> bool:
        return self.value > 0
```

##### 2.1.3 Create `domain/models/position.py`
```python
from dataclasses import dataclass
from datetime import datetime

from .ticker import Ticker
from .price import Price

@dataclass
class Position:
    """Trading position (domain model)"""
    id: int | None = None
    ticker: Ticker
    quantity: int
    entry_price: Price
    stop_loss: Price
    entry_date: datetime
    exit_price: Price | None = None
    exit_date: datetime | None = None
    status: str = "open"
    
    @property
    def is_open(self) -> bool:
        return self.status == "open"
    
    @property
    def pnl(self) -> float | None:
        if not self.exit_price:
            return None
        return (self.exit_price.value - self.entry_price.value) * self.quantity
```

##### 2.1.4 Create `domain/models/candidate.py`
```python
from dataclasses import dataclass
from datetime import datetime

from .ticker import Ticker

@dataclass
class Candidate:
    """Trading candidate (domain model)"""
    ticker: Ticker
    scan_date: datetime
    status: str = "watching"
    strategy_name: str = ""
    created_at: datetime = datetime.now()

@dataclass
class GapCandidate(Candidate):
    """Gap scanner candidate"""
    gap_percent: float
    conid: int | None = None

@dataclass
class NewsCandidate(Candidate):
    """News scanner candidate"""
    headline: str
    announcement_type: str = "pricesens"
    announcement_timestamp: datetime | None = None
```

##### 2.1.5 Create `domain/models/signal.py`
```python
from dataclasses import dataclass

from .ticker import Ticker
from .price import Price

@dataclass
class Signal:
    """Trading signal"""
    ticker: Ticker
    action: str  # "BUY" | "SELL"
    quantity: int
    price: Price | None = None
    reason: str = ""
```

##### 2.1.6 Create `domain/models/event.py`
```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

class EventType(Enum):
    MARKET_DATA = "market_data"
    GAP_SCAN_RESULT = "gap_scan"
    NEWS_SCAN_RESULT = "news_scan"
    OPENING_RANGE_TRACKED = "or_tracked"
    STOP_HIT = "stop_hit"

@dataclass
class Event:
    """Domain event"""
    type: EventType
    data: dict | object
    timestamp: datetime = datetime.now()
```

#### 2.2 Create Event-Driven Strategy Interface

##### 2.2.1 Update `domain/strategies/base.py`
```python
from abc import ABC, abstractmethod
from typing import Protocol

from .event import Event
from .signal import Signal

class Strategy(ABC):
    """Base strategy interface - event-driven"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""
    
    @abstractmethod
    async def on_event(self, event: Event) -> list[Signal]:
        """Process event and return trading signals"""
    
    async def initialize(self) -> None:
        """Optional initialization hook"""
        pass
    
    async def shutdown(self) -> None:
        """Optional cleanup hook"""
        pass
```

#### 2.3 Create Repository Protocols

##### 2.3.1 Create `domain/repositories/base.py`
```python
from typing import Protocol, TypeVar, Generic

T = TypeVar('T')

class Repository(Protocol[T]):
    """Generic repository protocol"""
    
    def add(self, entity: T) -> None:
        """Add entity to repository"""
        ...
    
    def get(self, id: int) -> T | None:
        """Get entity by ID"""
        ...
    
    def update(self, entity: T) -> None:
        """Update entity"""
        ...
    
    def delete(self, id: int) -> None:
        """Delete entity by ID"""
        ...
```

##### 2.3.2 Create `domain/repositories/candidate.py`
```python
from typing import Protocol
from .base import Repository
from ..models import Candidate, GapCandidate, NewsCandidate

class CandidateRepository(Protocol):
    """Candidate repository protocol"""
    
    def save(self, candidate: Candidate) -> None:
        """Save or update candidate"""
        ...
    
    def get_tradeable(self) -> list[Candidate]:
        """Get candidates ready for trading"""
        ...
    
    def get_alertable(self) -> list[Candidate]:
        """Get candidates for alerting"""
        ...
    
    def purge(self) -> int:
        """Purge all candidates"""
        ...
```

##### 2.3.3 Create `domain/repositories/position.py`
```python
from typing import Protocol
from .base import Repository
from ..models import Position

class PositionRepository(Protocol):
    """Position repository protocol"""
    
    def create(self, position: Position) -> int:
        """Create position, return ID"""
        ...
    
    def get_open(self) -> list[Position]:
        """Get all open positions"""
        ...
    
    def close(self, position_id: int, exit_price: float, exit_date: str) -> None:
        """Close position"""
        ...
```

#### 2.4 Create `__init__.py` files
Export all public classes from each package.

### Acceptance Criteria
- [ ] All domain models are pure Python (no SQLModel imports)
- [ ] Value objects are frozen dataclasses
- [ ] Domain models have business logic properties
- [ ] No infrastructure dependencies in domain layer
- [ ] Strategy interface is event-driven
- [ ] Repositories are protocol-based
- [ ] All existing code can import from domain layer

### Steps to Complete
1. Create all domain model files
2. Create event-driven strategy interface
3. Create repository protocols
4. Create all `__init__.py` files
5. Verify no SQLModel imports in domain layer
6. Commit with message: `feat(domain): add unified domain models and protocols`

### Notes
- Domain models should NOT import from infrastructure layer
- Use TYPE_CHECKING for any imports needed only for type hints
- Keep models simple and focused on business logic
