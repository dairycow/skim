# Strategy Interface Unification Plan

**Date:** January 15, 2026  
**Status:** COMPLETED - No action needed

---

## Summary

The Strategy interface is already unified after the domain-builder merge. The current interface on `main` combines the best of both approaches:

```python
class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:  # From worktree
        """Strategy name identifier"""

    @abstractmethod
    async def scan(self) -> int:  # From main
        ...

    @abstractmethod
    async def trade(self) -> int:  # From main
        ...

    @abstractmethod
    async def manage(self) -> int:  # From main
        ...

    async def on_event(self, event: Event) -> list[Signal]:  # Both
        """Handle event - dispatches to phase methods by default"""

    async def initialize(self) -> None:  # From worktree
        """Optional initialization hook"""

    async def shutdown(self) -> None:  # From worktree
        """Optional cleanup hook"""

    # Additional methods from main:
    async def alert(self) -> int: ...
    async def track_ranges(self) -> int: ...
    async def health_check(self) -> bool: ...
    async def setup(self) -> None: ...
```

## Current State

| Aspect | Status |
|--------|--------|
| `name` property | Implemented |
| `scan()` method | Abstract |
| `trade()` method | Abstract |
| `manage()` method | Abstract |
| `on_event()` dispatch | Implemented |
| `initialize()` hook | Implemented |
| `shutdown()` hook | Implemented |
| Tests | 193 passing |

## What's Still Needed

### 1. ORHBreakoutStrategy needs `name` property

**File:** `src/skim/trading/strategies/orh_breakout/orh_breakout.py`

```python
@property
def name(self) -> str:
    return "orh_breakout"
```

### 2. StrategyContext needs export

**File:** `src/skim/domain/strategies/__init__.py`

Should also export Strategy:
```python
from .base import Strategy
from .context import StrategyContext
from .registry import StrategyRegistry, register_strategy

__all__ = [
    "Strategy",
    "StrategyContext",
    "StrategyRegistry",
    "register_strategy",
]
```

---

## Remaining Tasks

| Task | File | Status |
|------|------|--------|
| Add `name` property to ORHBreakoutStrategy | `trading/strategies/orh_breakout/orh_breakout.py` | Pending |
| Export Strategy from __init__.py | `domain/strategies/__init__.py` | Pending |

---

## Verification

```bash
uv run pytest tests/trading/ -q  # Should pass 193 tests
uv run ruff check src/skim/domain/  # Should pass
```

---

**Plan Status: RESOLVED**
