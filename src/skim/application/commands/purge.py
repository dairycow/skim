from datetime import date

from loguru import logger

from skim.application.commands.base import PurgeCommand


async def handle_purge(trading_bot, command: PurgeCommand) -> int:
    """Clear candidate rows before a scan

    Args:
        trading_bot: TradingBot instance
        command: PurgeCommand with optional cutoff date

    Returns:
        Exit code (0 for success, 1 for error)
    """
    cutoff = None
    if command.cutoff_date:
        try:
            cutoff = date.fromisoformat(command.cutoff_date)
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD for cutoff.")
            return 1

    logger.info("Purging candidates...")
    try:
        result = await trading_bot.purge_candidates(cutoff)
        logger.info(f"Deleted {result} candidate rows")
        return 0
    except Exception as e:
        logger.error(f"Candidate purge failed: {e}", exc_info=True)
        return 1
