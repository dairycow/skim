from dataclasses import dataclass


@dataclass
class Command:
    """Base command class"""

    name: str


@dataclass
class ScanCommand(Command):
    """Scan for trading candidates"""

    strategy: str | None = None


@dataclass
class TradeCommand(Command):
    """Execute breakout entries"""

    strategy: str | None = None


@dataclass
class ManageCommand(Command):
    """Monitor positions and execute stops"""

    strategy: str | None = None


@dataclass
class PurgeCommand(Command):
    """Clear candidate rows before a scan"""

    cutoff_date: str | None = None


@dataclass
class StatusCommand(Command):
    """Perform health check"""

    strategy: str | None = None
