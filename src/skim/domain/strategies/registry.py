"""Strategy registry"""

from collections.abc import Callable
from typing import TypeVar

S = TypeVar("S")


class StrategyRegistry(dict[str, type[S]]):
    """Registry for strategy classes"""

    def register(self, name: str) -> Callable[[type[S]], type[S]]:
        def decorator(cls: type[S]) -> type[S]:
            self[name] = cls
            return cls

        return decorator
