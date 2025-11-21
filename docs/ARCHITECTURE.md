# Architecture

The Skim trading bot is implemented as a cron-driven, containerized Python application. See the codebase for details; this summary references implementation files rather than re-writing behavior.

## High-Level Overview

See code for actual flow; the architecture is composed of a small, cohesive set of modules under `src/skim/`.

## Core Components

- `src/skim/core/bot.py` – CLI entry points and cron integration
- `src/skim/core/config.py` – environment configuration and ScannerConfig
- `src/skim/brokers/ibkr_client.py` – OAuth 1.0a client, IBKR interactions
- `src/skim/brokers/ibkr_oauth.py` – RSA signatures and token management
- `src/skim/brokers/ib_interface.py` – trading operations and market data
- `src/skim/scanners/ibkr_gap_scanner.py` – gap detection
- `src/skim/scanners/asx_announcements.py` – price-sensitive news filter
- `src/skim/strategy/entry.py` – ORH breakout logic
- `src/skim/strategy/exit.py` – stop-loss and take-profit
- `src/skim/strategy/position_manager.py` – risk and positions
- `src/skim/data/database.py` – sqlite CRUD
- `src/skim/data/models.py` – domain models
- `src/skim/notifications/discord.py` – alerts

## Trading Workflow

- Cron-driven sequence drives scanning, tracking, execution, management, and reporting
- Exact schedule is defined in `crontab` (see file for timings)

## Data Flow

- Tables and status transitions are defined in `src/skim/data/models.py`
- Typical progression: candidates → or_tracking → orh_breakout → entered; positions: entered → half_exited → closed

## Technology Stack

- Python 3.12
- SQLite
- OAuth 1.0a
- Docker

- Key dependencies and dev-tools are listed in `pyproject.toml`

## Development Tools

- Ruff, pytest, pre-commit (as configured in `pyproject.toml` and dev-dependencies)

## Security Architecture

- OAuth 1.0a with RSA signatures; token encryption/decryption with private keys
- No plaintext secrets in code; volume-mounted key files
- Environment-based configuration; minimized attack surface

## Deployment Architecture

- Containerized deployment using Docker; single lightweight container
- Data and logs persisted via mounted volumes
- Cron daemon for scheduling; GitOps webhook automation
- See `docker-compose.yml` and `crontab` for specifics

## Design Decisions

- OAuth 1.0a vs Gateway: lightweight direct IBKR access, lower footprint
- SQLite vs PostgreSQL: simplicity for a single account
- Cron vs Real-Time: predictable schedule, low resource use
- ORH breakout strategy: gap + opening range momentum

End of file