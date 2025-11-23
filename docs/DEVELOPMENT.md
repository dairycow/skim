# Development

Local setup, development workflow, testing, deployment, and configuration management.

## Prerequisites

- Python 3.12+
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
OAUTH_CONSUMER_KEY=your_key
OAUTH_ACCESS_TOKEN=your_token
OAUTH_ACCESS_TOKEN_SECRET=your_secret
OAUTH_DH_PRIME=your_dh_prime_hex


# Optional notifications
DISCORD_WEBHOOK_URL=your_webhook_url
```

### OAuth Key Setup
```bash
# Generate RSA keys
openssl genrsa -out oauth_keys/private_signature.pem 2048
openssl genrsa -out oauth_keys/private_encryption.pem 2048
chmod 600 oauth_keys/*.pem

# For production: upload to server
scp -r oauth_keys root@your-server:/opt/skim/
```

## Development Workflow

### Quality Checks
The project uses UV-based pre-commit hooks:
```bash
# Run all checks
uv run pre-commit run --all-files

# Individual checks
uv run ruff check src tests        # Linting
uv run ruff format src tests       # Formatting
uv run pytest                       # Testing
```

### Making Changes
1. Create feature branch
2. Make changes following TDD (RED → GREEN → REFACTOR)
3. Run quality checks
4. Commit (pre-commit hooks run automatically)
5. Push and create pull request

### Running Bot Locally
```bash
# Run bot commands
uv run python -m skim.core.bot scan_ibkr_gaps
uv run python -m skim.core.bot track_or_breakouts
uv run python -m skim.core.bot execute_orh_breakouts
uv run python -m skim.core.bot manage_positions
uv run python -m skim.core.bot status
```

## Testing

### Test Structure
- `tests/unit/` - Fast unit tests, everything mocked
- `tests/integration/` - Integration tests, real IBKR credentials required
- `tests/fixtures/` - Test data and mock responses

### Running Tests
```bash
# All tests
uv run pytest

# By category
uv run pytest tests/unit/
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=src/skim --cov-report=html

# Specific test
uv run pytest tests/unit/test_database.py::test_create_candidate
```

### Test Markers
```python
@pytest.mark.unit         # Fast, everything mocked
@pytest.mark.integration  # Real credentials required
```

### Writing Tests
Follow TDD with Arrange-Act-Assert pattern. Use `@pytest.mark.unit` for mocked tests and `@pytest.mark.integration` for real credentials.

## Deployment

### Production Setup
```bash
# On server: Install dependencies
sudo apt update && sudo apt install -y python3.12 python3.12-venv cron curl git
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create skim user
sudo useradd -r -m -d /opt/skim -s /bin/bash skim

# Clone repo as skim user
sudo -u skim git clone https://github.com/your-repo/skim.git /opt/skim
cd /opt/skim

# Set up directories
sudo mkdir -p /opt/skim/{logs,data,oauth_keys}
sudo chown -R skim:skim /opt/skim

# Create .env file
sudo -u skim cp .env.example .env
# Edit with production values

# Upload OAuth keys
scp -r oauth_keys root@server:/opt/skim/
sudo chown skim:skim /opt/skim/oauth_keys/*.pem
sudo chmod 600 /opt/skim/oauth_keys/*.pem

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
sudo -u skim /opt/skim/.venv/bin/python -m skim.core.bot status
```

### GitOps Automation
Automated deployments trigger on push to main via webhook:

1. GitHub webhook triggers `deploy/webhook.sh`
2. Script runs: `git reset --hard origin/main`
3. Updates dependencies: `uv sync --frozen`
4. Reloads crontab: `sudo cp crontab /etc/cron.d/skim-trading-bot`
5. Reloads cron: `sudo systemctl reload cron`
6. Health check: `/opt/skim/.venv/bin/python -m skim.core.bot status`

**Persistent Data** (survives deployments):
- `/opt/skim/data/` - SQLite database
- `/opt/skim/logs/` - Log files
- `/opt/skim/oauth_keys/` - RSA keys
- `/opt/skim/.env` - Configuration

### GitOps Setup
Install webhook receiver, configure systemd service, and set up GitHub webhook. See old WEBHOOK_SETUP.md for detailed SSL configuration.

## Configuration Management

### Scanner Settings
Configure in `src/skim/core/config.py` via `ScannerConfig` dataclass:
- Volume filter: 50,000 shares
- Price filter: $0.50
- OR duration: 10 minutes
- OR poll interval: 30 seconds
- Gap fill tolerance: $1.0

### Cron Schedule (UTC times)
- **00:00:30** - SCAN_IBKR_GAPS (10:00:30 AEDT)
- **00:10:30** - TRACK_OR_BREAKOUTS (10:10:30 AEDT)
- **00:12:00** - EXECUTE_ORH_BREAKOUTS (10:12:00 AEDT)
- ***/5 (market hours)** - MANAGE_POSITIONS

### Environment-Specific Config

| Setting | Development | Production | Testing |
|---------|-------------|------------|---------|
| PAPER_TRADING | true | false | true |
| LOG_LEVEL | DEBUG | INFO | DEBUG |
| DB_PATH | ./data/skim.db | /opt/skim/data/skim.db | :memory: |

## Troubleshooting

### OAuth Authentication Failed
```bash
cat .env | grep OAUTH                    # Check credentials
ls -la oauth_keys/                       # Verify keys exist
uv run python -m skim.core.bot status    # Test connection
grep oauth /opt/skim/logs/*.log          # Check logs (production)
```

### Database or Cron Issues
```bash
ls -la data/skim.db                      # Check database (local)
ls -la /opt/skim/data/skim.db            # Check database (production)
cat /etc/cron.d/skim-trading-bot         # Verify cron schedule
tail -100 /opt/skim/logs/cron.log        # Inspect cron logs
tail -100 /opt/skim/logs/skim_*.log      # Inspect application logs
```

## Code Quality

- **Ruff**: Line length 80, Python 3.12
- **Pre-commit**: Linting, formatting, testing
- **VS Code**: Use Python, Ruff extensions

## Resource Requirements

**Production**: 1 GB RAM, 25 GB SSD, 1 vCPU (~$6/month)
**Savings**: OAuth 1.0a reduces costs 50-75% vs Gateway (2-4 GB RAM)
