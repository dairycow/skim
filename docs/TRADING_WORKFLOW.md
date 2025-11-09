# Skim Trading Bot - Automated Workflow

## Cron-Managed Trading Workflow

The entire trading workflow is automated via cron jobs running in the Docker container.

```mermaid
graph TB
    Start[Container Startup] --> StartCron[Start Cron Daemon]
    StartCron --> TailLogs[Tail Logs]

    subgraph "Cron Schedule (UTC Times)"

        subgraph "Market Open - 00:00:30 UTC (10:00:30 AM AEDT)"
            Scan[SCAN_IBKR_GAPS<br/>Monday-Friday 00:00:30]
            Scan --> QueryIBKR[Query IBKR<br/>Gaps ≥ 3%]
            QueryIBKR --> SaveCandidates[Save to DB<br/>status: or_tracking]
        end

        subgraph "10 Min After Scan - 00:10:30 UTC (10:10:30 AM AEDT)"
            Track[TRACK_OR_BREAKOUTS<br/>Monday-Friday 00:10:30]
            Track --> GetTracking[Get OR tracking<br/>candidates]
            GetTracking --> TrackOR[Track opening range<br/>for 10 minutes]
            TrackOR --> FilterBreakouts[Filter ORH<br/>breakouts]
            FilterBreakouts --> UpdateBreakouts[Update candidates<br/>status: orh_breakout]
        end

        subgraph "12 Min After Scan - 00:12:00 UTC (10:12:00 AM AEDT)"
            Execute[EXECUTE_ORH_BREAKOUTS<br/>Monday-Friday 00:12:00]
            Execute --> CheckMax{Max positions<br/>reached?}
            CheckMax -->|No| GetBreakouts[Get ORH breakout candidates]
            CheckMax -->|Yes| SkipExec[Skip execution]
            GetBreakouts --> PlaceOrders[Place BUY orders via<br/>Custom IBKR Client<br/>OAuth 1.0a]
            PlaceOrders --> RecordPos[Record position & trade<br/>status: entered]
        end

        subgraph "Every 5 Min During Market - */5 23-05 UTC"
            Manage[MANAGE_POSITIONS<br/>Sunday-Thursday */5 23-05]
            Manage --> GetOpen[Get open positions]
            GetOpen --> CheckDay3{Day 3?}
            CheckDay3 -->|Yes & not half_sold| SellHalf[Sell 50%<br/>status: half_exited]
            CheckDay3 -->|No| CheckStop{Price ≤<br/>stop_loss?}
            SellHalf --> CheckStop
            CheckStop -->|Yes| SellAll[Sell remaining<br/>status: closed]
            CheckStop -->|No| Continue[Continue monitoring]
        end

        subgraph "End of Day - 05:30 UTC (4:30 PM AEDT)"
            Status[STATUS<br/>Monday-Friday 05:30]
            Status --> Report[Generate report:<br/>- Watching candidates<br/>- Open positions<br/>- Total PnL]
        end
    end

    subgraph "Data Layer"
        DB[(SQLite Database<br/>/app/data/skim.db)]
        Logs[Log Files<br/>/var/log/cron.log<br/>/app/logs/skim_*.log]
    end

    SaveCandidates -.-> DB
    UpdateCandidates -.-> DB
    RecordPos -.-> DB
    GetOpen -.-> DB
    Report -.-> DB

    Scan -.-> Logs
    Monitor -.-> Logs
    Execute -.-> Logs
    Manage -.-> Logs
    Status -.-> Logs

    style Start fill:#e1f5ff
    style Scan fill:#fff4e6
    style Monitor fill:#e8f5e9
    style Execute fill:#fce4ec
    style Manage fill:#f3e5f5
    style Status fill:#e0f2f1
    style DB fill:#fffde7
    style Logs fill:#fff3e0
```

## Workflow Confirmation

- **Cron is active** - Started by `/app/startup.sh`
- **All jobs configured** - Loaded from `/etc/cron.d/skim-cron`
- **Logs are captured** - Output to `/var/log/cron.log`
- **Custom IBKR Client** - OAuth 1.0a authentication via `ibkr_client.py`
- **OAuth configured** - All environment variables and key files present

## Manual Execution

You can manually trigger any workflow step:

```bash
# SSH into droplet

# Run any command manually
docker exec skim-bot /usr/local/bin/python -m skim.core.bot scan_ibkr_gaps
docker exec skim-bot /usr/local/bin/python -m skim.core.bot track_or_breakouts
docker exec skim-bot /usr/local/bin/python -m skim.core.bot execute_orh_breakouts
docker exec skim-bot /usr/local/bin/python -m skim.core.bot manage_positions
docker exec skim-bot /usr/local/bin/python -m skim.core.bot status
```

## Data Flow

1. **Candidates Table**: Stores stocks identified during scan
2. **Positions Table**: Tracks active trades with entry/exit prices
3. **Trades Table**: Records all buy/sell transactions
4. **Status Transitions**: watching → triggered → entered → half_exited → closed
