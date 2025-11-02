# Price-Sensitive Announcements Filter Design

**Date**: 2025-11-03
**Status**: Approved

## Overview

Add ASX price-sensitive announcement filtering to the existing TradingView momentum scan. The bot will only flag candidates that show BOTH momentum signals (gaps) AND have price-sensitive announcements today.

## Motivation

Price-sensitive announcements are often catalysts for sustained momentum. By filtering for stocks with both technical signals (gaps) and fundamental catalysts (announcements), we improve candidate quality and reduce false signals.

## Design

### High-Level Approach

**Current Flow**:
- `scan()` → TradingView API → Find stocks with gaps >2% → Store as candidates
- `monitor()` → Check if candidates now have gaps ≥3% → Mark as triggered

**New Flow**:
- `scan()` → TradingView API → Find momentum stocks → **Check ASX announcements** → Only keep stocks with BOTH signals → Store as candidates
- `monitor()` → (unchanged - just checks gap threshold)

**Key Principle**: Price-sensitive announcements act as a **quality filter**, not a separate data source.

### Implementation Details

#### 1. New Method: `_fetch_price_sensitive_announcements()`

Fetches today's price-sensitive announcements from ASX:

```python
def _fetch_price_sensitive_announcements(self) -> set[str]:
    """
    Fetch today's price-sensitive announcements from ASX

    Returns:
        Set of ticker symbols with price-sensitive announcements
    """
```

**Steps**:
1. Fetch HTML from `https://www.asx.com.au/asx/v2/statistics/todayAnns.do`
2. Parse with BeautifulSoup
3. Filter `<tr>` rows containing "pricesens"
4. Extract ticker symbols from first `<td>` element
5. Return set of tickers (e.g., `{"BHP", "RIO", "FMG"}`)

**Error Handling**:
- Network timeout: 10 seconds
- Parse errors: Log warning, return empty set
- Empty results: Log info, return empty set
- Graceful degradation: Bot continues with empty set (zero candidates)

#### 2. Modified `scan()` Method

**Integration Logic**:

```python
def scan(self):
    # 1. Fetch price-sensitive announcements FIRST
    price_sensitive_tickers = self._fetch_price_sensitive_announcements()
    logger.info(f"Found {len(price_sensitive_tickers)} price-sensitive announcements today")

    # 2. Query TradingView (unchanged)
    stocks = self._query_tradingview(min_gap=2.0)

    # 3. Filter for intersection
    for ticker, gap_percent, close_price in stocks:
        # Only process if ticker has price-sensitive announcement
        if ticker not in price_sensitive_tickers:
            logger.debug(f"{ticker}: Skipped (no price-sensitive announcement)")
            continue

        # Rest of existing logic - add to candidates
        # ... (unchanged)
```

**Logging Enhancements**:
- Summary: "Found X price-sensitive announcements today"
- Per-ticker: "Added {ticker} to candidates (gap: X%, price-sensitive announcement)"
- Filtered out: Debug-level log for skipped tickers
- Final: "Scan complete. Found X candidates with both momentum and announcements"

#### 3. Dependencies

Add to `pyproject.toml`:
```toml
beautifulsoup4 = "^4.12.0"
lxml = "^5.1.0"  # Fast HTML parser
```

#### 4. No Database Changes

- No new columns needed
- Announcements used only as filter (not stored)
- Keeps schema simple and unchanged

### Graceful Degradation Scenarios

| Scenario | Behavior |
|----------|----------|
| ASX endpoint returns empty | Log warning, continue with zero candidates (safe) |
| ASX endpoint fails (network) | Log warning, return empty set, zero candidates |
| ASX HTML format changes | Parse fails, log warning, empty set |
| TradingView fails | Existing error handling (returns empty list) |

All failure modes are safe: bot continues without crashing.

## Testing Strategy

### Manual Testing (via Termius)

1. **Test ASX announcement fetching**:
   ```bash
   docker-compose exec bot python -c "from bot import TradingBot; bot = TradingBot(); print(bot._fetch_price_sensitive_announcements())"
   ```
   - Verify against ASX website manually

2. **Test scan with filtering**:
   ```bash
   docker-compose exec bot python /app/bot.py scan
   ```
   - Check logs show announcement count
   - Query database: `SELECT ticker, gap_percent FROM candidates;`
   - Manually verify tickers have both signals

3. **Test graceful degradation**:
   - Temporarily break ASX URL
   - Run scan, verify warning logged
   - Confirm bot doesn't crash
   - Restore URL

### Verification Checklist

- [ ] BeautifulSoup parses ASX HTML correctly
- [ ] Only tickers with BOTH signals become candidates
- [ ] Logs clearly show filtering in action
- [ ] ASX endpoint failure doesn't crash bot
- [ ] Existing functionality (monitor, execute, manage_positions) unaffected

### Production Monitoring

Watch for:
- "Found 0 price-sensitive announcements" (could indicate ASX format change)
- Compare candidate counts before/after to gauge filter effectiveness

## Implementation Plan

1. Add dependencies to `pyproject.toml`
2. Implement `_fetch_price_sensitive_announcements()` method
3. Modify `scan()` method with filtering logic
4. Add imports (BeautifulSoup)
5. Test locally
6. Deploy and monitor

## Rollback Plan

If issues arise:
1. Remove filtering logic from `scan()` (revert to previous version)
2. Bot continues with TradingView-only scanning
3. No database migrations to rollback

## Future Enhancements

- Add `ASX_ANN_ENABLED` env var to toggle feature
- Store announcement headlines in database for review
- Add announcement text to logs/status output
- Cache announcements for 24h to reduce API calls
