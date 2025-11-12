# Architecture

System design, components, and trading workflow for the Skim trading bot.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Skim Trading Bot                         │
├─────────────────────────────────────────────────────────────┤
│  Cron Scheduler (Container Startup)                         │
│  ├── SCAN (00:00 UTC)     ──→ Market Scanning               │
│  ├── TRACK (00:10 UTC)    ──→ OR Tracking                   │
│  ├── EXECUTE (00:12 UTC)  ──→ Order Execution               │
│  ├── MANAGE (*/5 min)     ──→ Position Management           │
│  └── STATUS (05:30 UTC)   ──→ Daily Reporting               │
├─────────────────────────────────────────────────────────────┤
│  Core Components                                            │
│  ├── Market Scanners     ──→ IBKR Gap Scanner               │
│  ├── Trading Strategy    ──→ ORH Breakout Detection         │
│  ├── Position Manager    ──→ Risk & Exit Management         │
│  └── IBKR Interface      ──→ OAuth 1.0a API Client          │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── SQLite Database     ──→ Candidates, Positions, Trades  │
│  └── Log Files           ──→ Execution Logs                 │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### src/skim/core/
- **bot.py**: CLI commands and cron entry points
- **config.py**: Environment configuration with ScannerConfig

### src/skim/brokers/
- **ibkr_client.py**: Custom OAuth 1.0a client (no Gateway)
- **ibkr_oauth.py**: RSA signatures and token management
- **ib_interface.py**: Trading operations and market data

### src/skim/scanners/
- **ibkr_gap_scanner.py**: Gap detection via IBKR scanner
- **asx_announcements.py**: Price-sensitive news filter

### src/skim/strategy/
- **entry.py**: ORH breakout detection
- **exit.py**: Stop-loss and profit-taking
- **position_manager.py**: Position sizing and risk

### src/skim/data/
- **database.py**: SQLite CRUD operations
- **models.py**: Candidates, positions, trades models

### src/skim/notifications/
- **discord.py**: Rich embeds for alerts

## Trading Workflow

### Cron-Managed Automated Flow

```
Market Open (00:00:30 UTC / 10:00:30 AEDT)
├── SCAN_IBKR_GAPS
│   ├── Query IBKR scanner for gaps ≥ 3%
│   ├── Filter ASX stocks with volume > 50k
│   └── Save to DB (status: or_tracking)
│
10 Minutes Later (00:10:30 UTC / 10:10:30 AEDT)
├── TRACK_OR_BREAKOUTS
│   ├── Get or_tracking candidates
│   ├── Monitor price for 10 minutes
│   ├── Calculate opening range high (ORH)
│   └── Update breakouts (status: orh_breakout)
│
12 Minutes After Open (00:12:00 UTC / 10:12:00 AEDT)
├── EXECUTE_ORH_BREAKOUTS
│   ├── Check max positions limit
│   ├── Get orh_breakout candidates
│   ├── Place BUY orders via OAuth client
│   └── Record positions (status: entered)
│
Every 5 Minutes During Market Hours
├── MANAGE_POSITIONS
│   ├── Get open positions
│   ├── Day 3? → Sell 50% (status: half_exited)
│   ├── Price ≤ stop_loss? → Sell all (status: closed)
│   └── Continue monitoring
│
End of Day (05:30 UTC / 4:30 PM AEDT)
└── STATUS
    └── Report: candidates, positions, P&L
```

### Data Flow

**Candidates Table**: watching → or_tracking → orh_breakout → entered
**Positions Table**: entered → half_exited → closed
**Trades Table**: All buy/sell transactions with timestamps

## Technology Stack

### Backend
- **Python 3.12**: Core language
- **SQLite**: Database
- **OAuth 1.0a**: Direct IBKR authentication
- **Docker**: Containerization

### Key Dependencies
- requests (HTTP client)
- beautifulsoup4 (HTML parsing)
- pycryptodome (RSA cryptography)
- loguru (logging)
- python-dotenv (environment management)

### Development Tools
- uv (package management)
- ruff (linting and formatting)
- pytest (testing framework)
- pre-commit (git hooks)

## Security Architecture

### OAuth 1.0a Implementation
- RSA signature generation for each request
- Token encryption/decryption with private keys
- No plaintext secrets in code
- Volume-mounted key files (not in container image)

### Data Protection
- Environment-based configuration
- Database encryption (SQLite)
- Log sanitization
- Minimal attack surface (no web server)

## Deployment Architecture

### Container-Based Deployment
- Single lightweight container
- Python 3.12-slim base image
- Volume-mounted persistent data:
  - `/app/data/` - SQLite database
  - `/app/logs/` - Log files
  - `/opt/skim/oauth_keys/` - RSA keys
- Cron daemon for scheduling
- GitOps webhook automation

### Resource Optimization
- 256-512 MB RAM usage
- No Java/JVM overhead
- Minimal dependencies (7 packages)
- Cron-based execution (idle most of time)

## Design Decisions

### OAuth 1.0a vs Gateway
- 50-75% cost reduction (1 GB vs 2-4 GB RAM)
- No IB Gateway or IBeam containers
- Direct lightweight API access
- Better reliability (no Gateway crashes)

### SQLite vs PostgreSQL
- Single-account trading (no concurrent writes)
- Simplicity (no separate database server)
- Portability (single file backups)

### Cron vs Real-Time
- Predictable ASX market schedule
- Resource efficient (bot idle 23 hrs/day)
- Simple, battle-tested scheduling

### ORH Breakout Strategy
- Gap + opening range momentum
- Objective entry signal
- Stop at low of day
- Day 3 half-sell reduces exposure
