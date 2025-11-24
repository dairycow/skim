# Architecture

Skim is a minimal, cron-driven ASX trading bot using an Opening Range High (ORH) breakout strategy.

## Core Modules

- `src/skim/scanner.py` – Find candidates with gaps + announcements
- `src/skim/range_tracker.py` – Sample and store ORH/ORL values
- `src/skim/trader.py` – Execute breakout entries and stops
- `src/skim/monitor.py` – Check positions, trigger stops
- `src/skim/core/bot.py` – Thin orchestrator, dispatches to modules
- `src/skim/data/database.py` – SQLite persistence
- `src/skim/brokers/ibkr_client.py` – IBKR OAuth integration

Supporting modules:
- `src/skim/core/config.py` – Environment configuration
- `src/skim/notifications/discord.py` – Alert webhooks

## Trading Workflow

### 1. Morning Scan (10:00 AM)
```
scan() → Find gaps + announcements → Save candidates (ORH/ORL = NULL)
```

### 2. Range Tracking (10:10 AM)
```
track_ranges() → Wait until 10:10 → Sample market data → Set ORH/ORL
```

### 3. Execution (10:15 AM, then every 5 min)
```
trade() → Get watching candidates → Check if price > ORH → Buy with stop = ORL
```

### 4. Monitoring (every 5 min during market)
```
manage() → Get open positions → Check if price < stop_loss → Sell
```

## Data Model

Two tables only:

**candidates**
```sql
ticker TEXT PRIMARY KEY
or_high REAL             -- Opening range high (NULL until tracked)
or_low REAL              -- Opening range low (NULL until tracked)
scan_date TEXT           -- When added
status TEXT              -- 'watching' | 'entered' | 'closed'
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

## Cron Schedule

```cron
# 10:00 AM - Market open, scan for candidates
00 10 * * 1-5  bot scan

# 10:10 AM - Track opening ranges
10 10 * * 1-5  bot track_ranges

# 10:15 AM - 4:00 PM, every 5 min - Execute breakouts
*/5 10-16 * * 1-5  bot trade

# 10:15 AM - 4:00 PM, every 5 min - Monitor and exit stops
*/5 10-16 * * 1-5  bot manage
```

## Technology

- Python 3.13
- SQLite
- OAuth 1.0a (IBKR)
- Docker
- Cron scheduling

## Why This Design

- **Reduce complexity**: Single status flow per table
- **Clear responsibilities**: Scanner finds, RangeTracker sets levels, Trader executes, Monitor exits
- **Phase separation**: Each workflow step is independent and testable
- **Easy to extend**: Add rules without rewriting architecture
