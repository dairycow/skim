# Architecture

This document describes the architecture and component structure of the Skim trading bot.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Skim Trading Bot                         │
├─────────────────────────────────────────────────────────────┤
│  Cron Scheduler (Container Startup)                         │
│  ├── SCAN (23:15 UTC)     ──→ Market Scanning               │
│  ├── MONITOR (23:20 UTC)  ──→ Gap Monitoring                │
│  ├── EXECUTE (23:25 UTC)  ──→ Order Execution               │
│  ├── MANAGE (*/5 min)     ──→ Position Management           │
│  └── STATUS (05:30 UTC)   ──→ Daily Reporting               │
├─────────────────────────────────────────────────────────────┤
│  Core Components                                           │
│  ├── Market Scanners     ──→ Data Sources                   │
│  ├── Trading Strategy    ──→ Entry/Exit Logic              │
│  ├── Position Manager    ──→ Risk Management                │
│  └── IBKR Interface      ──→ OAuth 1.0a API Client          │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                │
│  ├── SQLite Database     ──→ Candidates, Positions, Trades  │
│  └── Log Files          ──→ Execution Logs                 │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
skim/
├── src/skim/                    # Core application code
│   ├── core/                    # Orchestration and main logic
│   │   ├── bot.py              # Main bot entry point and CLI
│   │   └── config.py           # Configuration management
│   ├── brokers/                 # Interactive Brokers integration
│   │   ├── ib_interface.py     # IBKR API interface
│   │   ├── ibkr_client.py      # Custom OAuth 1.0a client
│   │   └── ibkr_oauth.py       # OAuth authentication logic
│   ├── scanners/                # Market data sources
│   │   ├── asx_announcements.py # ASX announcement scanner
│   │   └── tradingview.py      # TradingView API integration
│   ├── strategy/                # Trading algorithms
│   │   ├── entry.py            # Entry signal generation
│   │   ├── exit.py             # Exit signal generation
│   │   └── position_manager.py # Position and risk management
│   └── data/                    # Data layer
│       ├── database.py         # Database operations
│       └── models.py           # Data models
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data and mocks
├── docs/                        # Documentation
├── deploy/                      # Deployment scripts
│   └── webhook.sh              # GitOps deployment script
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Container definition
└── pyproject.toml              # Project configuration
```

## Core Components

### 1. Core Module (`src/skim/core/`)

**bot.py** - Main orchestration and CLI interface
- Command-line interface for bot operations
- Cron job integration
- Workflow coordination

**config.py** - Configuration management
- Environment variable handling
- Trading parameters
- OAuth credentials management

### 2. Brokers Module (`src/skim/brokers/`)

**ibkr_client.py** - Custom OAuth 1.0a client
- Direct IBKR API authentication
- No Gateway required
- Lightweight Python implementation

**ibkr_oauth.py** - OAuth authentication logic
- OAuth 1.0a signature generation
- RSA key management
- Session handling

**ib_interface.py** - IBKR API interface
- Order placement and management
- Account information retrieval
- Market data queries

### 3. Scanners Module (`src/skim/scanners/`)

**asx_announcements.py** - ASX announcement scanner
- Price-sensitive announcement filtering
- ASX API integration
- News sentiment analysis

**tradingview.py** - TradingView API integration
- Market scanning
- Gap detection
- Technical indicator data

### 4. Strategy Module (`src/skim/strategy/`)

**entry.py** - Entry signal generation
- Gap analysis
- Breakout detection
- Entry timing logic

**exit.py** - Exit signal generation
- Stop-loss management
- Profit-taking logic
- Trailing stops

**position_manager.py** - Position and risk management
- Position sizing
- Risk calculation
- Portfolio management

### 5. Data Module (`src/skim/data/`)

**database.py** - Database operations
- SQLite database management
- CRUD operations
- Data persistence

**models.py** - Data models
- SQLAlchemy models
- Database schema
- Data validation

## Data Flow

### Trading Workflow

1. **SCAN Phase** (23:15 UTC)
   ```
   TradingView Scanner → Gap Detection → ASX Filter → Database Storage
   ```

2. **MONITOR Phase** (23:20 UTC)
   ```
   Database Candidates → Gap Validation → Status Update
   ```

3. **EXECUTE Phase** (23:25 UTC)
   ```
   Triggered Candidates → Order Placement → Position Recording
   ```

4. **MANAGE Phase** (Every 5 min)
   ```
   Open Positions → Exit Signals → Order Execution → Status Updates
   ```

### Data Models

**Candidates Table**
- Stock symbols identified during scan
- Gap percentages and announcement data
- Status: watching → triggered

**Positions Table**
- Active trading positions
- Entry/exit prices and quantities
- Status: entered → half_exited → closed

**Trades Table**
- All buy/sell transactions
- Timestamps and execution details
- P&L calculations

## Technology Stack

### Backend
- **Python 3.12** - Core language
- **SQLite** - Database
- **OAuth 1.0a** - IBKR authentication
- **Docker** - Containerization

### Dependencies
- **requests** - HTTP client
- **beautifulsoup4** - HTML parsing
- **pycryptodome** - Cryptographic operations
- **loguru** - Logging
- **python-dotenv** - Environment management

### Development Tools
- **uv** - Package management
- **ruff** - Linting and formatting
- **pytest** - Testing framework
- **pre-commit** - Git hooks

## Security Architecture

### OAuth 1.0a Implementation
- RSA signature generation
- Token encryption/decryption
- Secure credential storage
- No plaintext secrets in code

### Data Protection
- Environment-based configuration
- Volume-mounted sensitive files
- Database encryption (SQLite)
- Log sanitization

## Deployment Architecture

### Container-Based Deployment
- Single container deployment
- Volume-mounted persistent data
- Cron-based scheduling
- GitOps automation

### Resource Optimization
- Lightweight Python 3.12-slim base image
- Minimal dependencies (7 packages)
- No Java/JVM overhead
- 256-512 MB RAM usage

## Integration Points

### External APIs
- **Interactive Brokers** - Trading and market data
- **TradingView** - Market scanning
- **ASX** - Company announcements

### Internal Systems
- **Cron Daemon** - Workflow scheduling
- **SQLite Database** - Data persistence
- **File System** - Log and key storage

## Scalability Considerations

### Current Limitations
- Single-account trading
- SQLite database (single-node)
- Cron-based scheduling

### Future Enhancements
- Multi-account support
- PostgreSQL migration
- Microservices architecture
- Real-time event processing

## Monitoring and Observability

### Logging Strategy
- Structured logging with loguru
- Component-based log separation
- Performance metrics tracking
- Error alerting

### Health Checks
- OAuth authentication status
- Database connectivity
- API rate limiting
- System resource monitoring