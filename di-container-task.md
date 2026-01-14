# Agent Task: DI Container Builder
## Phase: 5
## Priority: HIGH

### Objective
Create dependency injection container for centralized dependency management.

### Reference Files
- All Phase 1-4 output (domain, infrastructure, application layers)

### New File
```
src/skim/shared/
├── __init__.py
├── config.py        # (existing, may need updates)
├── exceptions.py    # (new, consolidate exceptions)
└── container.py     # NEW: DI Container
```

### Tasks

#### 5.1 Consolidate Exceptions

##### 5.1.1 Create `shared/exceptions.py`
Collect all custom exceptions in one place:

```python
# Broker exceptions
class IBKRClientError(Exception):
    """Base exception for IBKR client errors"""
    pass

class IBKRAuthenticationError(IBKRClientError):
    """Raised when OAuth authentication fails"""
    pass

class IBKRConnectionError(IBKRClientError):
    """Raised when connection fails"""
    pass

# Scanner exceptions
class ScannerError(Exception):
    """Base scanner error"""
    pass

class ScannerValidationError(ScannerError):
    """Raised when scanner validation fails"""
    pass

class GapCalculationError(ScannerError):
    """Raised when gap calculation fails"""
    pass

# Trading exceptions
class TradingError(Exception):
    """Base trading error"""
    pass

class OrderError(TradingError):
    """Raised when order fails"""
    pass

# Database exceptions
class DatabaseError(Exception):
    """Base database error"""
    pass

# Repository exceptions
class RepositoryError(Exception):
    """Base repository error"""
    pass
```

#### 5.2 Create DI Container

##### 5.2.1 Create `shared/container.py`
```python
import inspect
from typing import Type, TypeVar, Callable, Any, Dict

T = TypeVar('T')

class DIContainer:
    """Dependency injection container for centralized dependency management"""
    
    def __init__(self, config: Any = None) -> None:
        self._config = config
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}
        
        # Register core services
        self._register_core_services()
    
    def _register_core_services(self) -> None:
        """Register built-in services"""
        # Config is provided externally
        self._singletons[type(self._config)] = self._config
        
        # Database
        self.register_factory(self._create_database)
        
        # Event bus
        self.register_factory(self._create_event_bus)
        
        # Broker
        self.register_factory(self._create_broker)
        
        # Market data
        self.register_factory(self._create_market_data)
        
        # Orders
        self.register_factory(self._create_orders)
        
        # Repositories
        self.register_factory(self._create_candidate_repository)
        self.register_factory(self._create_position_repository)
        
        # Strategy registry
        self.register_factory(self._create_strategy_registry)
        
        # Trading service
        self.register_factory(self._create_trading_service)
    
    def register_factory(self, factory: Callable[[Any], T]) -> Type[T]:
        """Register a factory function"""
        return_type = inspect.signature(factory).return_annotation
        self._factories[return_type] = factory
        return return_type
    
    def register_singleton(self, instance: T, cls: Type[T] | None = None) -> None:
        """Register a singleton instance"""
        if cls is None:
            cls = type(instance)
        self._singletons[cls] = instance
    
    def get(self, cls: Type[T]) -> T:
        """Resolve dependency"""
        # Check singleton first
        if cls in self._singletons:
            return self._singletons[cls]
        
        # Check if already created
        if cls in self._instances:
            return self._instances[cls]
        
        # Use factory
        if cls in self._factories:
            instance = self._factories[cls](self)
            self._instances[cls] = instance
            return instance
        
        raise ValueError(f"Cannot resolve dependency: {cls}")
    
    def _create_database(self, container: "DIContainer") -> Any:
        """Create database instance"""
        from infrastructure.database import BaseDatabase
        from shared.config import get_db_path
        
        db_path = get_db_path("skim.db")
        return BaseDatabase(str(db_path))
    
    def _create_event_bus(self, container: "DIContainer") -> Any:
        """Create event bus instance"""
        from application.events import EventBus
        return EventBus()
    
    def _create_broker(self, container: "DIContainer") -> Any:
        """Create broker instance"""
        from infrastructure.brokers import BrokerFactory
        config = container.get(type(container._config))
        return BrokerFactory.create("ibkr", config)
    
    def _create_market_data(self, container: "DIContainer") -> Any:
        """Create market data provider"""
        # Implementation
        pass
    
    def _create_orders(self, container: "DIContainer") -> Any:
        """Create order manager"""
        # Implementation
        pass
    
    def _create_candidate_repository(self, container: "DIContainer") -> Any:
        """Create candidate repository"""
        # Implementation
        pass
    
    def _create_position_repository(self, container: "DIContainer") -> Any:
        """Create position repository"""
        # Implementation
        pass
    
    def _create_strategy_registry(self, container: "DIContainer") -> Any:
        """Create strategy registry"""
        from domain.strategies import StrategyRegistry
        return StrategyRegistry()
    
    def _create_trading_service(self, container: "DIContainer") -> Any:
        """Create trading service"""
        from application.services import TradingService
        
        return TradingService(
            strategy=container.get(Any),  # Would be resolved by name
            event_bus=container.get(Any),
            db=container.get(Any),
            market_data=container.get(Any),
            orders=container.get(Any),
            config={}
        )
```

#### 5.3 Update `shared/__init__.py`
```python
"""Shared utilities for Skim"""
from .container import DIContainer
from .exceptions import (
    IBKRClientError,
    IBKRAuthenticationError,
    IBKRConnectionError,
    ScannerError,
    TradingError,
    OrderError,
    DatabaseError,
)

__all__ = [
    "DIContainer",
    "IBKRClientError",
    "IBKRAuthenticationError",
    "IBKRConnectionError",
    "ScannerError",
    "TradingError",
    "OrderError",
    "DatabaseError",
]
```

### Acceptance Criteria
- [ ] All services resolve from container
- [ ] Container handles dependency graph
- [ ] Singleton services are singletons
- [ ] Exceptions consolidated in one place
- [ ] No circular dependencies

### Steps to Complete
1. Create shared/exceptions.py
2. Create shared/container.py
3. Implement all factory methods
4. Test container resolution
5. Commit with message: `feat(di): add dependency injection container`

### Notes
- Container should be stateless after configuration
- Consider making container immutable after startup
- Lazy initialization is good for expensive resources
