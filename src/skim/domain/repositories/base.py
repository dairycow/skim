"""Generic repository protocol"""

from typing import Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    """Generic repository protocol"""

    def add(self, entity: T) -> None:
        """Add entity to repository"""
        ...

    def get(self, id: int) -> T | None:
        """Get entity by ID"""
        ...

    def update(self, entity: T) -> None:
        """Update entity"""
        ...

    def delete(self, id: int) -> None:
        """Delete entity by ID"""
        ...
