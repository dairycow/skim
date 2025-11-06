# Skim - ASX Pivot Trading Bot

Production-ready ASX pivot trading bot with modern layered architecture. Uses OAuth 1.0a authentication to connect directly to Interactive Brokers API - no Gateway needed! Optimized for iPhone deployment via Termius + DigitalOcean.

## Strategy Overview

1. Scan ASX market using TradingView scanner API for momentum stocks with gaps >2%
2. Filter candidates to only include stocks with price-sensitive ASX announcements today
3. Monitor for gaps ≥3% at market open
4. Enter on breakout above opening range high
5. Stop loss at low of day
6. Sell half position on day 3
7. Trail remaining with 10-day SMA

## Prerequisites

- DigitalOcean Ubuntu droplet (1 GB RAM minimum)
- Docker & Docker Compose installed
- Interactive Brokers paper trading account with OAuth 1.0a credentials

## Quick Start

1. Clone repo and setup environment (see docs/)
2. Generate OAuth credentials from IBKR portal
3. Configure .env with credentials
4. Deploy with docker-compose

See docs/ for detailed setup instructions.

## Documentation

- [Trading Workflow](docs/trading-workflow.md) - Automated cron-managed trading process
- [GitOps Deployment](docs/GITOPS_NOTES.md) - Auto-deployment and infrastructure notes  
- [Webhook Setup](docs/WEBHOOK_SETUP.md) - GitHub webhook configuration
- [Development](README.md#development) - Local development and testing

## Architecture

```
skim/
├── src/skim/          # Core trading logic
│   ├── core/          # Orchestration
│   ├── brokers/       # IBKR OAuth client
│   ├── scanners/      # Market data sources
│   ├── strategy/      # Trading algorithms
│   └── data/          # Database models
├── docker-compose.yml # Container orchestration
└── docs/              # Detailed documentation
```

## Development

See README.md for development setup, testing, and contribution guidelines.

## License

MIT License
