from loguru import logger

from skim.application.commands.base import (
    ManageCommand,
    PurgeCommand,
    ScanCommand,
    StatusCommand,
    TradeCommand,
)
from skim.application.commands.manage import handle_manage
from skim.application.commands.purge import handle_purge
from skim.application.commands.scan import handle_scan
from skim.application.commands.status import handle_status
from skim.application.commands.trade import handle_trade


class CommandDispatcher:
    """Dispatches CLI commands to appropriate handlers"""

    def __init__(self, trading_bot) -> None:
        self.trading_bot = trading_bot
        self._handlers = {
            "scan": self._handle_scan,
            "trade": self._handle_trade,
            "manage": self._handle_manage,
            "purge_candidates": self._handle_purge,
            "status": self._handle_status,
        }

    async def dispatch(self, argv: list[str]) -> int:
        """Parse and execute command

        Args:
            argv: Command line arguments (sys.argv)

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if len(argv) < 2:
            self._print_usage()
            return 1

        method = argv[1]
        handler = self._handlers.get(method)

        if handler is None:
            logger.error(f"Unknown method: {method}")
            self._print_usage()
            return 1

        return await handler(argv)

    def _print_usage(self) -> None:
        """Print available commands"""
        logger.error(
            "No method specified. Available: scan, trade, manage, purge_candidates, status"
        )

    async def _handle_scan(self, argv: list[str]) -> int:
        """Handle scan command"""
        strategy = argv[2] if len(argv) > 2 else None
        command = ScanCommand(name="scan", strategy=strategy)
        return await handle_scan(self.trading_bot, command)

    async def _handle_trade(self, argv: list[str]) -> int:
        """Handle trade command"""
        strategy = argv[2] if len(argv) > 2 else None
        command = TradeCommand(name="trade", strategy=strategy)
        return await handle_trade(self.trading_bot, command)

    async def _handle_manage(self, argv: list[str]) -> int:
        """Handle manage command"""
        strategy = argv[2] if len(argv) > 2 else None
        command = ManageCommand(name="manage", strategy=strategy)
        return await handle_manage(self.trading_bot, command)

    async def _handle_purge(self, argv: list[str]) -> int:
        """Handle purge_candidates command"""
        cutoff = argv[2] if len(argv) > 2 else None
        command = PurgeCommand(name="purge_candidates", cutoff_date=cutoff)
        return await handle_purge(self.trading_bot, command)

    async def _handle_status(self, argv: list[str]) -> int:
        """Handle status command"""
        strategy = argv[2] if len(argv) > 2 else None
        command = StatusCommand(name="status", strategy=strategy)
        return await handle_status(self.trading_bot, command)
