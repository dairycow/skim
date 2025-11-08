# Skim - ASX Pivot Trading Bot

Production-ready ASX pivot trading bot with modern layered architecture. Uses OAuth 1.0a authentication to connect directly to Interactive Brokers API - no Gateway needed!

## Strategy Overview
Scan ASX for momentum stocks with gaps >2%, filter by price-sensitive announcements, enter on breakouts, manage positions with automated stops.

## Quick Start
```bash
git clone https://github.com/your-repo/skim.git
cd skim
# See docs/SETUP.md for detailed configuration
docker-compose up -d
```

## Documentation
- **Setup & Configuration**: docs/SETUP.md
- **Development**: docs/DEVELOPMENT.md  
- **Architecture**: docs/ARCHITECTURE.md
- **Trading Workflow**: docs/trading-workflow.md
- **GitOps Deployment**: docs/GITOPS_NOTES.md

## License
MIT License