# Integrations

External service integrations: Discord webhooks and IBKR API.

## Discord Webhook Integration

### Overview
Discord notifications provide real-time alerts for:
- Market scan results (candidates found)
- Trade executions (entries/exits)
- Position status updates
- Error notifications

### Setup

1. **Create webhook**: Discord Server → Integrations → Create Webhook
2. **Configure**: Add `DISCORD_WEBHOOK_URL` to .env
3. **Deploy**: Restart bot with `docker-compose restart bot`

Webhook URL: `https://discord.com/api/webhooks/{ID}/{TOKEN}`

### Notification Types

**Scan Results** (Green):
- Title: "ASX Market Scan Complete"
- Description: "X new candidates found"
- Fields: Ticker, gap %, price

**No Candidates** (Yellow):
- Title: "ASX Market Scan Complete"
- Description: "No new candidates found"

**Errors** (Red):
- Title: "ASX Market Scan Error"
- Description: Error details

### Troubleshooting
```bash
docker-compose exec bot printenv DISCORD_WEBHOOK_URL  # Verify URL
docker-compose logs bot | grep discord                # Check logs
curl -X POST -d '{"content":"Test"}' "YOUR_URL"       # Test webhook
```

**Security**: Treat URL as password, never commit, rotate regularly. Rate limit: 30/min.

## IBKR Web API Integration

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
5. Maintains session for API calls
```

### Setup

#### 1. Generate OAuth Credentials
1. [IBKR Portal](https://www.interactivebrokers.com/portal) → Settings → API → Access
2. Enable OAuth 1.0a
3. Save: Consumer Key, Access Token, Access Token Secret, DH Prime

#### 2. Generate RSA Keys
```bash
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
```

#### 4. Deploy to Production
```bash
scp -r oauth_keys root@server:/opt/skim/
ssh root@server "chmod 600 /opt/skim/oauth_keys/*.pem"
```

### Key API Endpoints

**Trading**: Place/cancel orders, get status
**Market Data**: Scanner, quotes, historical bars
**Account**: Positions, balance, summary

**Servers**: Production (`api.ibkr.com`), Sandbox (`qa.interactivebrokers.com`)

**OAuth Components**: Consumer Key, Access Token, RSA Signatures, DH Prime
**Implementation**: `src/skim/brokers/ibkr_oauth.py` and `ibkr_client.py`

### Troubleshooting
```bash
cat .env | grep OAUTH                         # Check credentials
ls -la oauth_keys/                            # Verify keys (600 perms)
uv run python -m skim.core.bot status         # Test auth
docker-compose logs bot | grep oauth          # Check logs
```

**Common Issues**:
- Invalid consumer key: Verify no extra spaces
- Missing keys: Ensure private_signature.pem and private_encryption.pem exist
- Permission errors: Keys must be 600 (`-rw-------`)

**Rate Limits**: Implement backoff for HTTP 429 errors.

## ASX Announcements

Uses ASX public API to filter price-sensitive announcements.
**Implementation**: `src/skim/scanners/asx_announcements.py`

## Security Best Practices

1. Never commit secrets (.env, .pem files)
2. Rotate credentials periodically
3. File permissions: 600 for keys and .env
4. Monitor logs for auth failures
5. Use HTTPS for all API calls
6. Validate all API responses
