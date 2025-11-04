# Custom IBKR Client Portal API Client Design

**Date:** 2025-11-04
**Status:** Approved
**Replaces:** IBind library

## Overview

Build a lightweight custom IBKR Client Portal API client using OAuth 1.0a authentication to replace the IBind library dependency. The custom client provides better control, reduced complexity, and focuses only on the operations needed for the swing trading bot.

## Motivation

- **Proven OAuth flow:** Successfully tested OAuth 1.0a authentication with standalone script
- **Simple requirements:** Only need order management, position queries, and market data
- **Direct control:** No abstraction layer, direct access to IBKR API
- **Reduced dependencies:** Remove IBind library and its dependencies
- **Maintainability:** Full control over error handling and retry logic

## Scope

### In Scope
- OAuth 1.0a authentication with Live Session Token (LST)
- Order placement: Market, Stop Market, Stop Limit orders
- Order management: Query open orders, cancel orders
- Position queries: Get current positions from IBKR
- Account info: Get account ID and balance for position sizing
- Market data: Get current price snapshots
- Error handling with exponential backoff retry

### Out of Scope
- Historical data (using external data sources)
- Streaming/real-time data feeds
- Order modification (use cancel + replace)
- Complex order types (brackets, OCO, etc.)
- Multiple account management
- Historical fills/executions

## Architecture

### Component Structure

```
src/skim/brokers/
├── ib_interface.py     # Existing protocol (unchanged)
├── ibkr_oauth.py       # NEW: OAuth/LST generation
└── ibkr_client.py      # NEW: Main API client
```

### Data Flow

```
Bot Startup:
  connect() → generate_lst() → init_brokerage_session() → get_account_id()

Order Flow:
  place_order() → lookup_contract() → submit_order() → return OrderResult

Position Query:
  get_positions() → query IBKR API → return list[dict]

Market Data:
  get_market_data() → lookup_contract() → fetch_snapshot() → return MarketData
```

## Detailed Design

### 1. OAuth & Authentication (`ibkr_oauth.py`)

Extract OAuth logic from test script into reusable module.

**Key Function:**

```python
def generate_lst(
    consumer_key: str,
    access_token: str,
    access_token_secret: str,
    dh_prime_hex: str,
    signature_key_path: str,
    encryption_key_path: str
) -> tuple[str, int]:
    """Generate Live Session Token for IBKR API

    Steps:
    1. Load RSA keys (signature + encryption)
    2. Generate DH random value (256-bit)
    3. Calculate DH challenge: (2 ^ random) mod prime
    4. Decrypt access token secret (prepend)
    5. Build OAuth params and sign request
    6. POST to /oauth/live_session_token
    7. Compute final LST from response

    Returns:
        (lst_signature, expiration_timestamp)
    """
```

**Dependencies:**
- `pycryptodome` - RSA operations, SHA256, PKCS1
- `requests` - HTTP client
- Standard library: `base64`, `random`, `datetime`, `urllib.parse`

### 2. Main Client (`ibkr_client.py`)

**Class Structure:**

```python
class IBKRClient(IBInterface):
    """Custom IBKR Client Portal API client with OAuth"""

    def __init__(self, paper_trading: bool = True):
        self._lst: str | None = None
        self._lst_expiration: int | None = None
        self._account_id: str | None = None
        self._connected: bool = False
        self._paper_trading = paper_trading
        self._contract_cache: dict[str, str] = {}  # ticker -> conid

        # Load OAuth config from environment
        self._consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
        self._access_token = os.getenv("OAUTH_ACCESS_TOKEN")
        # ... etc
```

**Core Request Helper:**

```python
def _request(
    self,
    method: str,
    endpoint: str,
    data: dict | None = None,
    params: dict | None = None,
    max_retries: int = 5
) -> dict:
    """Make HTTP request with retry logic

    Retry Strategy:
    - Exponential backoff: 1s, 2s, 4s, 8s, 16s
    - Retry on: network errors, 500/502/503, 429 (rate limit)
    - Don't retry: 400 (bad request), 404 (not found)
    - Special: 401 → regenerate LST → retry once

    Headers:
    - Authorization: {lst}
    - User-Agent: skim-trading-bot/1.0
    - Content-Type: application/json

    Base URL: https://api.ibkr.com/v1/api
    """
```

### 3. API Operations

#### Connection & Session

```python
def connect(self, host: str, port: int, client_id: int, timeout: int = 20) -> None:
    """Establish authenticated session with IBKR

    Steps:
    1. Generate LST via OAuth flow
    2. POST /iserver/auth/ssodh/init - Initialize brokerage session
    3. GET /iserver/account - Get account ID
    4. Verify paper trading (account starts with 'DU')

    Raises:
        ValueError: If not paper trading account
        RuntimeError: If connection fails
    """

def is_connected(self) -> bool:
    """Check if session is still valid

    Simple check: self._connected and self._lst is not None
    (Will regenerate LST on 401 automatically)
    """
```

#### Order Management

```python
def place_order(
    self,
    ticker: str,
    action: str,  # "BUY" or "SELL"
    quantity: int,
    order_type: str = "MKT",
    limit_price: float | None = None,
    stop_price: float | None = None
) -> OrderResult | None:
    """Place order with flexible order types

    Order Types:
    - "MKT": Market order (immediate execution)
    - "STP": Stop market (triggers market order at stop_price)
    - "STP LMT": Stop limit (triggers limit at stop_price, fills at limit_price)

    Flow:
    1. Look up contract ID (conid) via _get_contract_id()
    2. Build order JSON based on order_type
    3. POST /iserver/account/{accountId}/orders
    4. Handle confirmation questions (auto-accept common ones)
    5. Return OrderResult with order_id and status

    Returns:
        OrderResult or None on failure
    """

def get_open_orders(self) -> list[dict]:
    """Query all open orders from IBKR

    Endpoint: GET /iserver/account/orders

    Returns list with:
    - order_id, ticker, quantity, order_type
    - status, limit_price, stop_price
    """

def cancel_order(self, order_id: str) -> bool:
    """Cancel specific order

    Endpoint: DELETE /iserver/account/{accountId}/order/{orderId}
    """
```

#### Position Queries

```python
def get_positions(self) -> list[dict]:
    """Get current positions from IBKR (source of truth)

    Endpoint: GET /portfolio/{accountId}/positions/0

    Returns list with:
    - ticker (symbol)
    - conid (contract ID)
    - position (quantity, negative = short)
    - avgPrice (average entry price)
    - mktPrice (current market price)
    - unrealizedPnL
    """

def get_account_balance(self) -> dict:
    """Get account balance for position sizing

    Endpoint: GET /portfolio/{accountId}/summary

    Returns:
    - availableFunds: Cash available
    - netLiquidation: Total account value
    - buyingPower: Margin buying power
    """
```

#### Market Data

```python
def get_market_data(self, ticker: str) -> MarketData | None:
    """Get current market snapshot

    Flow:
    1. Look up conid via _get_contract_id()
    2. GET /iserver/marketdata/snapshot?conids={conid}
    3. Parse fields: 31=last, 84=bid, 86=ask, 87=volume
    4. Return MarketData object
    """

def _get_contract_id(self, ticker: str) -> str:
    """Look up IBKR contract ID (conid) for ticker

    Endpoint: GET /iserver/secdef/search?symbol={ticker}

    Cache results in self._contract_cache to avoid repeated lookups
    Filter: secType="STK", exchange="ASX"
    """
```

### 4. Error Handling

**Retry Logic:**
- Initial delay: 1 second
- Exponential backoff multiplier: 2x
- Max retries: 5 (total ~31 seconds)
- Jitter: ±10% to avoid thundering herd

**Error Categories:**

| Error Type | Status Code | Action |
|------------|-------------|--------|
| Network error | N/A | Retry with backoff |
| Rate limit | 429 | Retry with backoff |
| Server error | 500, 502, 503 | Retry with backoff |
| Auth expired | 401 | Regenerate LST, retry once |
| Bad request | 400 | Log and raise (no retry) |
| Not found | 404 | Log and raise (no retry) |

**Logging:**
- DEBUG: All API requests/responses
- INFO: Authentication events, order placement
- WARNING: Retries, non-critical errors
- ERROR: Failed operations after all retries

### 5. Configuration

**Environment Variables (existing):**
```bash
OAUTH_CONSUMER_KEY=PSKIMMILK
OAUTH_ACCESS_TOKEN=dce0eabe3ee53c197f58
OAUTH_ACCESS_TOKEN_SECRET=<encrypted>
OAUTH_SIGNATURE_PATH=/opt/skim/oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_PATH=/opt/skim/oauth_keys/private_encryption.pem
OAUTH_DH_PRIME=<hex_string>
PAPER_TRADING=true
```

No new configuration needed - reuse existing OAuth setup.

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create `ibkr_oauth.py` with LST generation
2. Create `ibkr_client.py` skeleton with `_request()` helper
3. Implement `connect()` and session management
4. Test authentication against paper account

### Phase 2: Read Operations
1. Implement `get_account()` and account balance
2. Implement `get_positions()`
3. Implement `_get_contract_id()` with caching
4. Implement `get_market_data()`
5. Test queries against paper account

### Phase 3: Order Management
1. Implement `place_order()` with all order types
2. Implement `get_open_orders()`
3. Implement `cancel_order()`
4. Test order lifecycle (place → query → cancel)

### Phase 4: Integration
1. Update `src/skim/core/bot.py` to use `IBKRClient`
2. Remove `IBIndClient` import
3. Test full bot workflow with paper account
4. Remove IBind from `pyproject.toml`

### Phase 5: Cleanup
1. Delete `ibind_client.py`
2. Add test files to `.gitignore`:
   - `test_oauth_local.py`
   - `.venv_oauth_test/`
   - `OAUTH_TEST_RESULTS.md`
3. Update documentation

## Testing Strategy

**Approach:** Direct replacement testing (Option A from brainstorm)
- Replace IBind immediately
- Test against paper trading account
- Fast iteration, validate each endpoint

**Test Checklist:**
- [ ] Authentication: LST generation works
- [ ] Session: Brokerage session initializes
- [ ] Account: Can retrieve account ID and balances
- [ ] Positions: Can query open positions
- [ ] Market data: Can get price snapshots
- [ ] Orders: Can place market order
- [ ] Orders: Can place stop market order
- [ ] Orders: Can place stop limit order
- [ ] Orders: Can query open orders
- [ ] Orders: Can cancel order
- [ ] Retry: Network failures trigger retries
- [ ] Auth: 401 triggers LST regeneration

## Migration & Rollback

**Migration:**
1. Implement new client alongside existing code
2. Update bot.py import: `from .ibkr_client import IBKRClient`
3. Delete `ibind_client.py` immediately (clean break)
4. Remove IBind from dependencies

**No Rollback Plan:**
- Clean break from IBind (delete immediately)
- Test thoroughly against paper account before production
- Keep OAuth test script temporarily for debugging

## Dependencies

**New:**
- `pycryptodome` - Already installed for OAuth test
- `requests` - Already installed

**Removed:**
- `ibind` - Delete from pyproject.toml

## API Endpoints Reference

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get LST | POST | `/oauth/live_session_token` |
| Init session | POST | `/iserver/auth/ssodh/init` |
| Get account | GET | `/iserver/account` |
| Get balance | GET | `/portfolio/{accountId}/summary` |
| Get positions | GET | `/portfolio/{accountId}/positions/0` |
| Search contract | GET | `/iserver/secdef/search` |
| Place order | POST | `/iserver/account/{accountId}/orders` |
| Get orders | GET | `/iserver/account/orders` |
| Cancel order | DELETE | `/iserver/account/{accountId}/order/{orderId}` |
| Market snapshot | GET | `/iserver/marketdata/snapshot` |

## Success Criteria

- [ ] All `IBInterface` methods implemented
- [ ] Bot connects to paper account successfully
- [ ] Can place, query, and cancel orders
- [ ] Can query positions and balances
- [ ] Can retrieve market data
- [ ] Retry logic handles transient failures
- [ ] 401 errors trigger LST regeneration
- [ ] IBind dependency removed
- [ ] No credentials committed to git

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| OAuth complexity | Already proven working in test script |
| API changes | Use official IBKR docs, test thoroughly |
| Rate limits | Exponential backoff, swing trading = low frequency |
| Session expiration | Reactive 401 handling regenerates LST |
| Order errors | Paper trading mode, DU account verification |
| Missing features | Start with core operations, extend as needed |

## References

- [IBKR OAuth 1.0a Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/oauth-1-0a-extended/)
- [IBKR Client Portal API](https://www.interactivebrokers.com/api/doc.html)
- Working OAuth test script: `test_oauth_local.py`
- Test results: `OAUTH_TEST_RESULTS.md`

## Next Steps

After design approval:
1. Create isolated git worktree for implementation
2. Write detailed implementation plan with bite-sized tasks
3. Implement in phases (auth → reads → writes → integration)
4. Test against paper account at each phase
5. Remove IBind and test files
