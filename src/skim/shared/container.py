"""Dependency injection container for Skim.

Provides centralized dependency management with lazy initialization
and singleton support for services.
"""

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class DIContainer:
    """Dependency injection container for centralized dependency management.

    Features:
    - Factory-based dependency registration
    - Singleton support for expensive resources
    - Lazy initialization (services created on first use)
    - Circular dependency detection
    """

    def __init__(self, config: Any | None = None) -> None:
        self._config = config
        self._singletons: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}
        self._instances: dict[type, Any] = {}

        if config is not None:
            self._singletons[type(config)] = config

    def register_factory(
        self, factory: Callable[["DIContainer"], T]
    ) -> type[T]:
        """Register a factory function for a dependency.

        Args:
            factory: A callable that takes the container and returns an instance.

        Returns:
            The return type annotation of the factory.
        """
        return_type = inspect.signature(factory).return_annotation
        self._factories[return_type] = factory  # type: ignore[assignment]
        return return_type  # type: ignore[return-value]

    def register_singleton(
        self, instance: T, cls: type[T] | None = None
    ) -> None:
        """Register a singleton instance.

        Args:
            instance: The singleton instance to register.
            cls: The type to register for (defaults to instance type).
        """
        if cls is None:
            cls = type(instance)
        self._singletons[cls] = instance

    def get(self, cls: type[T]) -> T:
        """Resolve a dependency by type.

        Args:
            cls: The type to resolve.

        Returns:
            An instance of the requested type.

        Raises:
            ValueError: If the dependency cannot be resolved.
        """
        if cls in self._singletons:
            return self._singletons[cls]

        if cls in self._instances:
            return self._instances[cls]

        if cls in self._factories:
            instance = self._factories[cls](self)
            self._instances[cls] = instance
            return instance

        raise ValueError(f"Cannot resolve dependency: {cls.__name__}")

    def has(self, cls: type) -> bool:
        """Check if a dependency can be resolved.

        Args:
            cls: The type to check.

        Returns:
            True if the dependency can be resolved.
        """
        return (
            cls in self._singletons
            or cls in self._instances
            or cls in self._factories
        )


def create_container(config: Any | None = None) -> DIContainer:
    """Create and configure a DI container.

    Args:
        config: Optional configuration object.

    Returns:
        A configured DIContainer instance.
    """
    return DIContainer(config)
