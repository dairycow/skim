import asyncio
import sys

from loguru import logger

from skim.application.services.command_dispatcher import CommandDispatcher
from skim.trading.core.bot import TradingBot
from skim.trading.core.config import Config


def main() -> int:
    """CLI entry point for the trading bot

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.add(
        "logs/skim_{time}.log",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        level="INFO",
    )
    logger.info("=" * 60)
    logger.info("SKIM TRADING BOT - MULTI-STRATEGY")
    logger.info("=" * 60)

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    bot = TradingBot(config)
    dispatcher = CommandDispatcher(bot)

    async def run():
        try:
            exit_code = await dispatcher.dispatch(sys.argv)
            return exit_code
        finally:
            if bot.ib_client.is_connected():
                logger.info("Shutting down IBKR connection...")
                await bot.ib_client.disconnect()

    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        logger.warning("Bot stopped manually.")
        return 1
    except Exception as e:
        logger.critical(
            f"Unhandled exception in bot execution: {e}", exc_info=True
        )
        return 1
    finally:
        logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    sys.exit(main())
