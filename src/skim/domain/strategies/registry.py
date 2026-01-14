"""Strategy registry for managing strategy factories"""

from collections.abc import Callable

from skim.domain.strategies.base import Strategy
from skim.domain.strategies.context import StrategyContext


class StrategyRegistry:
    """Registry for managing strategy factories and instances.

    This class provides a central registry for strategies,
    allowing dynamic strategy discovery and instantiation.
    """

    def __init__(self):
        self._factories: dict[str, Callable[[StrategyContext], Strategy]] = {}

    def register(
        self, name: str, factory: Callable[[StrategyContext], Strategy]
    ) -> None:
        """Register a strategy factory.

        Args:
            name: Strategy identifier
            factory: Factory function that creates strategy instances
        """
        self._factories[name] = factory

    def get(self, name: str, context: StrategyContext) -> Strategy:
        """Get a strategy instance by name.

        Args:
            name: Strategy identifier
            context: Strategy context with dependencies

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy not found
        """
        if name not in self._factories:
            raise ValueError(
                f"Unknown strategy: {name}. "
                f"Available strategies: {self.list_available()}"
            )
        return self._factories[name](context)

    def list_available(self) -> list[str]:
        """List all available strategy names.

        Returns:
            List of strategy identifiers
        """
        return list(self._factories.keys())


def register_strategy(name: str) -> Callable:
    """Decorator to register a strategy factory.

    Args:
        name: Strategy identifier

    Returns:
        Decorator function
    """

    def decorator(
        factory: Callable[[StrategyContext], Strategy],
    ) -> Callable[[StrategyContext], Strategy]:
        registry.register(name, factory)
        return factory

    return decorator


registry = StrategyRegistry()
