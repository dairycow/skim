# Architecture

Skim is a minimal, cron-driven ASX trading bot using an Opening Range High (ORH) breakout strategy.

## Core Modules

- `src/skim/scanners/gap_scanner.py` – Find gap-only candidates
- `src/skim/scanners/news_scanner.py` – Find news-only candidates
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

### 1. Gap Scan (10:00 AM)
```
scan_gaps() → Find gap-only candidates → Save to database
```

### 2. News Scan (10:00 AM)
```
scan_news() → Find news-only candidates → Merge with gap candidates
```
> News scan merges with existing gap candidates by updating the same record with headline fields.

### 3. Range Tracking (10:10 AM, UTC clock)
```
track_ranges() → Get gap+news candidates → Sample market data → Set ORH/ORL
```
> Range tracking uses a UTC clock with a default market open of **23:00 UTC** (10:00 AM AEDT) so cron and in-code timing stay aligned. Only tracks candidates with both gap and news.

### 4. Execution (10:15 AM, then every 5 min)
```
trade() → Get tradeable candidates (gap+news+ORH/ORL) → Check if price > ORH → Buy with stop = ORL
```

### 5. Monitoring (every 5 min during market)
```
manage() → Get open positions → Check if price < stop_loss → Sell
```

## Data Model

Three tables:

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

## Cron Schedule (UTC; 10:00 AM AEDT = 23:00 UTC prior day)

Canonical schedule lives in `crontab` and is copied to `/etc/cron.d/skim-trading-bot` during deploys:

```cron
# 22:55 UTC (09:55 AEDT) - Purge previous candidates
55 22 * * 0-4 bot purge_candidates

# 23:00 UTC (10:00 AEDT) - Gap scan
1 23 * * 0-4 bot scan_gaps

# 23:00 UTC (10:00 AEDT) - News scan (merges with gap candidates)
1 23 * * 0-4 bot scan_news

# 23:10 UTC (10:10 AEDT) - Track opening ranges
10 23 * * 0-4 bot track_ranges

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Execute breakouts
*/5 23-6 * * 0-4 bot trade

# 23:15-06:00 UTC, every 5 min (10:15 AM - 5:00 PM AEDT) - Monitor and exit stops
*/5 23-6 * * 0-4 bot manage
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
