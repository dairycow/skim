# Agent Task: Infrastructure Builder
## Phase: 3
## Priority: MEDIUM

### Objective
Build infrastructure layer with unified database, broker factory, and consolidated models.

### Reference Files
- `src/skim/trading/data/database.py` (existing)
- `src/skim/shared/historical/repository.py` (existing)
- `src/skim/trading/brokers/ibkr_client.py` (Phase 1.1 will have split this)
- `src/skim/trading/validation/scanners.py` (duplicate models)

### New Infrastructure Layer Structure
```
src/skim/infrastructure/
├── __init__.py
├── database/
│   ├── __init__.py
│   ├── base.py        # BaseDatabase class
│   ├── session.py     # SessionManager
│   └── repositories/  # Repository implementations
│       ├── __init__.py
│       ├── candidate.py
│       └── position.py
├── brokers/
│   ├── __init__.py
│   ├── protocols.py   # Broker interfaces (existing, move here)
│   ├── factory.py     # BrokerFactory
│   └── ibkr/          # (From Phase 1.1)
│       ├── __init__.py
│       ├── auth.py
│       ├── connection.py
│       ├── requests.py
│       └── facade.py
└── notifications/
    ├── __init__.py
    ├── base.py        # NotificationService protocol
    └── discord.py     # (existing, move here)
```

### Tasks

#### 3.1 Create Unified Database Layer

##### 3.1.1 Create `infrastructure/database/base.py`
Extract common database connection logic:

```python
from sqlmodel import SQLModel, create_engine, Session

class BaseDatabase:
    """Base database class with common connection logic"""
    
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False}
        )
        self._create_schema()
    
    def _create_schema(self) -> None:
        """Create tables (override in subclasses)"""
        SQLModel.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return Session(self.engine)
    
    def close(self) -> None:
        """Dispose of engine"""
        if self.engine:
            self.engine.dispose()
```

##### 3.1.2 Create `infrastructure/database/session.py`
```python
from contextlib import contextmanager
from typing import Generator

class SessionManager:
    """Context manager for database sessions"""
    
    def __init__(self, database: BaseDatabase) -> None:
        self.database = database
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager for session with auto commit/rollback"""
        sess = self.database.get_session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()
```

##### 3.1.3 Refactor `trading/data/database.py`
```python
from infrastructure.database import BaseDatabase

class Database(BaseDatabase):
    """Trading database (inherits common logic)"""
    
    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)
        # Trading-specific table creation if needed
    
    def purge_candidates(self, ...) -> int:
        # Existing implementation, uses get_session()
        ...
```

##### 3.1.4 Refactor `shared/historical/repository.py`
- Inherit from BaseDatabase
- Remove duplicate connection logic

##### 3.1.5 Create `shared/database.py` utility
```python
from pathlib import Path

def get_db_path(filename: str) -> Path:
    """Get database path - single source for all database paths"""
    production_path = Path("/opt/skim/data") / filename
    if production_path.parent.exists():
        return production_path
    
    project_root = Path(__file__).parent.parent.parent
    local_path = project_root / "data" / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)
    return local_path
```

#### 3.2 Create Broker Factory

##### 3.2.1 Create `infrastructure/brokers/factory.py`
```python
from typing import Protocol
from skim.trading.core.config import Config

class BrokerFactory:
    """Factory for creating broker clients"""
    
    @staticmethod
    def create(broker_type: str, config: Config) -> "BrokerConnectionManager":
        """Create broker client by type"""
        if broker_type == "ibkr":
            return _create_ibkr_client(config)
        elif broker_type == "demo":
            return _create_demo_broker(config)
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")

def _create_ibkr_client(config: Config):
    """Create IBKR client with all dependencies"""
    from infrastructure.brokers.ibkr import (
        IBKRAuthManager,
        IBKRConnectionManager,
        IBKRRequestClient,
        IBKRClientFacade
    )
    
    auth = IBKRAuthManager(config)
    connection = IBKRConnectionManager(auth)
    requests = IBKRRequestClient(auth)
    
    return IBKRClientFacade(
        auth=auth,
        connection=connection,
        requests=requests,
        paper_trading=config.paper_trading
    )
```

#### 3.3 Unify Market Data Models

##### 3.3.1 Consolidate Models
- Choose dataclass representation (not Pydantic)
- Use models from `domain/models/`
- Update `trading/validation/scanners.py` to use domain models
- Remove duplicate Pydantic models

##### 3.3.2 Update `trading/validation/scanners.py`
```python
# Remove Pydantic model definitions
# Use imports from domain.models:
from domain.models import GapCandidate, NewsCandidate
```

#### 3.4 Move Broker Protocols

##### 3.4.1 Move protocols to infrastructure
- Move `trading/brokers/protocols.py` to `infrastructure/brokers/protocols.py`
- Update imports in dependent files

### Acceptance Criteria
- [ ] No duplicate database connection code
- [ ] All database classes inherit from BaseDatabase
- [ ] Single function for database path resolution
- [ ] SessionManager used everywhere
- [ ] BrokerFactory supports IBKR type
- [ ] Unified market data models
- [ ] No Pydantic models in domain layer

### Steps to Complete
1. Create BaseDatabase and SessionManager
2. Refactor trading/data/database.py to inherit from BaseDatabase
3. Refactor shared/historical/repository.py
4. Create get_db_path utility
5. Create BrokerFactory
6. Consolidate market data models
7. Move broker protocols
8. Update all imports
9. Run tests
10. Commit with message: `feat(infrastructure): add unified database and broker factory`

### Notes
- Be careful with import cycles when moving files
- Update all import statements in dependent files
- Keep backward compatibility where possible
