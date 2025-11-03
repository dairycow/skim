# IBeam + IBind Migration Design

**Date:** 2025-11-03
**Status:** Approved for Implementation
**Goal:** Replace TWS Gateway + ib-insync with IBeam + IBind for better reliability and maintenance

## Problem Statement

Current setup using `ghcr.io/gnzsnz/ib-gateway` is broken:
- IB Gateway container failing with "Offline TWS/Gateway version 10.40.1c is not installed"
- Deployment complexity with Java-based Gateway
- Maintenance burden (manual 2FA, 24-hour restarts)
- Resource usage from heavy Gateway container

## Solution: IBeam + IBind

Migrate to modern REST-based Client Portal API using:
- **IBeam**: Docker container that manages Client Portal Gateway authentication
- **IBind**: Python client library for Client Portal REST + WebSocket APIs

## Architecture Comparison

### Before (Current - Broken)
```
Skim Bot → ib-insync → IB Gateway (Java) → IBKR Servers
                        (gnzsnz container - broken)
```

### After (Proposed)
```
Skim Bot → IBind → Client Portal Gateway → IBKR Servers
                    (managed by IBeam)
```

## Key Benefits

✅ **Deployment Complexity:** Active maintained image (`voyz/ibeam`), automated auth
✅ **Maintenance Burden:** Auto-reconnection, no 24h restart, handles 2FA
✅ **Modern API:** REST/HTTP instead of socket protocol
✅ **Better Rate Limits:** 50 req/sec vs 10 req/sec through Gateway
✅ **Cleaner Abstraction:** Our `IBInterface` protocol stays, just new implementation

## Trade-offs Accepted

⚠️ **Still requires Java:** Client Portal Gateway is Java-based (lighter than TWS Gateway)
⚠️ **Chrome/Selenium:** IBeam uses Chrome for auth automation (adds container weight)
⚠️ **Less Mature Library:** IBind v0.1.18 vs ib-insync (battle-tested since 2016)
⚠️ **Manual 2FA:** Weekly phone approval on IBKR Mobile (acceptable for pre-production)

## Authentication Flow

1. IBeam starts Client Portal Gateway
2. Selenium automates login (username/password entry)
3. IBKR sends push notification to phone
4. **User manually approves on IBKR Mobile** (~weekly)
5. IBeam maintains session automatically
6. Session persists ~1 week before re-auth

**2FA Method:** `EXTERNAL_REQUEST` - Manual phone approval
**Future Option:** Switch to SMS or challenge-response for full automation

## Implementation Plan

### Phase 1: Docker Infrastructure

**Update `docker-compose.yml`:**
```yaml
services:
  ibeam:
    image: voyz/ibeam:latest
    container_name: ibeam
    restart: unless-stopped
    network_mode: bridge  # Required for IP whitelist
    environment:
      - IBEAM_ACCOUNT=${IB_USERNAME}
      - IBEAM_PASSWORD=${IB_PASSWORD}
      - IBEAM_TWO_FA_HANDLER=EXTERNAL_REQUEST
      - IBEAM_GATEWAY_BASE_URL=https://localhost:5000
    ports:
      - "5000:5000"  # Client Portal API
    volumes:
      - ibeam-data:/srv/ibeam

  bot:
    # ... existing config
    depends_on:
      - ibeam  # Replace ibgateway
    environment:
      - IB_HOST=ibeam
      - IB_PORT=5000
      # ... rest of config

volumes:
  ibeam-data:
```

**Update `.env.example`:**
```bash
# Interactive Brokers Configuration
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password
IB_HOST=ibeam
IB_PORT=5000
IB_CLIENT_ID=1
PAPER_TRADING=true
```

### Phase 2: Broker Client

**Delete:** `src/skim/brokers/ib_client.py` (ib-insync implementation)

**Create:** `src/skim/brokers/ibind_client.py`

```python
"""Interactive Brokers client using IBind (Client Portal API)"""

from ibind import IbkrClient
from loguru import logger

from .ib_interface import IBInterface, MarketData


class IBIndClient(IBInterface):
    """IB client implementation using IBind for Client Portal API"""

    def __init__(self, base_url: str = "https://localhost:5000", paper_trading: bool = True):
        self.client = IbkrClient(url=base_url)
        self.paper_trading = paper_trading
        self._connected = False

    def connect(self, host: str, port: int, client_id: int, timeout: int = 20) -> None:
        """Connect to Client Portal API via IBeam

        Note: Client Portal API uses session-based auth managed by IBeam,
        so traditional connect() is primarily a health check.
        """
        # Check if gateway is authenticated
        health = self.client.check_health()
        if not health.ok:
            raise RuntimeError(f"Client Portal not healthy: {health.data}")

        # Tickle to verify session
        tickle = self.client.tickle()
        if not tickle.ok:
            raise RuntimeError("Session not authenticated")

        # Verify paper trading account
        accounts = self.client.portfolio_accounts()
        if not accounts.ok or not accounts.data:
            raise RuntimeError("No accounts available")

        account = accounts.data[0]['accountId']
        logger.info(f"Connected to account: {account}")

        if self.paper_trading and not account.startswith('DU'):
            raise ValueError("SAFETY CHECK FAILED: Not a paper trading account!")

        self._connected = True
        logger.info("Client Portal connection established")

    def is_connected(self) -> bool:
        """Check if connected to Client Portal"""
        if not self._connected:
            return False
        # Verify session is still valid
        tickle = self.client.tickle()
        return tickle.ok

    def place_order(self, ticker: str, action: str, quantity: int) -> int:
        """Place market order via Client Portal API"""
        # Implementation using ibind order placement
        # ... (to be implemented with full error handling)
        pass

    def get_market_data(self, ticker: str) -> MarketData:
        """Get current market data for ticker"""
        # Implementation using ibind market data endpoints
        # ... (to be implemented)
        pass

    def disconnect(self) -> None:
        """Disconnect from Client Portal"""
        self._connected = False
        logger.info("Disconnected from Client Portal")

    def get_account(self) -> str:
        """Get connected account ID"""
        accounts = self.client.portfolio_accounts()
        if accounts.ok and accounts.data:
            return accounts.data[0]['accountId']
        raise RuntimeError("No account available")
```

**Update:** `src/skim/brokers/__init__.py`
```python
"""Broker integrations (Interactive Brokers)"""

from .ibind_client import IBIndClient
from .ib_interface import IBInterface, MarketData

__all__ = ["IBIndClient", "IBInterface", "MarketData"]
```

### Phase 3: Dependencies

**Update `pyproject.toml`:**
```toml
dependencies = [
    "beautifulsoup4==4.12.3",
    "ibind>=0.1.18",  # Changed from ib-insync
    "loguru==0.7.2",
    "lxml==5.1.0",
    "python-dotenv==1.0.1",
    "requests==2.31.0",
    "pytz==2024.1",
]
```

### Phase 4: Configuration

**Update `src/skim/core/config.py`:**
```python
# Change defaults
IB_HOST: str = os.getenv("IB_HOST", "ibeam")  # Changed from "ibgateway"
IB_PORT: int = int(os.getenv("IB_PORT", "5000"))  # Changed from 4004
```

### Phase 5: Testing

**Create:** `tests/unit/test_ibind_client.py`
```python
"""Unit tests for IBind client"""

import pytest
from unittest.mock import Mock, MagicMock

def test_ibind_connect_success(mocker):
    """Test successful connection to Client Portal"""
    mock_client = mocker.patch('skim.brokers.ibind_client.IbkrClient')
    # ... mock health check, tickle, accounts
    # ... test connection success

def test_ibind_paper_trading_check(mocker):
    """Test paper trading safety validation"""
    # ... test DU prefix check
```

**Update `tests/conftest.py`:**
```python
@pytest.fixture
def mock_ibind_client(mocker):
    """Mock IBind client for testing"""
    mock = mocker.patch('ibind.IbkrClient')
    # Configure mock responses
    return mock
```

### Phase 6: Core Integration

**Update `src/skim/core/bot.py`:**
```python
from skim.brokers import IBIndClient  # Changed from IBClient

# In __init__:
self.ib_client = IBIndClient(
    base_url=f"https://{config.ib_host}:{config.ib_port}",
    paper_trading=config.paper_trading
)
```

## Migration Steps

1. ✅ Document design (this file)
2. ⏳ Update docker-compose.yml with ibeam service
3. ⏳ Update .env.example
4. ⏳ Create ibind_client.py
5. ⏳ Delete ib_client.py
6. ⏳ Update dependencies
7. ⏳ Update config.py
8. ⏳ Update bot.py
9. ⏳ Write tests
10. ⏳ Test Docker build
11. ⏳ Deploy and verify authentication flow
12. ⏳ Update README with new setup instructions

## Rollback Plan

**Not needed** - Pre-production system, no live trading to interrupt.

If migration fails, can revert commits and use old IB Gateway setup.

## Success Criteria

✅ IBeam container starts and reaches authentication prompt
✅ Manual phone approval completes authentication
✅ IBind client connects successfully
✅ Market data retrieval works
✅ Order placement works (paper trading)
✅ Session persists for ~1 week
✅ All unit tests pass
✅ Docker build succeeds

## Future Enhancements

1. **Full 2FA Automation:** Switch to SMS or challenge-response handler
2. **WebSocket Integration:** Use `IbkrWsClient` for real-time streaming
3. **Rate Limit Optimization:** Implement request batching for 50 req/sec limit
4. **Session Monitoring:** Add health checks and auto-reconnection

## References

- IBeam: https://github.com/Voyz/ibeam
- IBind: https://github.com/Voyz/ibind
- IBKR Web API Docs: https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-doc/

---

**Design approved:** Ready for implementation
**Implementation started:** 2025-11-03
