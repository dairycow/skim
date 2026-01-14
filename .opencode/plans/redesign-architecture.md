# Skim Codebase Redesign Plan
## Full Migration to Hexagonal Event-Driven Architecture

**Date:** January 15, 2026
**Current State:** 9,722 lines, 49 Python files, 3-module monorepo
**Target:** Hexagonal architecture with event-driven strategies, SRP-compliant design
**Estimated Duration:** 10 weeks

---

## Executive Summary

This plan restructures Skim quantitative trading codebase to address critical architectural debt:

- **SRP Violations:** IBKRClient (634 lines), ORHBreakoutStrategy (9 constructor params), bot.py (orchestration + CLI)
- **Code Duplication:** Duplicate Database classes, market data models, purge logic, path resolution
- **High Coupling:** Config instantiations, hardcoded strategy registration, cross-service dependencies
- **Inconsistent Patterns:** Mixed data models, incomplete protocol usage, scattered session management

The redesign introduces **hexagonal architecture** with **event-driven strategies**:
- **Domain Core:** Pure Python models and business logic (no infrastructure deps)
- **Application Layer:** Use cases, commands, services, event bus
- **Infrastructure Layer:** Adapters for brokers, databases, notifications
- **DI Container:** Centralized dependency management
- **Strategy Registry:** Plugin system for dynamic strategy loading

**Expected Benefits:**
- 30% reduction in code duplication
- New strategies addable in <30 minutes vs 2 hours
- Multi-broker support via factory pattern
- Test coverage >85%
- Clear separation of concerns

---

## Current Architecture Issues

### 1. Single Responsibility Violations (High Priority)

| File | Lines | Responsibilities | Should Be |
|-------|--------|------------------|------------|
| `trading/brokers/ibkr_client.py` | 634 | Auth, connection, retry, keepalive, logging, account info | 4 classes: AuthManager, ConnectionManager, RequestClient, IBKRClient (facade) |
| `trading/strategies/orh_breakout/orh_breakout.py` | 370 | Scan orchestration, range tracking, trading, managing, alerting, health checks | Strategy + domain objects (GapScanner, RangeTracker, Trader) |
| `trading/core/bot.py` | 301 | TradingBot orchestrator + CLI parsing (84 lines) | TradingBot (orchestrator) + CLI (separate module) |

### 2. Code Duplication (Medium Priority)

| Duplication | Locations | Impact |
|-------------|-------------|---------|
| Database connection management | `trading/data/database.py`, `shared/historical/repository.py` | 100% duplicate code |
| Market data models | `trading/data/models.py` (dataclass), `trading/validation/scanners.py` (Pydantic) | Two representations, conversion logic |
| purge_candidates logic | `trading/core/bot.py`, `trading/strategies/orh_breakout/orh_breakout.py` | Identical error handling |
| Database path resolution | `trading/core/config.py`, `shared/database.py` | Same logic duplicated |

### 3. High Coupling

- IBKRClient creates Config internally (line 79: `Config.from_env()`)
- ORHBreakoutStrategy takes 9 constructor parameters
- IBKROrders depends on both Client and MarketDataProvider
- Strategy registration hardcoded in `_register_strategies()`
- Config instantiated in multiple places

### 4. High Cyclomatic Complexity

- `IBKRClient._request()`: 182 lines, nested conditions for auth, retry, status codes
- `bot.run()`: 36 lines, 9-way if-elif chain for CLI commands

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │ Commands │  │ Services  │  │ DI Container │        │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘        │
└───────┼─────────────┼────────────────┼───────────────────┘
        │             │                │
        ▼             ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Domain Layer (Hexagon Core)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │ Models   │  │Strategies│  │ Repositories │        │
│  └──────────┘  └────┬─────┘  └──────┬───────┘        │
└────────────────────────┼──────────────────────┼───────────────────┘
                     │                      │
                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                Infrastructure Layer (Adapters)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐        │
│  │ Database │  │ Brokers   │  │ Notifications│        │
│  └──────────┘  └──────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### New Directory Structure

```
src/skim/
├── domain/                    # Domain layer (hexagon core)
│   ├── models/               # Unified domain models
│   │   ├── __init__.py
│   │   ├── ticker.py         # Ticker value object
│   │   ├── price.py          # Price value object
│   │   ├── position.py       # Position domain model
│   │   ├── candidate.py      # Candidate domain model
│   │   ├── signal.py         # Signal domain model
│   │   └── event.py         # Event domain model
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract Strategy interface (event-driven)
│   │   ├── context.py        # StrategyContext dataclass
│   │   └── registry.py      # Strategy discovery/registration
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py         # Generic repository protocol
│   │   ├── candidate.py     # CandidateRepository protocol
│   │   └── position.py      # PositionRepository protocol
│   └── services/
│       ├── __init__.py
│       ├── signal_service.py  # Signal generation/aggregation
│       └── filter_service.py # Historical performance filtering
│
├── infrastructure/           # Adapters layer
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py      # Unified session manager
│   │   ├── base.py        # BaseDatabase class (extracted)
│   │   ├── models.py       # SQLAlchemy models (infrastructure-specific)
│   │   └── repositories/  # Repository implementations
│   │       ├── candidate.py
│   │       └── position.py
│   ├── brokers/
│   │   ├── __init__.py
│   │   ├── protocols.py    # Broker interfaces (MarketDataProvider, OrderManager, etc.)
│   │   ├── factory.py     # Broker factory for multi-broker support
│   │   └── ibkr/
│   │       ├── __init__.py
│   │       ├── auth.py      # IBKRAuthManager (extracted)
│   │       ├── client.py    # IBKRConnectionManager (extracted)
│   │       ├── requests.py  # IBKRRequestClient (extracted)
│   │       ├── facade.py    # IBKRClient facade (simplified)
│   │       ├── orders.py
│   │       ├── market_data.py
│   │       └── scanner.py
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── base.py        # NotificationService protocol
│   │   └── discord.py     # Discord implementation
│   └── data_sources/
│       ├── __init__.py
│       ├── historical.py
│       └── cooltrader.py
│
├── application/              # Application/use case layer
│   ├── __init__.py
│   ├── commands/            # Command pattern for CLI operations
│   │   ├── __init__.py
│   │   ├── base.py         # Command base class
│   │   ├── scan.py         # ScanCommand
│   │   ├── trade.py        # TradeCommand
│   │   ├── manage.py       # ManageCommand
│   │   ├── purge.py        # PurgeCommand
│   │   └── status.py       # StatusCommand
│   ├── services/
│   │   ├── __init__.py
│   │   ├── trading_service.py  # Main orchestrator
│   │   ├── monitor_service.py  # Position monitoring
│   │   └── command_dispatcher.py # CLI command dispatch
│   ├── events/
│   │   ├── __init__.py
│   │   ├── event_bus.py    # Central event bus
│   │   └── handlers.py    # Event handlers
│   └── dto/               # Data transfer objects
│       └── __init__.py
│
├── trading/                 # Trading module (existing entry points)
│   ├── __init__.py
│   └── cli.py            # CLI entry point (simplified)
│
├── analysis/                # Analysis module (existing entry points)
│   ├── __init__.py
│   └── cli.py            # CLI entry point (simplified)
│
└── shared/                  # Shared utilities
    ├── __init__.py
    ├── config.py            # Centralized Config (singleton)
    ├── logging.py           # Logging configuration
    ├── exceptions.py        # Custom exceptions (consolidated)
    └── container.py        # DI container
```

---

## Implementation Phases

### Phase 1: Break Down Large Classes (Week 1-2)
**Priority: HIGH** - Addresses most critical SRP violations

#### 1.1 Split IBKRClient (634 lines → 4 classes, ~500 lines total)

**Tasks:**
1. Create `infrastructure/brokers/ibkr/auth.py` (IBKRAuthManager, ~150 lines)
   - Extract OAuth LST generation (lines 322-348 from ibkr_client.py)
   - Extract LST expiration check (lines 624-633)
   - Methods: `generate_lst()`, `is_expiring()`

2. Create `infrastructure/brokers/ibkr/connection.py` (IBKRConnectionManager, ~120 lines)
   - Extract session initialization (lines 174-278)
   - Extract disconnect logic (lines 279-297)
   - Extract keepalive thread (lines 382-419)
   - Methods: `connect()`, `disconnect()`, `is_connected()`, `get_account()`

3. Create `infrastructure/brokers/ibkr/requests.py` (IBKRRequestClient, ~200 lines)
   - Extract HTTP request logic (lines 423-604)
   - Extract OAuth signature building (lines 467-502)
   - Extract retry logic (lines 544-597)
   - Methods: `request()`, `_build_oauth_signature()`, `_handle_retryable_error()`

4. Refactor `infrastructure/brokers/ibkr/facade.py` (IBKRClient, ~100 lines)
   - Create facade that delegates to auth, connection, request_client
   - Maintain backward-compatible interface
   - Methods: `connect()`, `disconnect()`, `get_account()`, `get()`, `post()`

5. Update imports in:
   - `trading/core/bot.py`
   - `trading/brokers/ibkr_orders.py`
   - `trading/brokers/ibkr_market_data.py`
   - `trading/brokers/ibkr_gap_scanner.py`

6. Update tests:
   - `tests/trading/test_ibkr_client.py`
   - Mock IBKRAuthManager, IBKRConnectionManager, IBKRRequestClient separately

**Acceptance Criteria:**
- [ ] IBKRClient file < 150 lines
- [ ] No class > 250 lines in new structure
- [ ] All existing tests pass
- [ ] No functionality lost

---

#### 1.2 Simplify ORHBreakoutStrategy Constructor (9 params → 1 context)

**Tasks:**
1. Create `domain/strategies/context.py`
   - Define `StrategyContext` dataclass with all dependencies
   - Fields: market_data, order_service, scanner_service, repository, notifier, config, historical_service

2. Update `trading/strategies/orh_breakout/orh_breakout.py`:
   - Change constructor to `__init__(self, context: StrategyContext)`
   - Update internal references to `self.ctx.market_data`, etc.

3. Update `trading/core/bot.py`:
   - Create StrategyContext when instantiating strategy
   - Pass context instead of individual dependencies

4. Update tests to use context

**Acceptance Criteria:**
- [ ] Strategy constructor takes single parameter
- [ ] No functionality lost
- [ ] All tests pass

---

#### 1.3 Extract CLI from bot.py (301 lines → 120 lines bot + 180 lines CLI)

**Tasks:**
1. Create `application/commands/base.py`
   - Define Command base dataclass
   - Define ScanCommand, TradeCommand, ManageCommand, PurgeCommand, StatusCommand

2. Create `application/services/command_dispatcher.py`
   - Create CommandDispatcher class
   - Implement `dispatch(argv: list[str])` method
   - Use dictionary mapping for command → handler
   - Extract logic from bot.py lines 246-281

3. Refactor `trading/core/bot.py`:
   - Remove main() function
   - Keep only TradingBot class (lines 27-216)
   - Remove CLI-specific logic

4. Create `trading/cli.py`:
   - Move main() function from bot.py
   - Import CommandDispatcher
   - Wire up TradingBot and CommandDispatcher

5. Update `pyproject.toml` entry points
   - Change entry point to `skim.trading.cli:main`

6. Update tests:
   - Split bot tests into bot tests and CLI tests

**Acceptance Criteria:**
- [ ] bot.py < 150 lines (only TradingBot class)
- [ ] trading/cli.py contains CLI logic
- [ ] CommandDispatcher uses dictionary dispatch (no if-elif chain)
- [ ] All tests pass

---

### Phase 2: Build Domain Core (Week 3-4)
**Priority: HIGH** - Foundation for event-driven architecture

#### 2.1 Create Unified Domain Models

**Tasks:**
1. Create `domain/models/ticker.py`
   - Ticker value object (frozen dataclass)
   - Validation: non-empty string

2. Create `domain/models/price.py`
   - Price value object (frozen dataclass)
   - Fields: value (float), timestamp (datetime)
   - Property: is_valid

3. Create `domain/models/position.py`
   - Position domain model
   - Use Ticker and Price value objects
   - Properties: is_open, pnl

4. Create `domain/models/candidate.py`
   - Candidate base class
   - GapCandidate, NewsCandidate subclasses
   - Use Ticker value object

5. Create `domain/models/signal.py`
   - Signal domain model
   - Fields: ticker, action, quantity, price, reason
   - Use Ticker and Price value objects

6. Create `domain/models/event.py`
   - Event domain model
   - EventType enum (MARKET_DATA, GAP_SCAN, NEWS_SCAN, OR_TRACKED, STOP_HIT)
   - Event dataclass

**Acceptance Criteria:**
- [ ] All domain models are pure Python (no SQLModel imports)
- [ ] Value objects are frozen dataclasses
- [ ] Domain models have business logic properties
- [ ] No infrastructure dependencies in domain layer

---

#### 2.2 Create Event-Driven Strategy Interface

**Tasks:**
1. Create `domain/strategies/base.py`
   - Define EventType enum
   - Define Event dataclass
   - Define Signal dataclass
   - Define Strategy ABC with:
     - `@property abstract name(self) -> str`
     - `@abstractmethod async on_event(event: Event) -> list[Signal]`
     - `async initialize(self) -> None`
     - `async shutdown(self) -> None`

2. Update existing Strategy base:
   - Deprecate old interface in `trading/strategies/base.py`
   - New code should use `domain.strategies.base.Strategy`

**Acceptance Criteria:**
- [ ] Strategy interface is event-driven
- [ ] Clear separation between events and signals
- [ ] Strategies can be swapped without changing code

---

#### 2.3 Create Strategy Registry (Plugin System)

**Tasks:**
1. Create `domain/strategies/registry.py`
   - StrategyRegistry class
   - Methods: `register(name, factory)`, `get(name, context)`, `list_available()`, `auto_discover(module_path)`
   - Global registry instance
   - `@register_strategy(name)` decorator

2. Register ORHBreakoutStrategy:
   - Update ORHBreakoutStrategy to use new base interface
   - Register in module with `@register_strategy("orh_breakout")`

3. Auto-discovery:
   - Configure registry to auto-discover strategies in `trading.strategies` package

**Acceptance Criteria:**
- [ ] Strategies can be added without modifying bot.py
- [ ] Registry supports manual registration and auto-discovery
- [ ] Decorator-based registration works

---

#### 2.4 Create Repository Protocols

**Tasks:**
1. Create `domain/repositories/base.py`
   - Generic Repository protocol
   - Methods: `add(entity)`, `get(id)`, `update(entity)`, `delete(id)`, `query(spec)`

2. Create `domain/repositories/candidate.py`
   - CandidateRepository protocol
   - Methods: `save(candidate)`, `get_tradeable()`, `get_alertable()`, `purge()`

3. Create `domain/repositories/position.py`
   - PositionRepository protocol
   - Methods: `create(position)`, `get(id)`, `get_open()`, `close(position_id, exit_price, exit_date)`

**Acceptance Criteria:**
- [ ] Repositories are protocol-based
- [ ] No SQLModel imports in domain layer
- [ ] Clear separation between domain and persistence

---

### Phase 3: Build Infrastructure Layer (Week 5-6)
**Priority: MEDIUM** - Eliminates code duplication

#### 3.1 Create Unified Database Layer

**Tasks:**
1. Create `infrastructure/database/base.py`
   - BaseDatabase class
   - Extract common logic: `__init__`, `_create_schema`, `get_session`, `close`

2. Create `infrastructure/database/session.py`
   - SessionManager context manager
   - Handles commit/rollback/cleanup

3. Refactor `trading/data/database.py`:
   - Inherit from BaseDatabase
   - Remove duplicate connection logic
   - Use SessionManager

4. Refactor `shared/historical/repository.py`:
   - Inherit from BaseDatabase
   - Remove duplicate connection logic
   - Use SessionManager

5. Create utility in `shared/database.py`:
   - `get_db_path(filename: str)` function
   - Single source for all database path resolution

6. Update all usages:
   - Replace duplicated path resolution with utility function

**Acceptance Criteria:**
- [ ] No duplicate database connection code
- [ ] All database classes inherit from BaseDatabase
- [ ] Single function for database path resolution
- [ ] SessionManager used everywhere

---

#### 3.2 Create Broker Factory

**Tasks:**
1. Create `infrastructure/brokers/factory.py`
   - BrokerFactory class
   - `create(broker_type: str, config: Config)` method
   - Support "ibkr" type

2. Extract broker creation logic:
   - `_create_ibkr_client(config)` function
   - Wire up IBKRAuthManager, IBKRConnectionManager, IBKRRequestClient, IBKRClient facade

3. Update `trading/core/bot.py`:
   - Use BrokerFactory instead of direct instantiation
   - Make broker type configurable

**Acceptance Criteria:**
- [ ] Brokers created via factory
- [ ] Factory supports "ibkr" type
- [ ] Easy to add new broker types

---

#### 3.3 Unify Market Data Models

**Tasks:**
1. Consolidate models:
   - Choose dataclass representation (not Pydantic)
   - Update `trading/validation/scanners.py` to use dataclass models
   - Remove duplicate Pydantic models

2. Update imports:
   - All code uses unified models from `domain/models/`

3. Remove conversion logic:
   - Eliminate mapping between Pydantic and dataclass representations

**Acceptance Criteria:**
- [ ] Single representation for each domain concept
- [ ] No Pydantic models in domain layer
- [ ] No conversion logic needed

---

### Phase 4: Build Application Layer (Week 7-8)
**Priority: MEDIUM** - Implements event-driven architecture

#### 4.1 Create Event Bus

**Tasks:**
1. Create `application/events/event_bus.py`
   - EventBus class
   - Methods: `subscribe(event_type, handler)`, `publish(event)`, `start()`, `stop()`
   - Async event queue processing
   - Error handling in handlers

2. Create `application/events/handlers.py`
   - Event handler functions
   - Handlers for: GAP_SCAN_RESULT, NEWS_SCAN_RESULT, MARKET_DATA, STOP_HIT

3. Wire up subscriptions:
   - Strategies subscribe to relevant events
   - Monitor subscribes to MARKET_DATA
   - Order service subscribes to signals

**Acceptance Criteria:**
- [ ] Event bus processes events asynchronously
- [ ] Strategies emit/receive events
- [ ] Error handling doesn't stop event processing

---

#### 4.2 Create Trading Service (Orchestrator)

**Tasks:**
1. Create `application/services/trading_service.py`
   - TradingService class
   - Methods: `scan()`, `track_ranges()`, `alert()`, `trade()`, `manage()`
   - Event-driven: publish events, listen for signals

2. Implement phases:
   - `scan()`: Run gap/news scanners, publish events
   - `track_ranges()`: Track opening ranges, publish events
   - `trade()`: Execute signals from strategy
   - `manage()`: Monitor positions, handle stops

3. Use event bus:
   - TradingService subscribes strategies to events
   - TradingService processes signals from strategies

**Acceptance Criteria:**
- [ ] TradingService orchestrates via events
- [ ] Strategies emit signals, not direct calls
- [ ] Clear separation between orchestration and strategy logic

---

#### 4.3 Create Command Handlers

**Tasks:**
1. Implement `application/commands/scan.py`
   - ScanCommand handler
   - Calls TradingService.scan()

2. Implement `application/commands/trade.py`
   - TradeCommand handler
   - Calls TradingService.trade()

3. Implement other command handlers:
   - ManageCommand, PurgeCommand, StatusCommand

4. Update CommandDispatcher:
   - Wire up command handlers to TradingService methods

**Acceptance Criteria:**
- [ ] Each command has dedicated handler
- [ ] CommandDispatcher uses handlers, not direct calls
- [ ] Clear command → handler mapping

---

### Phase 5: Build DI Container (Week 9)
**Priority: HIGH** - Enables loose coupling

#### 5.1 Create DI Container

**Tasks:**
1. Create `shared/container.py`
   - DIContainer class
   - Methods: `register_factory(factory)`, `register_singleton(instance, cls)`, `get(cls)`
   - Auto-wiring for dependencies

2. Register core services:
   - Config (singleton)
   - BaseDatabase
   - EventBus
   - StrategyRegistry
   - BrokerFactory
   - MarketDataProvider
   - OrderManager
   - CandidateRepository
   - PositionRepository

3. Implement lazy initialization:
   - Services created on first use
   - Singletons maintained

**Acceptance Criteria:**
- [ ] All services resolve from container
- [ ] Container handles dependency graph
- [ ] Singleton services are singletons

---

### Phase 6: Migration & Cleanup (Week 10)
**Priority: MEDIUM** - Completes transition

#### 6.1 Migrate ORH Strategy to New Architecture

**Tasks:**
1. Update ORHBreakoutStrategy:
   - Implement event-driven interface
   - Subscribe to GAP_SCAN_RESULT, NEWS_SCAN_RESULT events
   - Emit signals instead of calling services directly

2. Update orchestration:
   - TradingService publishes events
   - ORHBreakoutStrategy processes events, returns signals

**Acceptance Criteria:**
- [ ] ORH strategy is fully event-driven
- [ ] No direct service calls from strategy
- [ ] All tests pass

---

#### 6.2 Update All Tests

**Tasks:**
1. Update unit tests:
   - Mock new abstractions (AuthManager, ConnectionManager, etc.)
   - Test in isolation

2. Update integration tests:
   - Use DI container for test setup
   - Test full workflows

3. Add new tests:
   - Event bus tests
   - Strategy registry tests
   - DI container tests

**Acceptance Criteria:**
- [ ] Test coverage >85% (trading/shared)
- [ ] All tests pass
- [ ] No test dependencies on implementation details

---

#### 6.3 Remove Deprecated Code

**Tasks:**
1. Remove duplicate code:
   - Old database implementations
   - Duplicate market data models
   - Duplicate purge logic

2. Remove deprecated classes:
   - Old Strategy base (if unused)
   - Old CLI logic in bot.py

3. Update imports:
   - Remove unused imports
   - Update to use new abstractions

4. Update documentation:
   - Update AGENTS.md
   - Update README
   - Add architecture documentation

**Acceptance Criteria:**
- [ ] No code duplication
- [ ] All imports resolve to correct locations
- [ ] Documentation updated

---

## Success Metrics

### Code Quality
- **Lines of Code:** -30% (9,722 → ~6,800)
- **Max File Size:** <300 lines (currently 922 in data_downloader.py)
- **Cyclomatic Complexity:** <15 per method (currently 182 in _request)
- **Test Coverage:** >85% (trading/shared) (currently unknown)

### Maintainability
- **New Strategy Addition:** <30 minutes (currently ~2 hours)
- **Strategy Constructor Parameters:** 1 context object (currently 9)
- **Broker Addition:** Implement 2 protocols (currently requires changing multiple files)
- **Configuration Loading:** Single Config singleton (currently instantiated in multiple places)

### Architecture
- **Domain Layer:** Pure Python, zero infrastructure dependencies
- **Adapters:** Swappable (IBKR → other brokers via factory)
- **Events:** Decoupled communication via event bus
- **Registry:** Plugin-based strategies (no code changes needed)
- **DI:** Centralized dependency management

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Comprehensive test suite, incremental migration, feature flags |
| Long migration period | Phased approach, each phase delivers value |
| Learning curve | Team training, documentation, code reviews |
| Performance regression | Benchmark before/after, event bus optimization |
| Test coverage gaps | Parallel test writing, integration tests |

---

## Dependencies & Prerequisites

### Required Tools
- uv (already in use)
- pytest (already in use)
- ruff (already in use)
- pre-commit (already in use)

### External Libraries
- sqlmodel (already in use)
- httpx (already in use)
- loguru (already in use)
- No new dependencies required

---

## Next Steps

1. **Review and Approve:** Review this plan with team, address questions/concerns
2. **Create Issue Tracking:** Create GitHub issues for each phase
3. **Assign Work:** Delegate phases to agents/stakeholders
4. **Establish Cadence:** Weekly syncs to track progress
5. **Begin Phase 1:** Start with IBKRClient split (highest priority)

---

## Questions for Clarification

Before beginning implementation, please clarify:

1. **Timeline:** Is 10 weeks acceptable, or do you need faster/slower delivery?
2. **Backward Compatibility:** Should old CLI commands remain functional during migration?
3. **Test Requirements:** Do you have specific test coverage targets?
4. **Deployment:** Is this a greenfield migration (new code) or brownfield (refactor existing)?
5. **Team Size:** How many developers will work on this in parallel?

---

## Appendix: File Changes Summary

### Files to Create (New)
- `domain/models/*` - 7 files
- `domain/strategies/*` - 4 files
- `domain/repositories/*` - 3 files
- `infrastructure/database/*` - 4 files
- `infrastructure/brokers/ibkr/*` - 6 files
- `infrastructure/brokers/factory.py` - 1 file
- `infrastructure/notifications/base.py` - 1 file
- `application/commands/*` - 6 files
- `application/services/*` - 3 files
- `application/events/*` - 2 files
- `shared/container.py` - 1 file
- `trading/cli.py` - 1 file

**Total New Files: ~40**

### Files to Refactor
- `trading/brokers/ibkr_client.py` - Split into 4 files
- `trading/strategies/orh_breakout/orh_breakout.py` - Update constructor
- `trading/core/bot.py` - Remove CLI, simplify
- `trading/data/database.py` - Inherit from BaseDatabase
- `shared/historical/repository.py` - Inherit from BaseDatabase
- `trading/validation/scanners.py` - Unify models
- `trading/scanners/*` - Update to use new abstractions
- `trading/data/repositories/*` - Implement protocols

### Files to Delete
- Duplicate code will be removed in Phase 6

---

**End of Plan**
