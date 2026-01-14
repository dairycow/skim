from loguru import logger

from skim.application.commands.base import StatusCommand


async def handle_status(trading_bot, command: StatusCommand) -> int:
    """Perform health check

    Args:
        trading_bot: TradingBot instance
        command: StatusCommand with optional strategy

    Returns:
        Exit code (0 for success, 1 for error)
    """
    strategy = command.strategy or "orh_breakout"
    logger.info(f"Starting status check for strategy: {strategy}")
    try:
        result = await trading_bot.status(strategy)
        if result:
            logger.info("Health check passed")
            return 0
        else:
            logger.error("Health check failed")
            return 1
    except ValueError as e:
        logger.error(f"Strategy error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return 1
