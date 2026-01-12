# ASX Swing Trading Study - Non-Interactive CLI Skill

This skill teaches agents how to use the ASX Swing Trading Study CLI in non-interactive mode for programmatic access.

## Overview

The ASX Swing Trading Study tool supports two modes:
- **Interactive mode**: Default human-interactive console (requires user input)
- **Non-interactive mode**: Execute single commands programmatically, return JSON output

  ## When to Use Non-Interactive Mode

  Use non-interactive mode when you need to:
  - Query stock performance data programmatically
  - Get company information and metadata
  - Get structured JSON output for processing
  - Run single commands without user interaction
  - Integrate with other tools or agents

## Usage Pattern

```bash
uv run skim-analyze <command> [arguments] [--json] [--limit N]
```

 ## Available Commands

 ### 1. Top Performers (`top`)

 Find top performing stocks over a period.

 **Syntax:**
 ```bash
 uv run skim-analyze top <period> [--limit N] [--json]
 ```

 **Period formats:**
 - `YYYY` (e.g., `2025`) - Full year
 - `YYYY-MM` (e.g., `2025-12`) - Specific month
 - `YYYY-MM-DD to YYYY-MM-DD` (e.g., `2025-12-01 to 2025-12-31`) - Date range
 - `1M`, `3M`, `6M`, `1Y` - Relative periods from today

 **Examples:**
 ```bash
 # Top performers for December 2025
 uv run skim-analyze top 2025-12 --json

 # Top 5 performers for 2024
 uv run skim-analyze top 2024 --json --limit 5

 # Top performers for last 3 months
 uv run skim-analyze top 3M --json
 ```

 **JSON output structure:**
 ```json
 [
   {
     "ticker": "4DX",
     "total_return": 125.21,
     "start_price": 1.745,
     "end_price": 3.93
   }
 ]
 ```

 ### 2. Gaps (`gaps`)

 Find significant price gaps (10%+) with volume confirmation.

 **Syntax:**
 ```bash
 uv run skim-analyze gaps <period> [--limit N] [--json]
 ```

 **Period formats:** Same as `top` command

 **Examples:**
 ```bash
 # Gaps in December 2025
 uv run skim-analyze gaps 2025-12 --json

 # Top 3 gaps for 2025
 uv run skim-analyze gaps 2025 --json --limit 3
 ```

 **JSON output structure:**
 ```json
 [
   {
     "ticker": "A1G",
     "date": "2025-12-02",
     "gap_percent": 65.08,
     "open": 0.52,
     "prev_close": 0.315
   }
 ]
 ```

 ### 3. Announcements (`ann`)

 Get ASX company announcements for a ticker.

 **Syntax:**
 ```bash
 uv run skim-analyze ann <ticker> <period> [--limit N] [--json]
 ```

 **Parameters:**
 - `ticker`: ASX ticker symbol (e.g., BHP, CBA)
 - `period`: Date range (same formats as above)

 **Examples:**
 ```bash
 # Announcements for BHP in 2024
 uv run skim-analyze ann BHP 2024 --json

 # Recent 5 announcements for CBA
 uv run skim-analyze ann CBA 3M --json --limit 5
 ```

  **JSON output structure:**
  ```json
  [
    {
      "date": "20241218",
      "time": "1651",
      "headline": "Federal Court of Australia Class Action Proceeding",
      "price_sensitive": false
    }
  ]
  ```

  **Rate Limit:** 50 calls/minute (ASX website rate limit)

 ### 4. Chart (`chart`)

 Display terminal candlestick chart (non-JSON output only).

 **Syntax:**
 ```bash
 uv run skim-analyze chart <ticker> [period]
 ```

 **Examples:**
 ```bash
 # Chart for BHP (all data)
 uv run skim-analyze chart BHP

 # Chart for BHP in 2025-12
 uv run skim-analyze chart BHP 2025-12

 # Chart for last 6 months
 uv run skim-analyze chart BHP 6M
 ```

 **Note:** Chart command does not support JSON output as it's visual-only.

 ### 5. Momentum Bursts (`momentum`)

 Find momentum bursts (3+ consecutive up days) with volume analysis.

 **Syntax:**
 ```bash
 uv run skim-analyze momentum <period> [--days N] [--limit N] [--json]
 ```

 **Parameters:**
 - `period`: Date range (same formats as `top` command)
 - `--days`: Minimum consecutive up days (default: 3)
 - `--limit`: Maximum results to return (default: 50)

 **Examples:**
 ```bash
 # Momentum bursts in December 2025 (3+ consecutive up days)
 uv run skim-analyze momentum 2025-12 --json

 # Momentum bursts with 5+ consecutive up days
 uv run skim-analyze momentum 2025-12 --days 5 --json

 # Top 10 momentum bursts
 uv run skim-analyze momentum 2025-12 --json --limit 10
 ```

 **JSON output structure:**
 ```json
 [
   {
     "ticker": "FTI",
     "start_date": "2025-12-11",
     "end_date": "2025-12-22",
     "duration_days": 7,
     "total_gain_pct": 100.0,
     "start_price": 0.185,
     "end_price": 0.37,
     "volume_spike_multiple": 28.32
   }
 ]
 ```

 **Detection criteria:**
 - Minimum 3 consecutive up days (configurable with `--days`)
 - Calculates price gain and volume spike vs 50-day baseline
 - Volume multiple indicates how much volume exceeded average

 ### 6. Consolidation Patterns (`consolidate`)

 Find consolidation patterns (flat price + low volume).

 **Syntax:**
 ```bash
 uv run skim-analyze consolidate <period> [--range-pct X] [--days N] [--limit N] [--json]
 ```

 **Parameters:**
 - `period`: Date range (same formats as `top` command)
 - `--range-pct`: Maximum price range percentage (default: 10.0)
 - `--days`: Minimum consolidation duration (default: 5 days)
 - `--limit`: Maximum results to return (default: 50)

 **Examples:**
 ```bash
 # Consolidations within 10% price range
 uv run skim-analyze consolidate 2025-12 --json

 # Tight consolidations within 5% price range
 uv run skim-analyze consolidate 2025-12 --range-pct 5 --json

 # Longer consolidations (10+ days)
 uv run skim-analyze consolidate 2025-12 --days 10 --json
 ```

 **JSON output structure:**
 ```json
 [
   {
     "ticker": "RIV",
     "start_date": "2025-12-09",
     "end_date": "2025-12-15",
     "duration_days": 5,
     "price_range_pct": 4.46,
     "low": 1.425,
     "high": 1.49,
     "volume_ratio_to_avg": 0.43
   }
 ]
 ```

 **Detection criteria:**
 - Price stays within specified range percentage
 - Duration meets minimum days requirement
 - Volume is below baseline (ratio < 1.0 indicates declining interest)

 ### 7. Pattern Analysis (`pattern`)

 Analyze both momentum bursts and consolidation patterns for a specific stock.

 **Syntax:**
 ```bash
 uv run skim-analyze pattern <ticker> <period> [--json]
 ```

 **Parameters:**
 - `ticker`: ASX ticker symbol (e.g., BHP, CBA)
 - `period`: Date range (same formats as `top` command)

 **Examples:**
 ```bash
 # Analyze 4DX patterns in December 2025
 uv run skim-analyze pattern 4DX 2025-12 --json

 # Analyze BHP patterns for 2024
 uv run skim-analyze pattern BHP 2024 --json
 ```

 **JSON output structure:**
 ```json
 {
   "ticker": "4DX",
   "momentum_bursts": [
     {
       "start_date": "2025-12-11",
       "end_date": "2025-12-16",
       "duration_days": 3,
       "total_gain_pct": 46.08,
       "start_price": 2.04,
       "end_price": 2.98
     }
   ],
   "consolidations": [],
   "total_momentum_bursts": 2,
   "total_consolidations": 0
 }
 ```

 ### 8. Move Statistics (`movestats`)

 Get statistical summary of momentum burst and consolidation durations across all stocks.

 **Syntax:**
 ```bash
 uv run skim-analyze movestats <period> [--json]
 ```

 **Parameters:**
 - `period`: Date range (same formats as `top` command)

 **Examples:**
 ```bash
 # Get statistics for December 2025
 uv run skim-analyze movestats 2025-12 --json

 # Get statistics for 2024
 uv run skim-analyze movestats 2024 --json
 ```

 **JSON output structure:**
 ```json
 {
   "period": "2025-12-01 to 2025-12-31",
   "total_stocks": 819,
   "momentum_bursts": {
     "total_count": 600,
     "avg_duration_days": 3.71,
     "median_duration_days": 3.0,
     "max_duration_days": 15,
     "min_duration_days": 3,
     "total_gain_avg_pct": 10.46,
     "duration_distribution": {
       "3_days": 338,
       "4_days": 168,
       "5_days": 62,
       "6+_days": 32
     }
   },
   "consolidation": {
     "total_count": 1000,
     "avg_duration_days": 5,
     "median_duration_days": 5.0,
     "max_duration_days": 5,
     "min_duration_days": 5,
     "avg_price_range_pct": 5.05,
     "duration_distribution": {
       "5_days": 1000
     }
   }
 }
 ```

  **Statistics include:**
  - Count, average, median, min, max durations
  - Average gain per momentum burst
  - Duration distribution bins
  - Price range analysis for consolidations

  ### 9. Company Info (`info`)

  Get company information including name, sector, industry, market cap, and business description.

  **Syntax:**
  ```bash
  uv run skim-analyze info <ticker> [--json]
  ```

  **Parameters:**
  - `ticker`: ASX ticker symbol (e.g., BHP, CBA)

  **Examples:**
  ```bash
  # Get BHP company info
  uv run skim-analyze info BHP --json

  # Get Commonwealth Bank info
  uv run skim-analyze info CBA --json
  ```

  **JSON output structure:**
  ```json
  {
    "ticker": "BHP",
    "name": "BHP Group Limited",
    "sector": "Basic Materials",
    "industry": "Other Industrial Metals & Mining",
    "market_cap": "$242.33B",
    "business_summary": "BHP Group Limited operates as a resources company in Australia, Europe, China, Japan, India, South Korea, rest of Asia, North America, South America, and internationally."
  }
  ```

  **Rate Limit:** 50 calls/minute (Yahoo Finance rate limit)
  **Note:** The `info` command works independently without requiring local data to be loaded. It fetches real-time data from Yahoo Finance.

   ## Common Flags

 - `--json`: Output as JSON (minimal format, machine-readable)
 - `--quiet`: Suppress status messages (for clean JSON output)
 - `--limit N`: Limit results to N items (default: 50)
 - `--days N`: Minimum days for momentum/consolidation (default: 3 for momentum, 5 for consolidation)
 - `--range-pct X`: Maximum price range percent for consolidation (default: 10.0)

 ## Momentum and Consolidation Analysis

 The CLI includes advanced pattern detection for studying momentum bursts and consolidation phases:

### Momentum Burst Detection

**Definition:** Periods of 3+ consecutive positive daily closes

**Key Metrics:**
- `duration_days`: Number of consecutive up days
- `total_gain_pct`: Percentage gain from start to end
- `volume_spike_multiple`: Volume vs 50-day average baseline
- `start_price`, `end_price`: Entry and exit prices

**Use Cases:**
- Identify strong upward momentum phases
- Study typical momentum burst durations
- Analyze volume confirmation during runs
- Find high-gain explosive moves

### Consolidation Detection

**Definition:** Sideways price action with low volume interest

**Key Metrics:**
- `duration_days`: Length of consolidation
- `price_range_pct`: High/low range as percentage of average price
- `volume_ratio_to_avg`: Volume vs baseline ( < 1.0 = declining interest)
- `low`, `high`: Support and resistance levels

**Use Cases:**
- Identify stocks building bases before breakouts
- Find pullback/rest phases during uptrends
- Study typical consolidation durations
- Detect potential reversal formations

### Statistical Analysis

**`movestats`** command provides insights:
- Average/median momentum burst durations
- Average gain per burst
- Duration distribution (e.g., how many bursts are 3, 4, 5+ days)
- Consolidation duration statistics
- Price range analysis

**Example insights from December 2025:**
- 600 momentum bursts found
- Average duration: 3.71 days
- Average gain: 10.46% per burst
- Longest burst: 15 days
- 1000 consolidations detected
- Average consolidation: 5 days with 5.05% price range

 ## Exit Codes

- `0`: Success
- `1`: Error (invalid arguments, unknown commands, parse errors)

## Best Practices for Agents

### 1. Always Use JSON Output
For programmatic access, always use `--json` to get structured data:

```python
# Good
uv run skim-analyze top 2025-12 --json

# Bad (human-readable, hard to parse)
uv run skim-analyze top 2025-12
```

### 2. Use Quiet Mode for Clean JSON
For automated processing, combine `--json` with `--quiet` to get clean, parseable output:

```bash
# Clean JSON output (no status messages)
uv run skim-analyze gaps 2025-12 --json --quiet --limit 10

# For comparison - includes status messages
uv run skim-analyze gaps 2025-12 --json --limit 10
```

### 3. Limit Results for Performance
When you only need a few results, use `--limit` to improve performance:

```bash
# Get only the top performer
uv run skim-analyze top 2025-12 --json --limit 1
```

### 3. Handle Exit Codes
Check exit codes to detect errors:

```bash
uv run skim-analyze top 2025-12 --json
exit_code=$?
if [ $exit_code -eq 0 ]; then
    # Success
else
    # Error
fi
```

### 4. Error Handling
Common errors to handle:
- Invalid period format
- Missing required arguments
- Unknown commands

 ## Example Workflows

 ### Get Top Performer for a Period
 ```bash
 # Get the #1 performing stock
 uv run skim-analyze top 2025-12 --json --limit 1
 ```

 ### Get Recent Announcements
 ```bash
 # Get last 5 announcements for a stock
 uv run skim-analyze ann BHP 3M --json --limit 5
 ```

 ### Find Gaps and Top Performers
 ```bash
 # Find significant gaps
 uv run skim-analyze gaps 2025-12 --json --limit 10

 # Find top performers
 uv run skim-analyze top 2025-12 --json --limit 10
 ```

 ### Analyze Momentum Patterns
 ```bash
 # Find all momentum bursts in a period
 uv run skim-analyze momentum 2025-12 --json --limit 20

 # Find strong momentum bursts (5+ consecutive up days)
 uv run skim-analyze momentum 2025-12 --days 5 --json --limit 10
 ```

 ### Study Consolidation Patterns
 ```bash
 # Find stocks in consolidation within 10% price range
 uv run skim-analyze consolidate 2025-12 --json --limit 20

 # Find tight consolidations within 5% price range
 uv run skim-analyze consolidate 2025-12 --range-pct 5 --days 5 --json
 ```

 ### Analyze a Stock's Pattern Sequence
 ```bash
 # Get complete pattern analysis for a stock
 uv run skim-analyze pattern 4DX 2025-12 --json

 # Analyze pattern sequence over multiple months
 uv run skim-analyze pattern BHP 2024 --json
 ```

  ### Get Statistical Insights
  ```bash
  # Get move duration statistics for a period
  uv run skim-analyze movestats 2025-12 --json

  # Compare statistics across different periods
  uv run skim-analyze movestats 2024 --json
  uv run skim-analyze movestats 2024-Q1 --json
  ```

  ### Get Company Information
  ```bash
  # Get company info for a stock
  uv run skim-analyze info BHP --json

  # Get company info for multiple stocks
  uv run skim-analyze info CBA --json
  uv run skim-analyze info ANZ --json
  ```

  ### Complete Analysis Workflow
 ```bash
 # 1. Find top performers
 uv run skim-analyze top 2025-12 --json --limit 10

 # 2. Check for momentum bursts
 uv run skim-analyze momentum 2025-12 --days 3 --json --limit 15

 # 3. Analyze specific stock patterns
 uv run skim-analyze pattern 4DX 2025-12 --json

 # 4. Get overall statistics
 uv run skim-analyze movestats 2025-12 --json
 ```

## Performance Notes

- First run loads all stock data (~819 stocks, ~5211 CSV files)
- Subsequent runs in same session reload data
- Loading data takes ~5-10 seconds
- Use `--limit` to reduce processing time for large result sets

## Data Loading

The CLI automatically loads stock data on each command run. Loading filters:
- Minimum price: $0.20
- Minimum volume: 50,000 shares
- 819 stocks typically pass filters from 5,211 CSV files

## Rate Limits

Some commands access external APIs and have rate limits:

| Command | Rate Limit | Reason |
|---------|-----------|--------|
| `ann` | 50 calls/minute | ASX website scraping |
| `info` | 50 calls/minute | Yahoo Finance API |

**No rate limits:**
- `top`, `gaps`, `momentum`, `consolidate`, `pattern`, `movestats`, `chart`
- These commands use local CSV data and don't access external APIs

**Best practice:** When making many calls to `ann` or `info`, add delays between requests to avoid hitting rate limits. The local data commands can be called without restrictions.

## Troubleshooting

### Command Not Found
Ensure you're in the correct directory and the file exists:
```bash
pwd  # Should be /Users/hf/repos/asx-swing-study
uv run skim-analyze  # Should exist
```

### Invalid Period Format
Check period format matches supported patterns:
- `2025` (year)
- `2025-12` (year-month)
- `2025-12-01 to 2025-12-31` (date range)
- `1M`, `3M`, `6M`, `1Y` (relative)

### No Data Found
If you get empty results, the period may have no trading data or no stocks meet the filters.

### Rate Limit Errors
If you get errors like "429 Too Many Requests" or connection failures for `ann` or `info` commands:
- You've exceeded the 50 calls/minute rate limit
- Wait 60 seconds before making more requests
- Use `--limit` to reduce the number of calls
- Local data commands (`top`, `gaps`, `momentum`, etc.) don't have rate limits

  ## Interactive Mode

 For human use, run without arguments to enter interactive mode:
 ```bash
 uv run skim-analyze
 ```

  Interactive commands: `load`, `top`, `gaps`, `ann`, `chart`, `momentum`, `consolidate`, `pattern`, `movestats`, `info`, `help`, `quit`

  **New interactive commands:**
  - `momentum <period>` - Show momentum bursts (e.g., `momentum 2025-12`)
  - `consolidate <period>` - Show consolidation patterns (e.g., `consolidate 2025-12`)
  - `pattern <ticker> <period>` - Show pattern analysis (e.g., `pattern 4DX 2025-12`)
  - `movestats <period>` - Show move statistics (e.g., `movestats 2025-12`)
  - `info <ticker>` - Show company info (e.g., `info BHP`)
