# Architecture

Skim is a cron-driven ASX trading bot using hexagonal architecture with domain-driven design. Implements an Opening Range High (ORH) breakout strategy.

## Architecture Overview

```
src/skim/
├── domain/           # Business logic (models, strategies, protocols)
├── application/      # Use cases (commands, events, services)
├── infrastructure/   # External integrations (IBKR, database)
├── trading/          # Bot orchestrator, brokers, scanners
├── analysis/         # Research CLI
└── shared/           # Historical data service
```

### Hexagonal Ports & Adapters

```
TradingBot (Application)
    │
    ├── Domain Layer
    │   ├── Strategies (ORHBreakoutStrategy)
    │   ├── Models (Candidate, Position, Signal)
    │   └── Repositories (Protocols)
    │
    └── Infrastructure Layer (Adapters)
        ├── IBKR Broker (orders, market data, gap scanner)
        ├── SQLite Database
        └── Discord Notifications
```

## Domain Layer

### Strategy Pattern

All strategies implement the `Strategy` interface from `src/skim/domain/strategies/base.py`:

```python
class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name identifier"""

    @abstractmethod
    async def scan(self) -> int:
        """Scan for candidates"""

    @abstractmethod
    async def trade(self) -> int:
        """Execute trade entries"""

    @abstractmethod
    async def manage(self) -> int:
        """Manage open positions"""

    async def on_event(self, event: Event) -> list[Signal]:
        """Handle events and return signals"""
```

### Event Types

Strategies support these event types:
- `SCAN` - Scan for candidates
- `TRADE` - Execute entries
- `MANAGE` - Monitor positions
- `TRACK_RANGES` - Track opening ranges (ORH/ORL)
- `ALERT` - Send notifications
- `HEALTH_CHECK` - Verify IBKR connection

### Domain Models

**Candidate** (`src/skim/domain/models/candidate.py`)
```python
@dataclass
class Candidate:
    ticker: Ticker
    scan_date: datetime
    status: str = "watching"      # watching | entered | closed
    strategy_name: str = ""
```

**Position** (`src/skim/domain/models/position.py`)
```python
@dataclass
class Position:
    ticker: Ticker
    quantity: int
    entry_price: Price
    stop_loss: Price
    entry_date: datetime
    status: str = "open"          # open | closed
```

### Repository Protocols

```python
class Repository(Protocol[T]):
    def add(self, entity: T) -> None: ...
    def get(self, id: int) -> T | None: ...
    def update(self, entity: T) -> None: ...
    def delete(self, id: int) -> None: ...
```

## Application Layer

### Commands (`src/skim/application/commands/`)

Command classes for CLI and dispatch:

```python
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

### Services

- `CommandDispatcher` - Routes commands to strategies
- `TradingService` - Orchestrates trading operations

### Events

- `EventBus` - Publish/subscribe event system
- `EventHandlers` - Handle domain events

## Infrastructure Layer

### IBKR Broker (`src/skim/infrastructure/brokers/ibkr/`)

- `auth.py` - OAuth 1.0a authentication
- `connection.py` - Client socket connection
- `facade.py` - Unified broker interface
- `requests.py` - Request builders
- `exceptions.py` - Custom exceptions

### Database (`src/skim/infrastructure/database/`)

- `base.py` - SQLAlchemy/SQLite base classes

## Trading Module

### Orchestrator (`src/skim/trading/core/bot.py`)

`TradingBot` class manages:

```python
class TradingBot:
    strategies: dict[str, DomainStrategy]
    ib_client: IBKRClient
    market_data_service: IBKRMarketData
    order_service: IBKROrders
    scanner_service: IBKRGapScanner
    discord: DiscordNotifier
```

### Brokers (`src/skim/trading/brokers/`)

- `ibkr_client.py` - IBKR connection and OAuth
- `ibkr_market_data.py` - Real-time market data
- `ibkr_orders.py` - Order execution
- `ibkr_gap_scanner.py` - Gap scanning via IBKR scanner

### Scanners (`src/skim/trading/scanners/`)

- `gap_scanner.py` - Find gap-up candidates
- `news_scanner.py` - ASX announcement scanning
- `asx_announcements.py` - ASX website scraping

### Data Layer (`src/skim/trading/data/`)

- `database.py` - SQLite database operations
- `models.py` - ORM models
- `repositories/` - Database repositories
    - `base.py` - Base repository
    - `orh_repository.py` - ORH candidate repository

### Notifications (`src/skim/trading/notifications/`)

- `discord.py` - Discord webhook alerts

### ORH Breakout Strategy (`src/skim/trading/strategies/orh_breakout/`)

```
orh_breakout.py
├── scan() - gap + news scanning
├── track_ranges() - sample ORH/ORL
├── trade() - breakout entry execution
├── manage() - stop-loss monitoring
└── alert() - Discord notifications
```

Modules:
- `trader.py` - Execute breakout entries and stops
- `range_tracker.py` - Sample and store ORH/ORL values

## Analysis Module

Research CLI tools for historical analysis:

```
src/skim/analysis/
├── cli/
│   ├── cli.py - Main CLI entry point
│   └── main.py - Typer CLI app
├── gap_scanner.py - Historical gap analysis
├── momentum_scanner.py - Momentum screening
├── performance.py - Performance metrics
├── data_loader.py - Load historical data
├── data_downloader.py - Download market data
└── announcement_scraper.py - Scrape announcements
```

## Shared Module

Historical data service:

```
src/skim/shared/
├── historical/
│   ├── service.py - Historical data operations
│   ├── repository.py - Data repository
│   └── models.py - Data models
├── database.py - Shared database
├── container.py - Dependency container
└── constants.py - Shared constants
```

## Strategy Registry

Strategies are auto-registered via `@register_strategy` decorator:

```python
from skim.domain.strategies.registry import registry, register_strategy

@register_strategy("orh_breakout")
class ORHBreakoutStrategy(Strategy):
    @property
    def name(self) -> str:
        return "orh_breakout"
    # ... implement abstract methods
```

## Data Model

### candidates table

```sql
id INTEGER PRIMARY KEY
ticker TEXT
scan_date TEXT
status TEXT              -- 'watching' | 'entered' | 'closed'
gap_percent REAL
conid INTEGER
headline TEXT
announcement_type TEXT
announcement_timestamp TEXT
strategy_name TEXT
created_at TEXT
```

### positions table

```sql
id INTEGER PRIMARY KEY
ticker TEXT
quantity INTEGER
entry_price REAL
stop_loss REAL
entry_date TEXT
exit_price REAL
exit_date TEXT
status TEXT              -- 'open' | 'closed'
```

### opening_ranges table

```sql
ticker TEXT PRIMARY KEY
or_high REAL
or_low REAL
sample_date TEXT
created_at TEXT
```

## Trading Workflow (ORH Breakout)

### 1. Scan Phase (10:00 AM AEDT)

```python
strategy.scan()
├── scan_gaps() → IBKR scanner → gap candidates
└── scan_news() → ASX announcements → news candidates
```

### 2. Range Tracking (10:05 AM AEDT)

```python
strategy.track_ranges()
├── Get candidates (gap + news)
├── Sample market data at 10:05
└── Store ORH/ORL values
```

### 3. Alert Phase (10:10 AM AEDT)

```python
strategy.alert()
├── Get tradeable candidates (gap + news + ORH/ORL)
└── Send Discord notifications
```

### 4. Trade Phase (10:15 AM - 5:00 PM AEDT, every 5 min)

```python
strategy.trade()
├── Get tradeable candidates
├── Check price > ORH
└── Execute buy order with stop = ORL
```

### 5. Manage Phase (10:15 AM - 5:00 PM AEDT, every 5 min)

```python
strategy.manage()
├── Get open positions
├── Check if price < stop_loss
└── Execute sell order
```

## CLI Interface

```bash
# Bot commands
uv run python -m skim.trading.core.bot purge_candidates
uv run python -m skim.trading.core.bot scan
uv run python -m skim.trading.core.bot trade
uv run python -m skim.trading.core.bot manage
uv run python -m skim.trading.core.bot status

# Analysis commands
uv run skim-analyze top 2024 --json
uv run skim-analyze gaps 2024 --limit 10 --json
```

## Cron Schedule (UTC)

```cron
# 22:55 UTC (09:55 AEDT) - Purge previous candidates
55 22 * * 0-4 bot purge_candidates

# 23:00 UTC (10:00 AEDT) - Full scan (gaps + news)
0 23 * * 0-4 bot scan

# 23:05 UTC (10:05 AEDT) - Track opening ranges
5 23 * * 0-4 bot scan --track-ranges

# 23:10 UTC (10:10 AEDT) - Send alerts
10 23 * * 0-4 bot alert

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Trade
*/5 23-6 * * 0-4 bot trade

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Manage
*/5 23-6 * * 0-4 bot manage
```

## Technology Stack

- Python 3.13+
- SQLite
- SQLAlchemy (infrastructure)
- IBKR API (OAuth 1.0a)
- loguru (logging)
- typer (CLI)
- Cron scheduling

## Why This Design

- **Hexagonal architecture**: Clean separation between core domain and external adapters
- **Domain-driven design**: Rich domain models with business logic
- **Strategy pattern**: Clean separation between orchestrator and strategy implementations
- **Auto-registration**: Strategies discoverable via decorator, no manual registration
- **Dependency injection**: `StrategyContext` provides all required services
- **Event-driven**: Strategies support event handling for extensibility
- **Testability**: Domain models and strategies are easy to test in isolation
