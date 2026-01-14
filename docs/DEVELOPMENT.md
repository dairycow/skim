# Development

Local setup, development workflow, testing, deployment, and configuration management.

## Prerequisites

- Python 3.13+
- uv (unified Python toolchain)
- Git

## Local Setup

### Install Dependencies
```bash
# Clone repository
git clone https://github.com/your-repo/skim.git
cd skim

# Install dependencies and create virtual environment
uv sync

# Install pre-commit hooks (one-time setup)
uv run pre-commit install
```

### Environment Configuration
```bash
# Copy example config
cp .env.example .env

# Essential variables
PAPER_TRADING=true
IBKR_SOCKET_PORT=7497  # 7497 = paper, 7496 = live
IBKR_CLIENT_ID=1

# Optional notifications
DISCORD_WEBHOOK_URL=your_webhook_url
```

## Development Workflow

### Quality Checks
```bash
# Run all checks
uv run pre-commit run --all-files

# Individual checks
uv run ruff check src tests        # Linting
uv run ruff format src tests       # Formatting
uv run pytest                      # Testing
```

### Making Changes
1. Create feature branch
2. Make changes following TDD (RED → GREEN → REFACTOR)
3. Run quality checks
4. Commit (pre-commit hooks run automatically)
5. Push and create pull request

### Running Bot Locally
```bash
# Bot commands
uv run python -m skim.trading.core.bot purge_candidates  # Clear previous-day candidates
uv run python -m skim.trading.core.bot scan              # Full strategy scan (gaps + news)
uv run python -m skim.trading.core.bot trade             # Execute breakouts
uv run python -m skim.trading.core.bot manage            # Monitor and manage positions
uv run python -m skim.trading.core.bot status            # Health check

# Shortcuts via entry points
uv run skim purge-candidates
uv run skim scan
uv run skim trade
uv run skim manage

# Analysis commands
uv run skim-analyze top 2024 --json
uv run skim-analyze gaps 2024 --limit 10 --json
```

## Testing

### Test Structure
```
tests/
├── domain/           # Domain model tests
├── trading/          # Trading bot tests
├── shared/           # Shared service tests
└── analysis/         # Analysis CLI tests
```

### Running Tests
```bash
# All tests
uv run pytest

# By module
uv run pytest tests/domain/
uv run pytest tests/trading/
uv run pytest tests/shared/

# With coverage
uv run pytest --cov=src/skim --cov-report=html

# Specific test
uv run pytest tests/domain/test_candidate.py
```

### Test Markers
```python
@pytest.mark.unit         # Fast, everything mocked
@pytest.mark.integration  # Real credentials required
@pytest.mark.manual       # Not run in CI
```

### Writing Tests
Follow TDD with Arrange-Act-Assert pattern. Use `@pytest.mark.unit` for mocked tests and `@pytest.mark.integration` for real credentials.

## Deployment

### Production Setup
```bash
# On server: Install dependencies
sudo apt update && sudo apt install -y python3.13 python3.13-venv cron curl git
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create skim user
sudo useradd -r -m -d /opt/skim -s /bin/bash skim

# Clone repo as skim user
sudo -u skim git clone https://github.com/your-repo/skim.git /opt/skim
cd /opt/skim

# Set up directories
sudo mkdir -p /opt/skim/{logs,data}
sudo chown -R skim:skim /opt/skim

# Create .env file
sudo -u skim cp .env.example .env
# Edit with production values

# Install Python dependencies
sudo -u skim /home/skim/.local/bin/uv sync --frozen

# Install crontab
sudo cp crontab /etc/cron.d/skim-trading-bot
sudo chmod 644 /etc/cron.d/skim-trading-bot
sudo chown root:root /etc/cron.d/skim-trading-bot

# Configure sudoers
sudo cp deploy/sudoers-skim /etc/sudoers.d/skim-deploy
sudo chmod 440 /etc/sudoers.d/skim-deploy

# Reload cron
sudo systemctl reload cron

# Verify deployment
tail -f /opt/skim/logs/*.log
```

### GitOps Automation
Automated deployments trigger on push to main via webhook:

1. GitHub webhook triggers `deploy/webhook.sh`
2. Script runs: `git reset --hard origin/main`
3. Updates dependencies: `uv sync --frozen`
4. Reloads crontab: `sudo cp crontab /etc/cron.d/skim-trading-bot`
5. Reloads cron: `sudo systemctl reload cron`

**Persistent Data** (survives deployments):
- `/opt/skim/data/` - SQLite database
- `/opt/skim/logs/` - Log files
- `/opt/skim/.env` - Configuration

### GitOps Setup
Install webhook receiver, configure systemd service, and set up GitHub webhook. See old WEBHOOK_SETUP.md for detailed SSL configuration.

## Configuration Management

### Scanner Settings
Configure in `src/skim/trading/core/config.py` via `ScannerConfig` dataclass:
- Volume filter: 50,000 shares
- Price filter: $0.50
- OR duration: 5 minutes
- OR poll interval: 30 seconds
- Gap fill tolerance: $1.0

### Cron Schedule (UTC, AEDT = UTC+11)
- **22:55 UTC (09:55 AEDT)** - purge_candidates
- **23:00 UTC (10:00 AEDT)** - scan
- **23:05 UTC (10:05 AEDT)** - track_ranges
- **23:10 UTC (10:10 AEDT)** - alert
- **23:15-06:00 UTC (*/5)** - trade
- **23:15-06:00 UTC (*/5)** - manage

Production uses the repository `crontab` (copied to `/etc/cron.d/skim-trading-bot`) which includes the `skim` user field and redirects to `/opt/skim/logs/cron.log`.

### Environment-Specific Config

| Setting | Development | Production | Testing |
|---------|-------------|------------|---------|
| PAPER_TRADING | true | false | true |
| LOG_LEVEL | DEBUG | INFO | DEBUG |
| DB_PATH | ./data/skim.db | /opt/skim/data/skim.db | :memory: |
| IBKR_SOCKET_PORT | 7497 | 7496 | 7497 |

## Troubleshooting

### IBKR Connection Failed
```bash
cat .env | grep IBKR                    # Check config
grep -i ibkr logs/*.log                 # Check logs (local)
grep -i ibkr /opt/skim/logs/*.log       # Check logs (production)
```

### Database or Cron Issues
```bash
ls -la data/skim.db                     # Check database (local)
ls -la /opt/skim/data/skim.db           # Check database (production)
cat /etc/cron.d/skim-trading-bot        # Verify cron schedule
tail -100 /opt/skim/logs/cron.log       # Inspect cron logs
tail -100 /opt/skim/logs/skim_*.log     # Inspect application logs
```

## Code Quality

- **Ruff**: Line length 80, Python 3.13, double quotes
- **Pre-commit**: Linting, formatting, testing
- **Type hints**: `str | None`, not `Optional[str]`

### Style Guidelines
- 80 chars max per line
- Double quotes for strings
- 4 spaces for indentation
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE
- Google-style docstrings

## Resource Requirements

**Production**: 1 GB RAM, 25 GB SSD, 1 vCPU (~$6/month)
