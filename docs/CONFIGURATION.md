# Configuration Guide

This guide covers detailed configuration of the Skim trading bot, including environment variables, OAuth setup, and trading parameters.

## Environment Configuration

### Basic Setup
```bash
# Copy example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

## Configuration Variables

### Trading Settings

#### Core Trading Parameters
```bash
# Trading mode (recommended: true for testing)
PAPER_TRADING=true

# Minimum gap percentage to consider
GAP_THRESHOLD=3.0

# Maximum position size in AUD
MAX_POSITION_SIZE=1000

# Maximum concurrent positions
MAX_POSITIONS=5

# Database file path
DB_PATH=/app/data/skim.db
```

#### Risk Management
```bash
# Stop loss percentage (optional, defaults to low of day)
STOP_LOSS_PERCENTAGE=2.0

# Take profit percentage (optional)
TAKE_PROFIT_PERCENTAGE=10.0

# Position sizing method (fixed, percentage, volatility)
POSITION_SIZING_METHOD=fixed

# Risk per trade as percentage of portfolio
RISK_PER_TRADE=2.0
```

### Market Data Configuration

#### TradingView API
```bash
# TradingView scanner configuration (if needed)
TRADINGVIEW_API_KEY=your_api_key
TRADINGVIEW_SCANNER=australia
TRADINGVIEW_INTERVAL=1D
```

#### ASX Announcements
```bash
# ASX announcement scanner settings
ASX_ANNOUNCEMENT_FILTER=price-sensitive
ASX_API_TIMEOUT=30
```

## OAuth 1.0a Configuration

The bot uses OAuth 1.0a to authenticate directly with Interactive Brokers API, eliminating the need for IB Gateway.

### Step 1: Generate OAuth Credentials

1. **Log into IBKR Portal**: https://www.interactivebrokers.com/portal
2. **Navigate**: Settings → API → Access
3. **Enable OAuth 1.0a**
4. **Generate Credentials**:
   - Consumer Key
   - Access Token
   - Access Token Secret
   - DH Prime (Diffie-Hellman)

### Step 2: Generate RSA Keys

```bash
# Create directory for keys
mkdir -p oauth_keys

# Generate signature key
openssl genrsa -out oauth_keys/private_signature.pem 2048

# Generate encryption key
openssl genrsa -out oauth_keys/private_encryption.pem 2048

# Set proper permissions
chmod 600 oauth_keys/*.pem
```

### Step 3: Configure Environment Variables

```bash
# ============================================================
# OAuth 1.0a Authentication for IBKR Client Portal API
# ============================================================

# Consumer key from IBKR (e.g., PSKIMMILK)
OAUTH_CONSUMER_KEY=your_consumer_key

# Access token and secret from IBKR OAuth setup
OAUTH_ACCESS_TOKEN=your_access_token
OAUTH_ACCESS_TOKEN_SECRET=your_encrypted_access_token_secret

# Paths to your RSA .pem key files
OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem

# Diffie-Hellman prime (hex string from IBKR, no spaces/colons)
OAUTH_DH_PRIME=your_dh_prime_hex_string
```

### Step 4: Upload Keys to Production Server

```bash
# Copy keys to server
scp -r oauth_keys root@your-server:/opt/skim/

# Set permissions on server
ssh root@your-server "chmod 600 /opt/skim/oauth_keys/*.pem"
```

## OAuth Configuration Details

### Consumer Key
- **Format**: Alphanumeric string provided by IBKR
- **Example**: `PSKIMMILK`
- **Purpose**: Identifies your application to IBKR

### Access Token & Secret
- **Access Token**: Token authorizing your application
- **Access Token Secret**: Secret used to sign requests
- **Security**: Treat as passwords, never commit to version control

### RSA Keys
- **Signature Key**: Used for OAuth signature generation
- **Encryption Key**: Used for encrypting sensitive data
- **Format**: PEM-encoded RSA private keys (2048-bit)

### DH Prime
- **Purpose**: Diffie-Hellman key exchange
- **Format**: Hexadecimal string (no spaces or colons)
- **Source**: Provided by IBKR during OAuth setup

## Database Configuration

### SQLite Settings
```bash
# Database path (production)
DB_PATH=/app/data/skim.db

# Database path (development)
# DB_PATH=./data/skim.db

# Database connection timeout (seconds)
DB_TIMEOUT=30

# Database connection pool size
DB_POOL_SIZE=5
```

### Database Backup
```bash
# Enable automatic backups
DB_BACKUP_ENABLED=true

# Backup interval in hours
DB_BACKUP_INTERVAL=24

# Backup retention in days
DB_BACKUP_RETENTION=30

# Backup path
DB_BACKUP_PATH=/app/data/backups/
```

## Logging Configuration

### Log Levels
```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file path
LOG_PATH=/app/logs/skim.log

# Log rotation settings
LOG_ROTATION=1 day
LOG_RETENTION=30 days
```

### Component-Specific Logging
```bash
# Enable debug logging for specific components
DEBUG_OAUTH=false
DEBUG_SCANNERS=false
DEBUG_STRATEGY=false
DEBUG_BROKERS=false
```

## Performance Configuration

### Rate Limiting
```bash
# IBKR API rate limits
IBKR_REQUESTS_PER_MINUTE=60
IBKR_REQUESTS_PER_SECOND=1

# TradingView API rate limits
TV_REQUESTS_PER_MINUTE=120

# ASX API rate limits
ASX_REQUESTS_PER_MINUTE=30
```

### Timeout Settings
```bash
# HTTP request timeouts (seconds)
HTTP_TIMEOUT=30
OAUTH_TIMEOUT=60

# Database operation timeout
DB_OPERATION_TIMEOUT=10
```

## Security Configuration

### SSL/TLS
```bash
# Verify SSL certificates
SSL_VERIFY=true

# Custom CA certificate path (if needed)
SSL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

### API Security
```bash
# Enable API request signing
API_REQUEST_SIGNING=true

# Request signature validity (seconds)
SIGNATURE_VALIDITY=300
```

## Advanced Configuration

### Cron Schedule
```bash
# Custom cron schedules (override defaults)
SCAN_SCHEDULE="15 23 * * 0-4"
MONITOR_SCHEDULE="20 23 * * 0-4"
EXECUTE_SCHEDULE="25 23 * * 0-4"
MANAGE_SCHEDULE="*/5 23-5 * * 0-4"
STATUS_SCHEDULE="30 5 * * 1-5"
```

### Market Hours
```bash
# ASX market hours (UTC)
MARKET_OPEN_TIME="23:00"
MARKET_CLOSE_TIME="05:00"

# Timezone
TIMEZONE="Australia/Sydney"
```

### Notification Settings
```bash
# Email notifications (optional)
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=alerts@example.com

# Slack notifications (optional)
SLACK_ENABLED=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
```

## Environment-Specific Configuration

### Development (.env.development)
```bash
PAPER_TRADING=true
LOG_LEVEL=DEBUG
DB_PATH=./data/skim.db
OAUTH_SIGNATURE_PATH=./oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=./oauth_keys/private_encryption.pem
```

### Production (.env.production)
```bash
PAPER_TRADING=false
LOG_LEVEL=INFO
DB_PATH=/app/data/skim.db
OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem
```

### Testing (.env.test)
```bash
PAPER_TRADING=true
LOG_LEVEL=DEBUG
DB_PATH=:memory:  # In-memory database for tests
GAP_THRESHOLD=1.0  # Lower threshold for test data
MAX_POSITIONS=1
```

## Configuration Validation

### Verify Configuration
```bash
# Check environment variables
uv run python -c "from skim.core.config import Config; print(Config().dict())"

# Test OAuth authentication
uv run python -m skim.core.bot status

# Validate database connection
uv run python -c "from skim.data.database import Database; db = Database(); print('Database connected')"
```

### Common Configuration Issues

#### OAuth Authentication Failed
```bash
# Check OAuth credentials
echo "Consumer Key: $OAUTH_CONSUMER_KEY"
echo "Access Token: $OAUTH_ACCESS_TOKEN"

# Verify key files exist
ls -la $OAUTH_SIGNATURE_PATH
ls -la $OAUTH_ENCRYPTION_PATH

# Test OAuth flow
uv run python -m skim.brokers.ibkr_oauth test
```

#### Database Connection Issues
```bash
# Check database path
ls -la $DB_PATH

# Test database permissions
sqlite3 $DB_PATH ".tables"
```

#### Permission Issues
```bash
# Check file permissions
ls -la oauth_keys/
chmod 600 oauth_keys/*.pem

# Check directory permissions
ls -la /app/data/
chmod 755 /app/data/
```

## Security Best Practices

### Environment Variables
- Never commit `.env` files to version control
- Use strong, unique secrets
- Rotate credentials regularly
- Use different credentials for each environment

### Key Management
- Store RSA keys securely
- Use file permissions (600) for key files
- Backup keys securely
- Monitor key access logs

### Network Security
- Use HTTPS for all API calls
- Verify SSL certificates
- Implement rate limiting
- Monitor API usage

## Troubleshooting

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Enable component-specific debugging
DEBUG_OAUTH=true
DEBUG_BROKERS=true
```

### Test Configuration
```bash
# Test with minimal configuration
PAPER_TRADING=true
MAX_POSITIONS=1
GAP_THRESHOLD=5.0

# Run single command
uv run python -m skim.core.bot scan --dry-run
```

### Configuration Reset
```bash
# Reset to defaults
cp .env.example .env

# Reconfigure with your values
nano .env
```

For additional help, see the [Setup Guide](SETUP.md) or [Development Guide](DEVELOPMENT.md).