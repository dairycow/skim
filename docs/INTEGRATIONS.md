# Integrations

External service integrations: Discord webhooks, IBKR API, and ASX announcements.

## Discord Webhook Integration

### Overview
Discord notifications provide real-time alerts for:
- Tradeable candidates (gap + news + opening range)
- Trade executions (entries and exits)
- P&L updates
- Error notifications

### Setup

1. **Create webhook**: Discord Server → Integrations → Create Webhook
2. **Configure**: Add `DISCORD_WEBHOOK_URL` to .env
3. **Verify**: Check logs after next scheduled run

Webhook URL: `https://discord.com/api/webhooks/{ID}/{TOKEN}`

### Notification Types

**Tradeable Candidates** (Green):
- Title: "Tradeable Candidates Ready"
- Fields: Ticker, gap %, ORH, ORL, headline
- Sent during alert phase (10:10 AM AEDT)

**Trade Executed** (Green/Red):
- Title: "Trade Executed"
- Fields: Ticker, action (BUY/SELL), quantity, price, P&L (if available)

**No Candidates** (Yellow):
- Title: "Tradeable Candidates Ready"
- Description: "No tradeable candidates found"

**Errors** (Red):
- Title: "ASX Market Scan Error"
- Description: Error details

### Troubleshooting
```bash
grep DISCORD_WEBHOOK_URL .env                         # Verify URL
tail -100 logs/skim_*.log | grep discord              # Check logs
curl -X POST -d '{"content":"Test"}' "YOUR_URL"       # Test webhook
```

**Security**: Treat URL as password, never commit, rotate regularly. Rate limit: 30/min.

## IBKR API Integration

### Overview
Direct integration with IBKR Client Portal API using OAuth 1.0a authentication.

**Benefits**:
- No IB Gateway required
- Lightweight (256-512 MB RAM vs 2-4 GB)
- Direct API access
- Better reliability

### Authentication Flow

```
1. Generate OAuth credentials in IBKR Portal
2. Create RSA keys for signatures and encryption
3. Configure environment variables
4. Bot authenticates on startup using OAuth 1.0a
5. Maintains session for API calls (LST token management)
```

### Setup

#### 1. Generate OAuth Credentials
1. [IBKR Portal](https://www.interactivebrokers.com/portal) → Settings → API → Access
2. Enable OAuth 1.0a
3. Save: Consumer Key, Access Token, Access Token Secret, DH Prime

#### 2. Generate RSA Keys
```bash
mkdir -p oauth_keys
openssl genrsa -out oauth_keys/private_signature.pem 2048
openssl genrsa -out oauth_keys/private_encryption.pem 2048
chmod 600 oauth_keys/*.pem
```

#### 3. Configure Environment
```bash
OAUTH_CONSUMER_KEY=your_key
OAUTH_ACCESS_TOKEN=your_token
OAUTH_ACCESS_TOKEN_SECRET=your_secret
OAUTH_DH_PRIME=your_dh_prime_hex
OAUTH_SIGNATURE_KEY_PATH=oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_KEY_PATH=oauth_keys/private_encryption.pem
```

#### 4. Deploy to Production
```bash
scp -r oauth_keys root@server:/opt/skim/
ssh root@server "chmod 600 /opt/skim/oauth_keys/*.pem"
```

### Key Components

**Implementation**: `src/skim/infrastructure/brokers/ibkr/auth.py`

**Core Classes**:
- `IBKRAuthManager` - Manages OAuth LST generation and token lifecycle
- `generate_lst()` - Generates Live Session Token for API access

**IBKR Services** (`src/skim/trading/brokers/`):
- `ibkr_client.py` - IBKR connection and session management
- `ibkr_market_data.py` - Real-time market data (quotes, bars)
- `ibkr_orders.py` - Order placement and management
- `ibkr_gap_scanner.py` - IBKR scanner API integration

**Servers**: Production (`api.ibkr.com`), Sandbox (`qa.interactivebrokers.com`)

### Troubleshooting
```bash
cat .env | grep OAUTH                         # Check credentials
ls -la oauth_keys/                            # Verify keys (600 perms)
tail -100 logs/skim_*.log | grep oauth        # Check logs
tail -100 logs/skim_*.log | grep ibkr         # Check IBKR logs
```

**Common Issues**:
- Invalid consumer key: Verify no extra spaces
- Missing keys: Ensure private_signature.pem and private_encryption.pem exist
- Permission errors: Keys must be 600 (`-rw-------`)
- LST expired: Auth manager auto-regenerates on expiration

**Rate Limits**: Implement backoff for HTTP 429 errors.

### Session Conflicts

**Symptom**: Scanner returns HTTP 500 with error `"Finished: EMPTY response is received."`

**Cause**: IBKR allows only one brokerage session per username. If you're logged into TradingView, IBKR Web Portal, or any other IBKR interface, the scanner will fail even though authentication succeeds.

**Resolution**:
1. Log out of TradingView, IBKR Portal, or any other IBKR sessions
2. Wait 1-2 minutes for session to clear
3. Re-run the scan

**Verification**: Check logs for `'competing': False` - this indicates IBKR doesn't detect a conflict, but the scanner endpoint may still be affected by other sessions.

**Alternative**: The bot's `connect()` method calls `/logout` before creating a new session with `compete: True`, but some sessions (like TradingView) may use a different session type that isn't cleared by this mechanism.

## ASX Announcements Integration

### Overview
Fetches price-sensitive announcements from ASX website to identify news-driven trading candidates.

**Implementation**: `src/skim/trading/scanners/asx_announcements.py`

**Scanner Class**: `ASXAnnouncementScanner`

**ASX Endpoint**: `https://www.asx.com.au/asx/v2/statistics/todayAnns.do`

### Filtering Options

**PriceSensitiveFilter** (`src/skim/trading/validation/scanners.py`):
- `min_ticker_length` - Minimum ticker symbol length
- `max_ticker_length` - Maximum ticker symbol length
- `min_headline_length` - Minimum headline length
- `max_headline_length` - Maximum headline length
- `include_only_tickers` - Whitelist of specific tickers
- `exclude_tickers` - Blacklist of tickers to skip

### Output

**ASXAnnouncement** model:
- `ticker` - ASX ticker symbol
- `headline` - Announcement headline
- `announcement_type` - Type (e.g., "pricesens")
- `timestamp` - Announcement timestamp
- `pdf_url` - Link to full announcement PDF (if available)

## Security Best Practices

1. Never commit secrets (.env, .pem files)
2. Rotate credentials periodically
3. File permissions: 600 for keys and .env
4. Monitor logs for auth failures
5. Use HTTPS for all API calls
6. Validate all API responses
