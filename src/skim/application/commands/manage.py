from loguru import logger

from skim.application.commands.base import ManageCommand


async def handle_manage(trading_bot, command: ManageCommand) -> int:
    """Monitor positions and execute stops

    Args:
        trading_bot: TradingBot instance
        command: ManageCommand with optional strategy

    Returns:
        Exit code (0 for success, 1 for error)
    """
    strategy = command.strategy or "orh_breakout"
    logger.info(f"Starting manage for strategy: {strategy}")
    try:
        result = await trading_bot.manage(strategy)
        logger.info(f"Manage completed. Managed {result} positions")
        return 0
    except ValueError as e:
        logger.error(f"Strategy error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Manage failed: {e}", exc_info=True)
        return 1
