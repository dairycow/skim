"""Tests for strategy registry"""

import pytest
from unittest.mock import MagicMock

from skim.domain.strategies.context import StrategyContext
from skim.domain.strategies.registry import (
    StrategyRegistry,
    registry,
    register_strategy,
)
from skim.domain.strategies.base import Strategy, Event, EventType


class MockStrategy(Strategy):
    """Mock strategy for testing"""

    def __init__(self, name: str = "mock"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def scan(self) -> int:
        return 0

    async def trade(self) -> int:
        return 0

    async def manage(self) -> int:
        return 0


class TestStrategyRegistry:
    """Tests for StrategyRegistry"""

    def setup_method(self):
        """Create fresh registry for each test"""
        self.test_registry = StrategyRegistry()

    def test_register_strategy(self):
        """Test registering a strategy"""
        factory = lambda ctx: MockStrategy("test")
        self.test_registry.register("test", factory)

        assert "test" in self.test_registry.list_available()

    def test_get_strategy(self):
        """Test retrieving a registered strategy"""
        context = MagicMock(spec=StrategyContext)
        factory = lambda ctx: MockStrategy("get_test")
        self.test_registry.register("get_test", factory)

        strategy = self.test_registry.get("get_test", context)

        assert strategy.name == "get_test"

    def test_get_unknown_strategy_raises(self):
        """Test that getting unknown strategy raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            self.test_registry.get("unknown", MagicMock())

        assert "Unknown strategy: unknown" in str(exc_info.value)

    def test_list_available(self):
        """Test listing available strategies"""
        self.test_registry.register(
            "strat1", lambda ctx: MockStrategy("strat1")
        )
        self.test_registry.register(
            "strat2", lambda ctx: MockStrategy("strat2")
        )

        available = self.test_registry.list_available()

        assert len(available) == 2
        assert "strat1" in available
        assert "strat2" in available


class TestRegisterStrategyDecorator:
    """Tests for @register_strategy decorator"""

    def test_decorator_registers_strategy(self):
        """Test that decorator registers strategy"""
        # Create a fresh registry for this test
        local_registry = StrategyRegistry()

        # Patch the global registry temporarily
        import skim.domain.strategies.registry as reg_module

        original_registry = reg_module.registry
        reg_module.registry = local_registry

        try:
            # Define a strategy with decorator
            @reg_module.register_strategy("decorated_test")
            class DecoratedStrategy(Strategy):
                @property
                def name(self) -> str:
                    return "decorated_test"

                async def scan(self) -> int:
                    return 0

                async def trade(self) -> int:
                    return 0

                async def manage(self) -> int:
                    return 0

            assert "decorated_test" in local_registry.list_available()
        finally:
            reg_module.registry = original_registry


class TestGlobalRegistry:
    """Tests for global registry"""

    def test_global_registry_exists(self):
        """Test that global registry is instantiated"""
        assert registry is not None
        assert isinstance(registry, StrategyRegistry)
