from loguru import logger

from skim.application.commands.base import ScanCommand


async def handle_scan(trading_bot, command: ScanCommand) -> int:
    """Execute strategy scan phase

    Args:
        trading_bot: TradingBot instance
        command: ScanCommand with optional strategy

    Returns:
        Exit code (0 for success, 1 for error)
    """
    strategy = command.strategy or "orh_breakout"
    logger.info(f"Starting scan for strategy: {strategy}")
    try:
        result = await trading_bot.scan(strategy)
        logger.info(f"Scan completed. Found {result} candidates")
        return 0
    except ValueError as e:
        logger.error(f"Strategy error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)
        return 1
