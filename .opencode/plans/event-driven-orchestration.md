# Event-Driven Orchestration Plan

## Overview

Transform cron-based orchestration into event-driven phase execution using the existing EventBus infrastructure. This aligns with the current architecture, reduces cron coupling, and scales better for multi-strategy support.

## Current State

```
Cron Jobs (7 entries) → CLI Commands → TradingBot → Strategy Methods
```

**Problems:**
- 7 separate cron jobs tightly coupled to implementation
- Adding new strategies requires more cron entries
- No phase dependency management
- Event infrastructure exists but unused for orchestration
- `alert` and `track_ranges` commands missing from CommandDispatcher

## Target State

```
Cron Jobs (1-2 entries) → Phase Events → EventBus → Strategy.on_event() → Phase Methods
```

**Benefits:**
- Single cron entry per strategy triggers workflow
- Phase transitions driven by events
- Strategies define their own phase dependencies
- Retry logic and error handling via event handlers
- Easy to add strategies with different phase needs

## Architecture Changes

### PhaseSequencer Component

New class: `src/skim/trading/orchestration/phase_sequencer.py`

```python
class PhaseSequencer:
    """Orchestrates strategy phases via event-driven workflow"""

    def __init__(self, event_bus: EventBus, bot: TradingBot):
        self.event_bus = event_bus
        self.bot = bot
        self._phase_state: dict[str, PhaseState] = {}

    async def start_trading_day(self, strategy: str = "orh_breakout"):
        """Start trading day workflow for strategy

        Publishes SETUP event, which triggers phase chain:
        SETUP → SCAN → TRACK_RANGES → ALERT → TRADE (continuous) → MANAGE (continuous)
        """
        await self.event_bus.publish(Event(type=EventType.SETUP, metadata={"strategy": strategy}))

    async def start_monitoring(self, strategy: str = "orh_breakout"):
        """Start continuous monitoring for strategy

        Used by separate cron job for background position management
        """
        await self.event_bus.publish(Event(type=EventType.MANAGE, metadata={"strategy": strategy}))
```

### Phase State Tracking

Track phase completion, dependencies, and retry logic:

```python
@dataclass
class PhaseState:
    strategy: str
    phase: str
    status: "pending" | "running" | "completed" | "failed"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    error: str | None = None
```

### Event Flow

```
Cron: 23:00 UTC
  → publishes Event(type=SETUP, metadata={"strategy": "orh_breakout"})
  → Strategy.on_event(SETUP) executes setup()
  → publishes Event(type=SCAN)
  → Strategy.on_event(SCAN) executes scan()
  → publishes Event(type=CANDIDATES_SCANNED)
  → PhaseSequencer detects scan completion
  → publishes Event(type=TRACK_RANGES)
  → Strategy.on_event(TRACK_RANGES) executes track_ranges()
  → publishes Event(type=OPENING_RANGE_TRACKED)
  → PhaseSequencer publishes Event(type=ALERT)
  → Strategy.on_event(ALERT) executes alert()
  → publishes Event(type=CANDIDATES_ALERTED)
  → PhaseSequencer starts continuous trading loop

Continuous Trading Loop:
  → Cron: */5 min (or internal timer)
  → publishes Event(type=TRADE)
  → Strategy.on_event(TRADE) executes trade()

Continuous Monitoring Loop:
  → Cron: */5 min (separate job)
  → publishes Event(type=MANAGE)
  → Strategy.on_event(MANAGE) executes manage()
```

## Implementation Steps

### Step 1: Create Orchestration Module (30 min)

**Create files:**
- `src/skim/trading/orchestration/__init__.py`
- `src/skim/trading/orchestration/phase_sequencer.py`
- `src/skim/trading/orchestration/phase_state.py`

**Implementation:**
1. Create PhaseState dataclass for tracking phase execution
2. Create PhaseSequencer class with:
   - `start_trading_day(strategy: str)` method
   - `start_monitoring(strategy: str)` method
   - Event handlers for phase completion
   - Phase dependency management
3. Add unit tests in `tests/trading/unit/orchestration/`

### Step 2: Restore Missing Commands (20 min)

**Modify files:**
- `src/skim/application/commands/base.py` - Add AlertCommand, TrackRangesCommand
- `src/skim/application/commands/alert.py` - Create new file
- `src/skim/application/commands/track_ranges.py` - Create new file
- `src/skim/application/services/command_dispatcher.py` - Register handlers

**Implementation:**
1. Add command dataclasses for alert and track_ranges
2. Create handler functions following existing pattern
3. Register in CommandDispatcher._handlers dict
4. Update _print_usage() to include new commands

### Step 3: Update Strategy Event Dispatching (20 min)

**Modify file:**
- `src/skim/domain/strategies/base.py`

**Implementation:**
1. Ensure `on_event()` method handles all phase events
2. Add strategy_name extraction from event metadata
3. Ensure proper event publication for phase completion
4. Verify return values for phase completion tracking

### Step 4: Add PhaseSequencer to TradingBot (15 min)

**Modify file:**
- `src/skim/trading/core/bot.py`

**Implementation:**
1. Import PhaseSequencer
2. Create instance in `__init__`
3. Add `start_trading_day()` and `start_monitoring()` methods
4. Wire up event bus subscriptions

### Step 5: Add CLI Commands for Orchestration (15 min)

**Modify files:**
- `src/skim/application/commands/base.py` - Add StartTradingDayCommand, StartMonitoringCommand
- `src/skim/application/commands/start_trading_day.py` - Create new file
- `src/skim/application/commands/start_monitoring.py` - Create new file
- `src/skim/application/services/command_dispatcher.py` - Register handlers

**Implementation:**
1. Add command dataclasses for new orchestration commands
2. Create handlers that call PhaseSequencer methods
3. Register in dispatcher

### Step 6: Update Crontab (10 min)

**Modify file:**
- `crontab`

**Implementation:**
1. Replace 7 cron entries with 2:
   ```cron
   # Start trading day workflow (23:00 UTC)
   0 23 * * 1-5 skim cd /opt/skim && /opt/skim/.venv/bin/skim start_trading_day >> /opt/skim/logs/cron.log 2>&1

   # Start continuous monitoring (every 5 min during market hours)
   */5 23,0,1,2,3,4,5,6 * * 1-5 skim cd /opt/skim && /opt/skim/.venv/bin/skim start_monitoring >> /opt/skim/logs/cron.log 2>&1
   ```

2. Keep CoolTrader download job unchanged

### Step 7: Add Tests (40 min)

**Create files:**
- `tests/trading/unit/orchestration/test_phase_sequencer.py`
- `tests/trading/unit/orchestration/test_phase_state.py`

**Test coverage:**
1. PhaseSequencer event subscription and publishing
2. Phase state tracking and transitions
3. Dependency management (scan → track_ranges → alert)
4. Error handling and retry logic
5. Strategy-specific phase isolation

### Step 8: Update Documentation (15 min)

**Modify files:**
- `AGENTS.md` - Update commands section
- `README.md` - Update usage examples

**Documentation:**
1. Document new orchestration commands
2. Update cron job explanations
3. Add event flow diagrams
4. Document PhaseSequencer API

### Step 9: Integration Testing (30 min)

**Test plan:**
1. Manual test: Run `skim start_trading_day` and verify phase sequence
2. Verify all phases execute in correct order
3. Check event logs for proper event publication
4. Test error handling (simulate IBKR disconnect)
5. Verify continuous monitoring with `skim start_monitoring`
6. Test with different strategies (add placeholder strategy if needed)

### Step 10: Deployment Migration (10 min)

**Deployment steps:**
1. Deploy new code to production
2. Update crontab on production server
3. Verify logs show expected event flow
4. Monitor for errors
5. Rollback plan: Revert crontab changes if needed

## File Structure

```
src/skim/
├── trading/
│   ├── orchestration/              # NEW
│   │   ├── __init__.py
│   │   ├── phase_sequencer.py      # NEW
│   │   └── phase_state.py          # NEW
│   └── core/
│       └── bot.py                  # MODIFY
├── application/
│   ├── commands/
│   │   ├── base.py                 # MODIFY (add AlertCommand, TrackRangesCommand, StartTradingDayCommand, StartMonitoringCommand)
│   │   ├── alert.py                # NEW
│   │   ├── track_ranges.py         # NEW
│   │   ├── start_trading_day.py    # NEW
│   │   └── start_monitoring.py     # NEW
│   └── services/
│       └── command_dispatcher.py   # MODIFY
└── domain/
    └── strategies/
        └── base.py                 # MODIFY (verify on_event handling)

tests/trading/unit/
├── orchestration/                  # NEW
│   ├── test_phase_sequencer.py     # NEW
│   └── test_phase_state.py         # NEW
└── commands/                       # NEW (if needed)
    ├── test_alert.py
    ├── test_track_ranges.py
    ├── test_start_trading_day.py
    └── test_start_monitoring.py
```

## Risk Mitigation

### Risk 1: Event Loop Complexity
**Mitigation:** Keep PhaseSequencer simple - single responsibility for publishing phase events based on phase completion events. Don't add complex state machines initially.

### Risk 2: Breaking Existing Workflows
**Mitigation:** Keep `alert` and `track_ranges` commands available for manual execution. Don't remove existing phase methods, just add event-driven orchestration on top.

### Risk 3: Debugging Event Flow
**Mitigation:** Add comprehensive logging to PhaseSequencer. Log all phase transitions with strategy name, timestamp, and status.

### Risk 4: Production Rollback
**Mitigation:** Keep old crontab backed up. Can quickly revert to old command structure if new orchestration fails.

## Rollback Plan

If issues arise in production:

1. Revert crontab to old 7-job structure
2. Ensure `alert` and `track_ranges` commands are restored (Step 2)
3. Remove PhaseSequencer integration from TradingBot (Step 4)
4. Deploy and monitor

## Success Criteria

- [ ] All tests pass (including new orchestration tests)
- [ ] Manual test of `skim start_trading_day` completes all phases
- [ ] Continuous monitoring via `skim start_monitoring` works correctly
- [ ] Event logs show proper phase sequencing
- [ ] Error handling works (IBKR disconnect, network failures)
- [ ] Crontab reduced from 7 to 2 entries (per strategy)
- [ ] Documentation updated
- [ ] Production deployment successful
- [ ] No regression in existing functionality

## Timeline Estimate

- **Total Implementation:** 3.5 hours
- **Testing:** 1 hour
- **Documentation:** 0.5 hours
- **Integration & Deployment:** 1 hour
- **Total:** 5-6 hours

## Future Enhancements

1. **Configuration-based workflows:** Allow strategies to define phase sequences in config
2. **Retry policies:** Configurable retry count and backoff per phase
3. **Phase timeouts:** Kill phases that run too long
4. **Multi-strategy coordination:** Run multiple strategies with shared phases
5. **Distributed event bus:** Scale across multiple bot instances
6. **Metrics and dashboards:** Track phase execution times and success rates

## Questions for Implementation

1. **Phase timing:** Should PhaseSequencer use internal timers for continuous phases (TRADE, MANAGE) or rely on external cron?

   *Recommendation:* Use external cron for continuous phases (simpler, aligns with current pattern). PhaseSequencer triggers initial phase, then cron repeats.

2. **Phase isolation:** Should phases for different strategies run concurrently or sequentially?

   *Recommendation:* Concurrently. Each strategy has its own phase state in PhaseSequencer.

3. **Error handling:** Should phase failures stop the workflow or continue to next phase?

   *Recommendation:* Depends on phase. Critical phases (SCAN, TRACK_RANGES) should stop. Non-critical (ALERT) should log warning and continue. Make configurable per phase.

4. **Purge candidates:** Should purge happen as part of SETUP or remain separate?

   *Recommendation:* Keep as part of SETUP phase (strategy.setup() already calls purge_candidates).
