"""Ticker value object"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticker:
    """Value object for ticker symbol"""

    symbol: str

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("Ticker symbol cannot be empty")

    def __str__(self) -> str:
        return self.symbol

    @classmethod
    def from_persistence(cls, value: str) -> "Ticker":
        return cls(symbol=value)

    def to_persistence(self) -> str:
        return self.symbol
