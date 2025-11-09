# Feature Request: IBKR Web API Gap Scanner with Opening Range Breakout Filter

## Overview
Implement a new IBKR Web API-based scanner that identifies ASX stocks with gap-ups that hold and break above their 10-minute opening range high. This leverages the existing OAuth-based IBKR Web API integration and follows established patterns in the codebase.

## Context
- **Market**: ASX (Australian Securities Exchange)
- **Strategy**: Gap-up stocks that maintain the gap and break 10-minute opening range highs (filtering out failed gaps)
- **Market Structure**: ASX opens all stocks simultaneously at 09:59:00 ±15 seconds (OSPA) as of May 12, 2025 (Service Release 15)
- **Normal Trading**: Begins 09:59:45-10:00:00
- **Timezone**: Australia/Sydney (AEDT/AEST)
- **API**: IBKR Client Portal Web API (OAuth-based, direct to api.ibkr.com, not local Gateway)

## Requirements

### Functional Requirements

1. **Authentication & Connection**
   - Extend existing IBKRClient OAuth authentication (api.ibkr.com)
   - Leverage existing session management and keepalive (tickle thread)
   - Use existing retry logic and error handling patterns
   - Health check via existing is_connected() method

2. **Initial Gap Scan (10:00:30 Sydney time)**
   - Scan ASX stocks using `/iserver/scanner/run` endpoint
   - Filter criteria:
     - Minimum 2% price change from previous close
     - Minimum volume: 50,000 shares
     - Minimum price: $0.50 (exclude penny stocks)
     - Maximum results: 50 stocks
   - Return list of candidate stock contracts (conid + symbol)

3. **Market Data Enrichment**
   - For each candidate, fetch real-time market data via existing `get_market_data()` method
   - Extend field mapping to include:
     - Field 31: Last price (already implemented)
     - Field 70: Change % from close (corrected from 84)
     - Field 86: Previous close price (already implemented as ask fallback)
     - Field 88: Today's open price
     - Field 7295: Volume (corrected from 87)
   - Leverage existing rate limiting and retry logic
   - Use existing contract ID caching for efficiency

4. **Opening Range Tracking (10:00:00 - 10:10:00)**
   - Track high and low prices during 10-minute window
   - Poll market data every 30 seconds for each candidate
   - Store:
     - Opening Range High (OR_High)
     - Opening Range Low (OR_Low)
     - Current price updates
   - Continue tracking even if some stocks become inactive

5. **Failed Gap Detection & Filtering (10:10:00)**
   - Calculate gap percentage: `(open - prev_close) / prev_close * 100`
   - Identify "gap holding" patterns:
     - Gap >= 2%
     - OR_Low >= prev_close * 0.99 (gap hasn't filled - 1% tolerance)
     - Current price >= OR_High * 1.001 (breaking OR high with 0.1% buffer)
   - Return filtered list of breakout candidates

6. **Output/Integration**
   - Create new GapStock dataclass for gap scanning results
   - Extend existing Candidate database model with OR tracking fields
   - Integrate with existing TradingBot workflow
   - Use existing structured logging patterns
   - Store results to existing SQLite database for backtesting

### Non-Functional Requirements

1. **Testing**
   - Unit tests for each component (scan, enrich, track, filter)
   - Integration tests with mocked IBKR API responses
   - Mock data for offline testing/development
   - Test edge cases: no gaps, all gaps filled, API failures

2. **Error Handling**
   - Graceful degradation if API is unavailable
   - Handle partial data (some stocks fail to fetch)
   - Timeout handling for long-running requests
   - Clear error messages with context

3. **Configuration**
   - Extend existing Config class with scanner parameters:
     - scanner_volume_filter: int = 50000
     - scanner_price_filter: float = 0.50
     - or_duration_minutes: int = 10
     - or_poll_interval_seconds: int = 30
     - gap_fill_tolerance: float = 1.0
     - or_breakout_buffer: float = 0.1
   - Leverage existing environment variable pattern
   - Use existing OAuth configuration (already externalized)

4. **Observability**
   - Structured logging (timestamp, stage, message, data)
   - Performance metrics (scan duration, number of candidates, etc.)
   - Debug mode for verbose output

## Technical Specifications

### IBKR Web API Endpoints
```
Base URL: https://api.ibkr.com/v1/api (existing OAuth implementation)

Authentication:
- Existing OAuth 1.0a flow with LST generation (already implemented)
- Existing session management with tickle keepalive

Scanner (NEW - to be added to IBKRClient):
- POST /iserver/scanner/params (get available parameters)
- POST /iserver/scanner/run (execute scan)

Market Data:
- GET /iserver/marketdata/snapshot?conids={conid} (already implemented)
- Extend field mapping for additional OR tracking fields

Session:
- POST /tickle (already implemented in keepalive thread)
```

### Scanner Parameters Structure
```json
{
  "instrument": "STK",
  "locations": "STK.ASX",
  "scanCode": "TOP_PERC_GAIN",
  "filters": [
    {"code": "changePercAbove", "value": 2.0},
    {"code": "volumeAbove", "value": 50000},
    {"code": "priceAbove", "value": 0.50}
  ]
}
```

### Data Models
```python
# New GapStock dataclass for IBKR gap scanning results
class GapStock(NamedTuple):
    """Stock with gap data from IBKR scanner"""
    ticker: str
    gap_percent: float
    close_price: float
    conid: int

# Extend existing Candidate database model
ALTER TABLE candidates ADD COLUMN or_high REAL;
ALTER TABLE candidates ADD COLUMN or_low REAL;
ALTER TABLE candidates ADD COLUMN or_timestamp DATETIME;
ALTER TABLE candidates ADD COLUMN conid INTEGER;

# New dataclass for OR tracking
@dataclass
class OpeningRangeData:
    ticker: str
    conid: int
    or_high: float
    or_low: float
    open_price: float
    prev_close: float
    current_price: float
    gap_holding: bool
    
@dataclass
class BreakoutSignal:
    ticker: str
    conid: int
    gap_pct: float
    or_high: float
    or_low: float
    or_size_pct: float
    current_price: float
    entry_signal: str  # "ORB_HIGH_BREAKOUT"
    timestamp: datetime
```

### Schedule/Orchestration

#### Current Cron Setup (UTC times)
```bash
# Scan for candidates after opening auction
37 23 * * 0-4  # 23:37 UTC = 10:37 AM AEDT

# Monitor for gaps and entry triggers  
42 23 * * 0-4  # 23:42 UTC = 10:42 AM AEDT

# Execute triggered orders
47 23 * * 0-4  # 23:47 UTC = 10:47 AM AEDT
```

#### New IBKR ORH-Based Schedule
```python
# Main execution flow (Sydney time)
09:50:00 - Pre-flight checks (API connection, auth)
10:00:30 - Execute IBKR gap scan
10:00:35 - Enrich candidates with market data
10:00:40 - Begin OR tracking loop (10-minute window)
10:02:40 - OR update #1 (2 min)
10:04:40 - OR update #2 (4 min) 
10:06:40 - OR update #3 (6 min)
10:08:40 - OR update #4 (8 min)
10:10:30 - Execute failed gap filter & ORH breakout detection
10:10:35 - Return breakout signals for entry
```

#### Cron Job Updates Required
```bash
# Replace existing cron entries with ORH-based schedule:

# IBKR gap scan (10:00:30 AEDT = 00:00:30 UTC)
30 0 * * 1-5 cd /app && /usr/local/bin/python -m skim.core.bot scan_ibkr >> /var/log/cron.log 2>&1

# OR tracking and breakout detection (10:10:30 AEDT = 00:10:30 UTC)  
30 0 * * 1-5 cd /app && /usr/local/bin/python -m skim.core.bot track_or_breakouts >> /var/log/cron.log 2>&1

# Execute ORH breakout orders (10:12:00 AEDT = 00:12:00 UTC)
0 1 * * 1-5 cd /app && /usr/local/bin/python -m skim.core.bot execute_orh_breakouts >> /var/log/cron.log 2>&1

# Keep existing position management
*/5 0,1,2,3,4,5 * * 1-5 cd /app && /usr/local/bin/python -m skim.core.bot manage_positions >> /var/log/cron.log 2>&1
```

## Implementation Notes

### TDD Example: Extending IBKRClient

#### Step 1: RED - Write Failing Test
```python
# tests/unit/brokers/test_ibkr_scanner.py
def test_run_scanner_returns_gap_candidates():
    """Test scanner returns gap candidates with expected structure"""
    # Setup
    client = IBKRClient(paper_trading=True)
    scan_params = {
        "instrument": "STK",
        "locations": "STK.ASX",
        "scanCode": "TOP_PERC_GAIN",
        "filters": [
            {"code": "changePercAbove", "value": 2.0},
            {"code": "volumeAbove", "value": 50000},
        ]
    }
    
    # Mock response
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            f"{IBKRClient.BASE_URL}/iserver/scanner/run",
            json={"contracts": [
                {"conid": 8724, "symbol": "BHP", "description": "BHP GROUP LTD"},
                {"conid": 8733, "symbol": "CBA", "description": "COMMONWEALTH BANK"},
            ]},
            status=200
        )
        
        # Execute
        result = client.run_scanner(scan_params)
        
        # Verify
        assert len(result) == 2
        assert result[0]["conid"] == 8724
        assert result[0]["symbol"] == "BHP"
```

#### Step 2: GREEN - Minimal Implementation
```python
# src/skim/brokers/ibkr_client.py
def run_scanner(self, scan_params: dict) -> list[dict]:
    """Execute IBKR scanner with gap criteria"""
    endpoint = "/iserver/scanner/run"
    response = self._request("POST", endpoint, data=scan_params)
    return response.get("contracts", [])
```

#### Step 3: REFACTOR - Improve Implementation
```python
# src/skim/brokers/ibkr_client.py
def run_scanner(self, scan_params: dict) -> list[dict]:
    """Execute IBKR scanner with gap criteria
    
    Args:
        scan_params: Scanner parameters following IBKR API format
        
    Returns:
        List of contract dictionaries with conid, symbol, description
        
    Raises:
        RuntimeError: If scanner request fails
    """
    logger.info(f"Running IBKR scanner with params: {scan_params}")
    
    endpoint = "/iserver/scanner/run"
    try:
        response = self._request("POST", endpoint, data=scan_params)
        contracts = response.get("contracts", [])
        
        logger.info(f"Scanner returned {len(contracts)} contracts")
        return contracts
        
    except Exception as e:
        logger.error(f"Scanner request failed: {e}")
        raise RuntimeError(f"Failed to run scanner: {e}") from e

def get_scanner_params(self) -> dict:
    """Get available scanner parameters"""
    endpoint = "/iserver/scanner/params"
    return self._request("POST", endpoint)

def get_market_data_extended(self, conid: str) -> dict:
    """Extended market data with OR tracking fields"""
    endpoint = "/iserver/marketdata/snapshot"
    params = {"conids": conid, "fields": "31,70,86,88,7295"}
    response = self._request("GET", endpoint, params=params)
    return response[0] if response else {}
```

#### Step 4: Verify All Tests Pass
```bash
uv run pytest tests/unit/brokers/test_ibkr_scanner.py -v
uv run pytest --cov=skim.brokers.ibkr_client
```

This TDD cycle repeats for every feature in the implementation.

### New Scanner Class
```python
# Create src/skim/scanners/ibkr_gap_scanner.py:
class IBKRGapScanner:
    """IBKR Web API gap scanner with opening range breakout filter"""
    
    def __init__(self, ib_client: IBKRClient, config: Config):
        self.ib_client = ib_client
        self.config = config
        
    def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Scan for ASX stocks with gaps above threshold"""
        
    def track_opening_range(self, candidates: list[GapStock]) -> list[OpeningRangeData]:
        """Track OR high/low for configured duration"""
        
    def filter_breakouts(self, or_data: list[OpeningRangeData]) -> list[BreakoutSignal]:
        """Identify ORB breakouts with gap holding"""
```

### Database Migration
```sql
-- Extend existing candidates table:
ALTER TABLE candidates ADD COLUMN or_high REAL;
ALTER TABLE candidates ADD COLUMN or_low REAL;
ALTER TABLE candidates ADD COLUMN or_timestamp DATETIME;
ALTER TABLE candidates ADD COLUMN conid INTEGER;
ALTER TABLE candidates ADD COLUMN source TEXT DEFAULT 'ibkr';
```

### Configuration Extension
```python
# Extend src/skim/core/config.py:
@dataclass
class Config:
    # Existing fields...
    
    # IBKR Scanner settings
    scanner_volume_filter: int = 50000
    scanner_price_filter: float = 0.50
    or_duration_minutes: int = 10
    or_poll_interval_seconds: int = 30
    gap_fill_tolerance: float = 1.0
    or_breakout_buffer: float = 0.1
    
    @classmethod
    def from_env(cls) -> "Config":
        # Existing code...
        config = cls(
            # Existing parameters...
            scanner_volume_filter=int(os.getenv("SCANNER_VOLUME_FILTER", "50000")),
            scanner_price_filter=float(os.getenv("SCANNER_PRICE_FILTER", "0.50")),
            or_duration_minutes=int(os.getenv("OR_DURATION_MINUTES", "10")),
            or_poll_interval_seconds=int(os.getenv("OR_POLL_INTERVAL_SECONDS", "30")),
            gap_fill_tolerance=float(os.getenv("GAP_FILL_TOLERANCE", "1.0")),
            or_breakout_buffer=float(os.getenv("OR_BREAKOUT_BUFFER", "0.1")),
        )
```

### Bot Integration
```python
# Update src/skim/core/bot.py:
class TradingBot:
    def __init__(self, config: Config):
        # Existing initialization...
        # Remove: self.tv_scanner = TradingViewScanner()
        self.ibkr_scanner = IBKRGapScanner(self.ib_client, config)
        
    def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Replace TradingView scan with IBKR scan"""
        # Remove: return self.tv_scanner.scan_for_gaps(min_gap)
        return self.ibkr_scanner.scan_for_gaps(min_gap)
        
    def scan_ibkr_gaps(self) -> int:
        """Execute IBKR gap scan and store candidates for OR tracking"""
        # Phase 1: Initial gap scan
        gap_candidates = self.ibkr_scanner.scan_for_gaps(self.config.gap_threshold)
        
        # Store candidates with OR tracking fields
        candidates_created = 0
        for stock in gap_candidates:
            # Check if already exists
            existing = self.db.get_candidate(stock.ticker)
            if not existing or existing.status != "or_tracking":
                candidate = Candidate(
                    ticker=stock.ticker,
                    headline=f"IBKR gap detected: {stock.gap_percent:.2f}%",
                    scan_date=datetime.now().isoformat(),
                    status="or_tracking",  # New status for OR tracking
                    gap_percent=stock.gap_percent,
                    prev_close=stock.close_price,
                    conid=stock.conid,  # New field
                )
                self.db.save_candidate(candidate)
                candidates_created += 1
                
        return candidates_created
        
    def track_or_breakouts(self) -> int:
        """Track opening range and detect ORH breakouts"""
        # Get candidates in OR tracking status
        candidates = self.db.get_or_tracking_candidates()
        
        if not candidates:
            logger.info("No candidates for OR tracking")
            return 0
            
        # Phase 2: Track opening range for remaining candidates
        gap_stocks = [GapStock(c.ticker, c.gap_percent, c.prev_close, c.conid) 
                     for c in candidates]
        or_data = self.ibkr_scanner.track_opening_range(gap_stocks)
        
        # Phase 3: Filter breakouts
        breakouts = self.ibkr_scanner.filter_breakouts(or_data)
        
        # Update candidates with OR data and breakout status
        breakout_count = 0
        for breakout in breakouts:
            # Update candidate with OR data
            self.db.update_candidate_or_data(
                breakout.ticker,
                or_high=breakout.or_high,
                or_low=breakout.or_low,
                or_timestamp=breakout.timestamp.isoformat()
            )
            
            # Mark as breakout triggered
            self.db.update_candidate_status(breakout.ticker, "orh_breakout")
            breakout_count += 1
            
        logger.info(f"OR tracking complete: {breakout_count} ORH breakouts detected")
        return breakout_count
        
    def execute_orh_breakouts(self) -> int:
        """Execute orders for ORH breakout candidates"""
        # Get ORH breakout candidates
        candidates = self.db.get_orh_breakout_candidates()
        
        if not candidates:
            logger.info("No ORH breakout candidates to execute")
            return 0
            
        # Execute similar to current execute() method but for ORH breakouts
        return self._execute_breakout_orders(candidates, "ORH Breakout")
```

### Remove TradingView References
```python
# Update src/skim/scanners/__init__.py:
"""Market scanners (ASX announcements, IBKR gaps)"""

# Update src/skim/strategy/entry.py:
# Remove TradingView references, update docstring:
"""Entry strategy combining IBKR gaps with ASX announcements"""

# Remove src/skim/scanners/tradingview.py entirely
```

### Database Schema Updates
```sql
-- Extend candidates table for OR tracking
ALTER TABLE candidates ADD COLUMN or_high REAL;
ALTER TABLE candidates ADD COLUMN or_low REAL;
ALTER TABLE candidates ADD COLUMN or_timestamp DATETIME;
ALTER TABLE candidates ADD COLUMN conid INTEGER;
ALTER TABLE candidates ADD COLUMN source TEXT DEFAULT 'ibkr';

-- New status values needed
-- Existing: watching, triggered, entered, half_exited
-- New: or_tracking, orh_breakout
```

### Database Method Updates
```python
# Add to src/skim/data/database.py:
def get_or_tracking_candidates(self) -> list[Candidate]:
    """Get candidates in OR tracking status"""
    
def get_orh_breakout_candidates(self) -> list[Candidate]:
    """Get candidates with ORH breakout signals"""
    
def update_candidate_or_data(self, ticker: str, or_high: float, 
                          or_low: float, or_timestamp: str) -> None:
    """Update candidate with opening range data"""
```

### Previous Close Data
Since Web API doesn't provide historical bars easily, implement one of:
1. **Option A**: Store previous day's closing prices locally (run EOD job at 4:12pm)
2. **Option B**: Use field 86 (previous close) from market data snapshot
3. **Recommended**: Use field 86 first, fallback to stored data if unavailable

### ASX-Specific Considerations
- **OSPA (Opening Single Price Auction)**: Randomized between 09:59:00-09:59:15
- **OSPA Levelling Period**: 09:59:15-09:59:45 (message buffering)
- **Normal Trading Start**: 09:59:45-10:00:00
- **Location Code**: "STK.ASX" for ASX stocks
- **Timezone Handling**: Critical for scheduling - use `pytz` with 'Australia/Sydney'

### Rate Limiting Strategy
- Scanner: 1 request per session (don't spam)
- Market data: Leverage existing retry logic with exponential backoff
- Keep-alive: Existing tickle thread every 60 seconds (already implemented)
- Contract caching: Use existing ticker → conid cache to reduce API calls

### Web API Limitations
- REST-based (polling, not streaming like TWS API)
- Higher latency than TWS API (~1-2 seconds per request)
- Rate limits are undocumented but conservative
- OAuth-based authentication (no SSL certificate issues with localhost)

## Test-Driven Development Strategy

### TDD Cycle: RED -> GREEN -> REFACTOR

This implementation MUST follow the TDD cycle as defined in AGENTS.md:

#### RED Phase: Write Failing Tests
1. **Start with failing tests for each component**
2. **Tests define the expected behavior and interface**
3. **All tests must fail initially (RED state)**

#### GREEN Phase: Make Tests Pass
1. **Write minimal code to make tests pass**
2. **No extra functionality beyond what tests require**
3. **All tests must pass (GREEN state)**

#### REFACTOR Phase: Improve Code
1. **Refactor while keeping tests green**
2. **Improve code quality, remove duplication**
3. **Maintain test coverage and functionality**

### Test Implementation Order (TDD Approach)

#### Phase 1: IBKRClient Extension (RED -> GREEN -> REFACTOR)
```python
# RED: Write failing tests first
def test_ibkr_scanner_params():
    """Test getting scanner parameters"""
    
def test_ibkr_scanner_run():
    """Test executing scanner with gap criteria"""
    
def test_get_market_data_extended():
    """Test extended market data with OR fields"""

# GREEN: Implement minimal methods in IBKRClient
# REFACTOR: Improve error handling, field mapping, caching
```

#### Phase 2: IBKRGapScanner Core Logic (RED -> GREEN -> REFACTOR)
```python
# RED: Write failing tests for core functionality
def test_scan_for_gaps():
    """Test gap scanning returns GapStock objects"""
    
def test_track_opening_range():
    """Test OR high/low tracking over time"""
    
def test_filter_breakouts():
    """Test breakout detection logic"""

# GREEN: Implement minimal scanner logic
# REFACTOR: Optimize performance, improve logging
```

#### Phase 3: Data Models & Database (RED -> GREEN -> REFACTOR)
```python
# RED: Write failing tests for data persistence
def test_candidate_model_extension():
    """Test new OR tracking fields"""
    
def test_opening_range_data_model():
    """Test OpeningRangeData dataclass"""
    
def test_breakout_signal_model():
    """Test BreakoutSignal dataclass"""

# GREEN: Implement database migration and models
# REFACTOR: Add validation, improve queries
```

#### Phase 4: Integration & Workflow (RED -> GREEN -> REFACTOR)
```python
# RED: Write failing integration tests
def test_full_ibkr_scan_workflow():
    """Test end-to-end scanning workflow"""
    
def test_bot_integration():
    """Test TradingBot integration"""
    
def test_error_recovery_integration():
    """Test graceful error handling"""

# GREEN: Implement integration points
# REFACTOR: Improve error handling, add monitoring
```

### Test Structure Requirements

#### Unit Tests (tests/unit/)
- **Location**: `tests/unit/brokers/test_ibkr_scanner.py`
- **Mocking**: Use `responses` library for HTTP mocking
- **Fixtures**: Leverage existing IBKR response fixtures
- **Coverage**: Each function must have dedicated tests

#### Integration Tests (tests/integration/)
- **Location**: `tests/integration/test_ibkr_gap_scanner.py`
- **Database**: Use in-memory SQLite for testing
- **Time Simulation**: Mock time progression for OR tracking
- **End-to-End**: Test complete workflow with mocked API

#### Mock Data Requirements
```python
# Add to tests/fixtures/ibkr_responses/:
# - scanner_params.json (scanner parameter response)
# - scanner_run_response.json (gap candidates)
# - market_data_extended_fields.json (OR tracking fields)
# - scanner_empty_response.json (no gaps found)
# - scanner_error_response.json (API error handling)

# Time-based mock data for OR tracking:
# - or_updates_1min.json (1 minute into tracking)
# - or_updates_5min.json (5 minutes into tracking)
# - or_updates_10min.json (complete OR data)
```

### TDD Implementation Checklist

#### Before Writing Any Production Code:
- [ ] Write failing test for the specific functionality
- [ ] Verify test fails with clear error message
- [ ] Run test suite to ensure RED state

#### After Writing Production Code:
- [ ] Run test suite to ensure GREEN state
- [ ] Verify all tests pass, no regressions
- [ ] Check test coverage remains >90%

#### Before Moving to Next Feature:
- [ ] Refactor code while keeping tests green
- [ ] Remove duplication, improve naming
- [ ] Ensure code follows existing patterns
- [ ] Run pre-commit hooks and linting

### Quality Assurance

#### Pre-commit Hooks (Already Configured)
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Test execution

#### Test Coverage Requirements
- **Minimum**: 90% line coverage
- **Target**: 95% line coverage for new code
- **Branch Coverage**: All decision paths tested

#### Continuous Integration
- **uv**: Use unified toolchain for dependency management
- **pytest**: Run tests with `uv run pytest`
- **Coverage**: Generate reports with `uv run pytest --cov`

### Australian English Requirements
- **Colour**: Use "colour" not "color"
- **Centre**: Use "centre" not "center"  
- **Behaviour**: Use "behaviour" not "behavior"
- **Analyse**: Use "analyse" not "analyze"
- **Organisation**: Use "organisation" not "organization"

## Acceptance Criteria (TDD-Driven)

### Test-Driven Requirements
1. ✅ **RED Phase**: All tests written first and fail initially
2. ✅ **GREEN Phase**: Minimal implementation makes all tests pass
3. ✅ **REFACTOR Phase**: Code quality improved while maintaining green tests
4. ✅ **Coverage**: >90% test coverage maintained throughout development
5. ✅ **Pre-commit**: All hooks pass (Black, isort, flake8, mypy, pytest)

### Functional Requirements (Test-Verified)
6. ✅ Successfully authenticates to IBKR Client Portal API (existing OAuth)
7. ✅ Executes gap scan at scheduled time (10:00:30 Sydney via cron)
8. ✅ Returns 5-50 gap candidates with >2% gap
9. ✅ Stores candidates in "or_tracking" status for OR monitoring
10. ✅ Tracks opening range for 10 minutes with 30-second polling
11. ✅ Correctly identifies stocks breaking OR high with gap holding
12. ✅ Updates candidates to "orh_breakout" status when triggered
13. ✅ Executes orders for ORH breakout candidates via separate cron job
14. ✅ Handles API errors gracefully without crashing
15. ✅ Integration tests pass with mock data
16. ✅ Logs clearly show execution stages and timing
17. ✅ Configuration can be modified without code changes

### Cron Schedule Requirements
18. ✅ **Gap Scan**: Runs at 10:00:30 Sydney (00:00:30 UTC)
19. ✅ **OR Tracking**: Runs at 10:10:30 Sydney (00:10:30 UTC) 
20. ✅ **ORH Execution**: Runs at 10:12:00 Sydney (00:12:00 UTC)
21. ✅ **Position Management**: Existing 5-minute schedule maintained

### Quality Assurance Requirements
22. ✅ **Australian English**: All code comments and documentation use Australian spelling
23. ✅ **uv Toolchain**: All commands use `uv run` for dependency management
24. ✅ **Parallel Testing**: Tests run in parallel where applicable
25. ✅ **Subagent Delegation**: Complex tasks delegated to subagents when appropriate

## Future Enhancements (Out of Scope)
- Real-time alerting/notifications
- Automatic order placement
- Multi-day backtesting framework
- Position sizing calculator
- Alternative gap patterns (gap fade, gap fill reversal)
- Integration with existing portfolio management system

## TDD Implementation Approach

### Integration Strategy (Test-Driven)
1. **Remove TradingView Scanner**: Delete `src/skim/scanners/tradingview.py` and update imports
2. **Update Existing References**: Replace TradingView imports in bot.py, entry.py, and __init__.py
3. **Extend IBKRClient**: Write failing tests first, then add scanner methods to existing OAuth-based client
4. **Follow Existing Patterns**: Use new GapStock dataclass, database models, error handling (all test-verified)
5. **Leverage Infrastructure**: Use existing retry logic, logging, configuration, testing (maintain test coverage)
6. **Database Extension**: Write failing tests for OR tracking fields, then extend existing Candidate model
7. **Bot Integration**: Write failing integration tests, then add scan_ibkr_gaps() method to existing TradingBot

### TDD Workflow Enforcement
- **No production code without failing test**: Every feature must start with a RED test
- **Minimal implementation**: Write just enough code to pass tests (GREEN)
- **Continuous refactoring**: Improve code while keeping tests green
- **Parallel testing**: Use parallel test execution where applicable
- **Subagent delegation**: Delegate complex multi-step tasks to subagents
- **Australian English**: All code comments and documentation use Australian spelling
- **uv toolchain**: All development commands use `uv run`

### TDD Development Phases

#### Phase 1: IBKRClient Extension (TDD Cycle)
1. **RED**: Write failing tests for scanner methods
2. **GREEN**: Implement minimal scanner endpoints
3. **REFACTOR**: Improve error handling and field mapping
4. **Verification**: All tests pass, coverage >90%

#### Phase 2: IBKRGapScanner Core Logic (TDD Cycle)
1. **RED**: Write failing tests for gap scanning and OR tracking
2. **GREEN**: Implement minimal scanner functionality
3. **REFACTOR**: Optimise performance and logging
4. **Verification**: All tests pass, integration tests work

#### Phase 3: Data Models & Database (TDD Cycle)
1. **RED**: Write failing tests for extended models
2. **GREEN**: Implement database migration and models
3. **REFACTOR**: Add validation and improve queries
4. **Verification**: Database tests pass, migrations work

#### Phase 4: Integration & Workflow (TDD Cycle)
1. **RED**: Write failing integration tests
2. **GREEN**: Implement TradingBot integration
3. **REFACTOR**: Improve error handling and monitoring
4. **Verification**: End-to-end tests pass

#### Phase 5: Final Polish (TDD Cycle)
1. **RED**: Add edge case tests as needed
2. **GREEN**: Implement missing functionality
3. **REFACTOR**: Final code quality improvements
4. **Verification**: Full test suite passes, pre-commit hooks clean

### Key Advantages of This Approach
- ✅ No OAuth implementation needed (already exists)
- ✅ Robust error handling and retry logic (already implemented)
- ✅ Contract ID caching for efficiency (already implemented)
- ✅ Session management and keepalive (already implemented)
- ✅ Paper trading safety (already enforced)
- ✅ Consistent with existing codebase patterns
- ✅ Leverages existing test infrastructure

---

**Note to implementer**: This extends the existing OAuth-based IBKR implementation. Web API latency (~10-15 seconds) means you'll never catch the absolute open, but for 10-minute ORB strategy this is acceptable. Focus on reliability over speed and leverage existing infrastructure. The ASX Service Release 15 changes (single open at 09:59) are critical context - don't try to scan multiple alphabetical groups like pre-May 2025.