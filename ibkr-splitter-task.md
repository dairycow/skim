# Agent Task: IBKRClient Splitter
## Phase: 1.1
## Priority: HIGH

### Objective
Split the monolithic `IBKRClient` (634 lines) into 4 focused classes:
1. `IBKRAuthManager` (~150 lines) - OAuth LST generation and validation
2. `IBKRConnectionManager` (~120 lines) - Connection lifecycle and keepalive
3. `IBKRRequestClient` (~200 lines) - HTTP requests with retry logic
4. `IBKRClientFacade` (~100 lines) - Lightweight facade

### Reference Files
- `src/skim/trading/brokers/ibkr_client.py` (current, 634 lines)
- `src/skim/trading/core/config.py` (Config definition)

### New File Structure
```
src/skim/infrastructure/brokers/ibkr/
├── __init__.py
├── auth.py           # IBKRAuthManager
├── connection.py     # IBKRConnectionManager
├── requests.py       # IBKRRequestClient
└── facade.py         # IBKRClientFacade (replaces ibkr_client.py)
```

### Tasks

#### 1. Create `auth.py` (IBKRAuthManager)
Extract from `ibkr_client.py` lines 322-348 and 624-633:
- `_generate_lst()` method
- `is_expiring()` method
- LST expiration timestamp handling
- OAuth signature key paths

**Extracted responsibilities:**
- OAuth LST generation via `generate_lst()`
- LST expiration checking
- OAuth key path management

#### 2. Create `connection.py` (IBKRConnectionManager)
Extract from `ibkr_client.py` lines 174-297 and 382-419:
- `connect()` method (session initialization)
- `disconnect()` method
- `is_connected()` property
- `get_account()` method
- Keepalive thread (`_start_tickle_thread()`, `_stop_tickle_thread()`, `_tickle_worker()`)

**Extracted responsibilities:**
- Session lifecycle management
- Keepalive thread management
- Account ID retrieval

#### 3. Create `requests.py` (IBKRRequestClient)
Extract from `ibkr_client.py` lines 423-604:
- `request()` method (main HTTP method)
- `_build_oauth_signature()` method (lines 467-502)
- `_handle_retryable_error()` method
- Error handling for 401/410 with LST regeneration
- Exponential backoff retry logic

**Extracted responsibilities:**
- HTTP request execution
- OAuth signature building
- Retry logic
- Error handling

#### 4. Create `facade.py` (IBKRClientFacade)
Create lightweight facade that delegates to the 3 components:
- Constructor takes auth, connection, request_client
- Maintains backward-compatible interface
- Methods: `connect()`, `disconnect()`, `is_connected()`, `get_account()`, `get()`, `post()`

#### 5. Update Imports
Update imports in:
- `src/skim/trading/core/bot.py`
- `src/skim/trading/brokers/ibkr_orders.py`
- `src/skim/trading/brokers/ibkr_market_data.py`
- `src/skim/trading/brokers/ibkr_gap_scanner.py`

#### 6. Update Tests
- `tests/trading/test_ibkr_client.py` - Split into tests for each component
- Mock IBKRAuthManager, IBKRConnectionManager, IBKRRequestClient separately

### Dependencies
- Import `Config` from `skim.trading.core.config`
- Import `IBKRAuthenticationError`, `IBKRConnectionError`, `IBKRClientError` from appropriate location

### Acceptance Criteria
- [ ] `ibkr_client.py` removed or replaced by `facade.py`
- [ ] New files total ~570 lines (down from 634)
- [ ] No class > 250 lines
- [ ] All existing tests pass
- [ ] No functionality lost
- [ ] Backward-compatible interface maintained

### Notes
- Keep exception classes (`IBKRClientError`, `IBKRAuthenticationError`, `IBKRConnectionError`) in a common location
- Update `__init__.py` to export all public classes
- Consider moving exceptions to `shared/exceptions.py`

### Steps to Complete
1. Read and understand `ibkr_client.py` completely
2. Create the 4 new files with extracted code
3. Create facade that wires them together
4. Update all import statements
5. Run tests to verify
6. Commit with message: `refactor(ibkr): split monolithic IBKRClient into focused classes`
