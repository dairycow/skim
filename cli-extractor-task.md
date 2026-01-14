# Agent Task: CLI Extractor
## Phase: 1.3
## Priority: HIGH

### Objective
Extract CLI logic from `bot.py` into separate `trading/cli.py` module using command pattern.

### Reference Files
- `src/skim/trading/core/bot.py` (current, 301 lines - lines 217-300 contain CLI)
- `pyproject.toml` (entry points)

### New Structure
```
src/skim/application/commands/
├── __init__.py
├── base.py           # Command base dataclass
├── scan.py           # ScanCommand
├── trade.py          # TradeCommand
├── manage.py         # ManageCommand
├── purge.py          # PurgeCommand
└── status.py         # StatusCommand

src/skim/application/services/
├── __init__.py
└── command_dispatcher.py  # CommandDispatcher

src/skim/trading/
├── __init__.py
└── cli.py            # CLI entry point (NEW)
```

### Tasks

#### 1. Create `application/commands/base.py`
Define command base class and concrete commands:

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class Command:
    """Base command class"""
    name: str

@dataclass
class ScanCommand(Command):
    strategy: str | None = None

@dataclass
class TradeCommand(Command):
    strategy: str | None = None

@dataclass
class ManageCommand(Command):
    strategy: str | None = None

@dataclass
class PurgeCommand(Command):
    cutoff_date: str | None = None

@dataclass
class StatusCommand(Command):
    strategy: str | None = None
```

#### 2. Create individual command files
- `scan.py`: Implements scan logic
- `trade.py`: Implements trade logic
- `manage.py`: Implements manage logic
- `purge.py`: Implements purge logic
- `status.py`: Implements status logic

Each file should have a handler function that takes TradingService and command, returns exit code.

#### 3. Create `application/services/command_dispatcher.py`
Create `CommandDispatcher` class:

```python
class CommandDispatcher:
    def __init__(self, trading_service: TradingService) -> None:
        self.trading = trading_service
        self._handlers = {
            'scan': self._handle_scan,
            'trade': self._handle_trade,
            # ...
        }
    
    async def dispatch(self, argv: list[str]) -> int:
        """Parse and execute command"""
        method = argv[1] if len(argv) > 1 else None
        handler = self._handlers.get(method)
        # ... dispatch logic
```

Key requirement: Use dictionary dispatch (no if-elif chain).

#### 4. Refactor `trading/core/bot.py`
- Remove `main()` function
- Keep only `TradingBot` class (lines 27-216)
- Remove CLI-specific logic

#### 5. Create `trading/cli.py`
```python
def main():
    # Setup logging
    logger.add(...)
    
    # Load config
    config = Config.from_env()
    
    # Create services
    trading_service = create_trading_service(config)
    
    # Create dispatcher
    dispatcher = CommandDispatcher(trading_service)
    
    # Run command
    return asyncio.run(dispatcher.dispatch(sys.argv))
```

#### 6. Update `pyproject.toml`
Change entry point:
```toml
[project.scripts]
skim = "skim.trading.cli:main"
```

#### 7. Update Tests
- Split `tests/trading/test_bot.py` into:
  - `tests/trading/test_trading_bot.py` (TradingBot class tests)
  - `tests/trading/test_cli.py` (CLI/CommandDispatcher tests)

### Acceptance Criteria
- [ ] `bot.py` < 150 lines (only TradingBot class)
- [ ] `trading/cli.py` contains all CLI logic
- [ ] CommandDispatcher uses dictionary dispatch (no if-elif chain)
- [ ] `pyproject.toml` entry point updated
- [ ] All tests pass
- [ ] CLI behavior unchanged

### Steps to Complete
1. Read `bot.py` to identify CLI-specific logic
2. Create command base class and concrete commands
3. Create command dispatcher with dictionary dispatch
4. Create trading/cli.py entry point
5. Refactor bot.py to remove CLI logic
6. Update pyproject.toml
7. Update tests
8. Run tests to verify
9. Commit with message: `refactor(cli): extract CLI into separate module with command pattern`

### Notes
- Keep TradingBot class in bot.py for backward compatibility
- Ensure command parsing handles missing arguments gracefully
- Maintain same error messages and exit codes
