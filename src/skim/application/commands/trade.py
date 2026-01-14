from loguru import logger

from skim.application.commands.base import TradeCommand


async def handle_trade(trading_bot, command: TradeCommand) -> int:
    """Execute breakout entries

    Args:
        trading_bot: TradingBot instance
        command: TradeCommand with optional strategy

    Returns:
        Exit code (0 for success, 1 for error)
    """
    strategy = command.strategy or "orh_breakout"
    logger.info(f"Starting trade for strategy: {strategy}")
    try:
        result = await trading_bot.trade(strategy)
        logger.info(f"Trade completed. Executed {result} trades")
        return 0
    except ValueError as e:
        logger.error(f"Strategy error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Trade failed: {e}", exc_info=True)
        return 1
