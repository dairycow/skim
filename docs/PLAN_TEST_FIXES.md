# Test Fixes Plan

## Current State Analysis
- **Total tests**: 395
- **Passing**: 380
- **Failing**: 15
- **Coverage**: 76.82% (target: 80%)

---

## Failing Tests Breakdown

### Category A: Missing `get_market_data_extended` Method (6 tests)

**Tests affected:**
- `test_ibkr_scanner.py::TestIBKRScanner::test_get_market_data_extended_not_found`
- `test_ibkr_scanner.py::TestIBKRScanner::test_get_market_data_extended_not_connected`
- `test_ibkr_scanner.py::TestIBKRScanner::test_get_market_data_extended_empty_response`
- `test_ibkr_scanner.py::TestIBKRScanner::test_get_market_data_extended_empty_conid`
- `test_ibkr_scanner.py::TestIBKRScanner::test_get_market_data_extended_type_conversion`
- `test_ibkr_scanner.py::TestIBKRGapScannerConfig::test_ibkr_scanner_default_config_when_not_provided`

**Root cause**: Tests reference `get_market_data_extended()` method that doesn't exist in `IBKRClient`

**Fix strategy**:
1. **Option A (Recommended)**: Remove/refactor these tests if the method was removed during refactoring
2. **Option B**: Implement `get_market_data_extended()` if it's needed functionality

**Action**: Review `ibkr_client.py` history to determine if this was intentionally removed, then either:
- Delete obsolete tests
- Implement missing method if needed

**Estimated effort**: 30 minutes

---

### Category B: Daily Low Field Not Captured (2 tests)

**Tests affected:**
- `test_ibkr_market_data_low.py::TestIBKRMarketDataWithLow::test_get_market_data_includes_daily_low`
- `test_ibkr_market_data_low.py::TestIBKRMarketDataWithLow::test_get_market_data_handles_missing_daily_low`

**Root cause**: `get_market_data()` returns `None` instead of market data with `low` field

**Evidence**: Test mocks include field `"7": "148.0"` (daily low) but the method returns `None`

**Fix strategy**:
1. Check field mapping in `ibkr_client.py` around line 790 - ensure field "7" is included and mapped to `low`
2. Update `MarketData` dataclass to include `low` field if missing
3. Ensure response parsing extracts field "7" from IBKR response

**Files to modify**:
- `src/skim/brokers/ibkr_client.py` (get_market_data method around line 750-850)
- `src/skim/data/models.py` or `src/skim/brokers/ib_interface.py` (MarketData dataclass)

**Estimated effort**: 30 minutes

---

### Category C: Penny Stock Price Parsing (2 tests)

**Tests affected:**
- `test_ibkr_penny_stocks.py::TestIBKRPennyStockParsing::test_get_market_data_handles_ibkr_prefixes`
- `test_ibkr_penny_stocks.py::TestIBKRPennyStockParsing::test_get_market_data_handles_extremely_small_prices`

**Root cause**: Test expects ticker "BLU" but gets "TEST" - ticker not being properly extracted from IBKR response

**Evidence**: `assert result.ticker == "BLU"` fails with `AssertionError: assert 'TEST' == 'BLU'`

**Fix strategy**:
1. Update `get_market_data()` to accept and use `ticker` parameter instead of relying on API response
2. Modify test mocks to properly simulate IBKR response structure
3. Ensure ticker is passed through correctly when contract ID is resolved

**Files to modify**:
- `src/skim/brokers/ibkr_client.py` (get_market_data method signature and implementation)
- `tests/unit/brokers/test_ibkr_penny_stocks.py` (test setup)

**Estimated effort**: 20 minutes

---

### Category D: Stop Loss Daily Low Integration (2 tests)

**Tests affected:**
- `test_bot_stop_loss_daily_low.py::TestBotStopLossWithDailyLow::test_stop_loss_falls_back_to_percentage_when_daily_low_unavailable`
- `test_bot_stop_loss_daily_low.py::TestBotStopLossWithDailyLow::test_stop_loss_handles_missing_market_data_gracefully`

**Root cause**: Depends on Category B - daily low field not being captured

**Fix strategy**:
1. Fix Category B first
2. Verify stop loss calculation uses `market_data.low` when available
3. Ensure fallback to percentage-based calculation works

**Files to modify**:
- Depends on Category B fixes
- `src/skim/strategy/position_manager.py` (calculate_stop_loss function)

**Estimated effort**: 10 minutes (dependent on Category B)

---

### Category E: Cron Schedule Validation (1 test)

**Tests affected:**
- `test_cron_schedule.py::TestCronScheduleValidation::test_scan_and_track_not_scheduled_same_time`

**Root cause**: Test expects to find "scan" command in crontab but finds 0 entries

**Evidence**: `AssertionError: No scan command found in crontab`

**Fix strategy**:
1. Review `crontab` file to ensure scan commands are present
2. Update test regex pattern to match actual crontab format
3. Ensure test is reading correct crontab file path

**Files to check**:
- `/Users/hf/repos/skim/crontab` (verify scan commands exist)
- `tests/unit/test_cron_schedule.py` (line 83 - check regex pattern)

**Estimated effort**: 15 minutes

---

### Category F: Opening Range Tracking Validation (2 tests)

**Tests affected:**
- `test_scanners.py::TestIBKRGapScanner::test_track_opening_range_success`

**Root cause**: Mock market data returns 0.0 for all price fields, failing Pydantic validation

**Evidence**: Validation errors show `or_high`, `or_low`, `open_price`, `prev_close`, `current_price` all 0.0 (must be > 0)

**Fix strategy**:
1. Update test mocks to provide realistic positive price values
2. Ensure `track_opening_range()` mock responses include valid market data
3. Fix mock `get_market_data()` calls to return proper `MarketData` objects

**Files to modify**:
- `tests/unit/test_scanners.py` (test setup around opening range tracking)
- Mock setup for `IBKRClient.get_market_data()` in test fixtures

**Estimated effort**: 20 minutes

---

## Implementation Timeline

### Phase 1: Fix Critical Test Failures

| Category | Effort | Blocker | Notes |
|----------|--------|---------|-------|
| A: Missing get_market_data_extended | 30 min | No | Remove obsolete tests |
| B: Daily low field capture | 30 min | No | Core fix for other issues |
| C: Penny stock ticker extraction | 20 min | No | Independent |
| E: Cron schedule validation | 15 min | No | Independent |
| F: Opening range mocks | 20 min | No | Independent |
| D: Stop loss integration | 10 min | Yes | Depends on B |

**Total estimated effort**: 2-2.5 hours
**Expected outcome**: All 15 tests passing, 80%+ coverage

---

## Test Execution Order

1. Start with Categories A, C, E, F (independent fixes)
2. Then Category B (foundational)
3. Finally Category D (depends on B)

This allows parallel work if needed and ensures blockers are resolved early.

---

## Validation Checklist

After implementing fixes:

- [ ] All 15 failing tests now pass
- [ ] No previously passing tests regress
- [ ] Coverage reaches 80%+ target
- [ ] Test execution completes in under 35 seconds
- [ ] No new warnings or errors in test output

---

## Notes

- Each category is independent except for D which depends on B
- Focus on fixing the root causes, not patching tests
- Ensure changes maintain compatibility with existing passing tests
- Update related tests if implementation changes API signatures
