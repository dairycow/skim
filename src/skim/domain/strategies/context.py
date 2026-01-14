"""Strategy context"""

from dataclasses import dataclass


@dataclass
class StrategyContext:
    """Strategy execution context"""

    strategy_name: str
    timestamp: str
