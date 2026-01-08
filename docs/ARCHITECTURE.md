# Architecture

Skim is a minimal, cron-driven ASX trading bot using a multi-strategy architecture with Strategy pattern. Current implementation includes an Opening Range High (ORH) breakout strategy.

## Strategy Pattern

The bot uses a Strategy pattern to enable clean management of multiple trading strategies:

```
TradingBot (Orchestrator)
├── Shared Services
│   ├── IBKRClient
│   ├── Database
│   ├── DiscordNotifier
│   ├── IBKRMarketData
│   ├── IBKROrders
│   └── IBKRGapScanner
└── Strategies (dict[str, Strategy])
    └── ORHBreakoutStrategy
        ├── scan() - gap + news + range tracking
        ├── trade() - breakout entry execution
        ├── manage() - position management
        └── health_check() - IBKR connection check
```

### Base Strategy Interface

All strategies must implement the `Strategy` interface from `src/skim/strategies/base.py`:

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
```

### ORH Breakout Strategy

Located in `src/skim/strategies/orh_breakout.py`, this strategy:

1. **Scans** for gap and news candidates
2. **Tracks** opening ranges (ORH/ORL) for tradeable stocks
3. **Executes** breakout entries when price > ORH
4. **Manages** positions with stop losses at ORL

Strategy-specific business logic modules:
- `GapScanner` – Find gap-only candidates
- `NewsScanner` – Find news-only candidates
- `RangeTracker` – Sample and store ORH/ORL values
- `Trader` – Execute breakout entries and stops
- `Monitor` – Check positions, trigger stops

## Core Modules

### Orchestrator
- `src/skim/core/bot.py` – Multi-strategy dispatcher, registers and delegates to strategies

### Strategies
- `src/skim/strategies/base.py` – Abstract Strategy interface
- `src/skim/strategies/orh_breakout.py` – ORH breakout implementation

### Shared Services
- `src/skim/data/database.py` – SQLite persistence
- `src/skim/brokers/ibkr_client.py` – IBKR OAuth integration
- `src/skim/core/config.py` – Environment configuration
- `src/skim/notifications/discord.py` – Alert webhooks

### ORH Strategy Modules (strategy-specific)
- `src/skim/scanners/gap_scanner.py` – Find gap-only candidates
- `src/skim/scanners/news_scanner.py` – Find news-only candidates
- `src/skim/strategies/orh_breakout/range_tracker.py` – Sample and store ORH/ORL values
- `src/skim/strategies/orh_breakout/trader.py` – Execute breakout entries and stops
- `src/skim/monitor.py` – Check positions, trigger stops

## Trading Workflow

### Strategy Phases (ORH Breakout)

The ORHBreakoutStrategy implements the following phases:

#### 1. Scan Phase (10:00 AM)
```python
strategy.scan()
├── scan_gaps() → Find gap-only candidates → Save to database
└── scan_news() → Find news-only candidates → Merge with gap candidates
```

#### 2. Range Tracking (10:05 AM, UTC clock)
```python
strategy.scan() → track_ranges()
└── Get gap+news candidates → Sample market data → Set ORH/ORL
```

> Range tracking uses a UTC clock with a default market open of **23:00 UTC** (10:00 AM AEDT) so cron and in-code timing stay aligned. Only tracks candidates with both gap and news.

#### 3. Execution (10:15 AM, then every 5 min)
```python
strategy.trade()
└── Get tradeable candidates (gap+news+ORH/ORL) → Check if price > ORH → Buy with stop = ORL
```

#### 4. Monitoring (every 5 min during market)
```python
strategy.manage()
└── Get open positions → Check if price < stop_loss → Sell
```

## Adding a New Strategy

To add a new trading strategy:

1. Create strategy class in `src/skim/strategies/my_strategy.py`
2. Extend `Strategy` base class
3. Implement required abstract methods
4. Register in `src/skim/core/bot.py:_register_strategies()`

Example:
```python
# src/skim/strategies/momentum.py
from skim.strategies.base import Strategy

class MomentumStrategy(Strategy):
    @property
    def name(self) -> str:
        return "momentum"

    async def scan(self) -> int:
        # Find momentum candidates
        return candidate_count

    async def trade(self) -> int:
        # Execute momentum trades
        return trade_count

    async def manage(self) -> int:
        # Manage momentum positions
        return managed_count
```

Register in bot.py:
```python
def _register_strategies(self) -> None:
    from skim.strategies.momentum import MomentumStrategy

    self.strategies["orh_breakout"] = ORHBreakoutStrategy(...)
    self.strategies["momentum"] = MomentumStrategy(...)
```

## Data Model

Three tables (shared across all strategies):

**candidates**
```sql
ticker TEXT PRIMARY KEY
scan_date TEXT           -- When added
status TEXT              -- 'watching' | 'entered' | 'closed'
gap_percent REAL         -- Gap percentage (from gap scan)
conid INTEGER            -- IBKR contract ID
headline TEXT            -- News headline (from news scan)
announcement_type TEXT   -- Announcement type (default 'pricesens')
announcement_timestamp TEXT -- Announcement timestamp
created_at TEXT
```

**opening_ranges**
```sql
ticker TEXT PRIMARY KEY
or_high REAL             -- Opening range high
or_low REAL              -- Opening range low
sample_date TEXT         -- When sampled
created_at TEXT
FOREIGN KEY (ticker) REFERENCES candidates(ticker)
```

**positions**
```sql
id INTEGER PRIMARY KEY
ticker TEXT
quantity INTEGER
entry_price REAL
stop_loss REAL           -- Set at entry = ORL
entry_date TEXT
exit_price REAL
exit_date TEXT
status TEXT              -- 'open' | 'closed'
```

## Status Transitions

**Candidates:**
- `watching` → candidate identified, waiting for ORH breakout
- `entered` → price broke ORH, position opened
- `closed` → position closed (exit via manage)

**Positions:**
- `open` → entry executed
- `closed` → stop hit or manual exit

## CLI Interface

```bash
# Strategy operations
python -m skim.core.bot scan              # Run strategy scan phase
python -m skim.core.bot trade             # Execute strategy trades
python -m skim.core.bot manage            # Manage strategy positions
python -m skim.core.bot status            # Strategy health check

# Utilities
python -m skim.core.bot purge_candidates   # Clear previous candidates
python -m skim.core.bot fetch_market_data <TICKER>  # Get market data
```

## Cron Schedule (UTC; 10:00 AM AEDT = 23:00 UTC)

Canonical schedule lives in `crontab`:

```cron
# 22:55 UTC (09:55 AEDT) - Purge previous candidates
55 22 * * 0-4 bot purge_candidates

# 23:00 UTC (10:00 AEDT) - Full scan (gaps + news + ranges)
1 23 * * 0-4 bot scan

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Execute breakouts
*/5 23-6 * * 0-4 bot trade

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Monitor and exit stops
*/5 23-6 * * 0-4 bot manage
```

## Technology

- Python 3.13
- SQLite
- OAuth 1.0a (IBKR)
- Strategy Pattern (design pattern)
- Async/await
- Cron scheduling

## Why This Design

- **Strategy pattern**: Clean separation between orchestrator and strategy implementations
- **Easy to extend**: Add new strategies without modifying core orchestrator
- **Reduce complexity**: Single status flow per table
- **Clear responsibilities**: Orchestrator delegates, strategies implement
- **Phase separation**: Each workflow step is independent and testable
- **Testability**: Strategy interface enables easy mocking for tests
