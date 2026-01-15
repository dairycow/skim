"""Persistence handler for ORH strategy events"""

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from skim.domain.models import GapCandidate, NewsCandidate
from skim.domain.models.event import Event
from skim.domain.models.ticker import Ticker
from skim.trading.data.database import Database

if TYPE_CHECKING:
    pass


class StrategyPersistenceHandler:
    """Handles ORH strategy persistence events"""

    def __init__(self, database: Database, repository):
        """Initialize persistence handler

        Args:
            database: Database for position management
            repository: ORHCandidateRepository for candidate management
        """
        self.db = database
        self.repo = repository

    async def handle_candidates_scanned(self, event: Event) -> None:
        """Save scanned candidates to repository

        Args:
            event: Event containing scan results
        """
        try:
            data = event.data or {}
            scanner_name = data.get("scanner_name", "")
            candidates_data = data.get("candidates", [])

            if scanner_name == "gap":
                for candidate_data in candidates_data:
                    candidate = GapCandidate(
                        ticker=Ticker(candidate_data.get("ticker", "")),
                        scan_date=datetime.fromisoformat(
                            candidate_data.get(
                                "scan_date", datetime.now().isoformat()
                            )
                        ),
                        status=candidate_data.get("status", "watching"),
                        gap_percent=candidate_data.get("gap_percent", 0.0),
                        conid=candidate_data.get("conid"),
                    )
                    self.repo.save_gap_candidate(candidate)
                    logger.debug(
                        f"Saved gap candidate: {candidate.ticker.symbol}"
                    )

            elif scanner_name == "news":
                for candidate_data in candidates_data:
                    candidate = NewsCandidate(
                        ticker=Ticker(candidate_data.get("ticker", "")),
                        scan_date=datetime.fromisoformat(
                            candidate_data.get(
                                "scan_date", datetime.now().isoformat()
                            )
                        ),
                        status=candidate_data.get("status", "watching"),
                        headline=candidate_data.get("headline", ""),
                        announcement_type=candidate_data.get(
                            "announcement_type"
                        ),
                        announcement_timestamp=datetime.fromisoformat(
                            candidate_data.get("announcement_timestamp", "")
                        )
                        if candidate_data.get("announcement_timestamp")
                        else None,
                    )
                    self.repo.save_news_candidate(candidate)
                    logger.debug(
                        f"Saved news candidate: {candidate.ticker.symbol}"
                    )

        except Exception as e:
            logger.error(f"Failed to handle candidates scanned event: {e}")

    async def handle_trade_executed(self, event: Event) -> None:
        """Create position from trade event

        Args:
            event: Event containing trade execution details
        """
        try:
            data = event.data or {}
            trade = data.get("trade", {})
            ticker = trade.get("ticker", "")
            quantity = trade.get("quantity", 0)
            price = trade.get("price", 0.0)
            stop_loss = trade.get("stop_loss", price * 0.95)

            if not ticker or quantity <= 0:
                logger.warning(f"Invalid trade data: {trade}")
                return

            self.db.create_position(
                ticker=ticker,
                quantity=quantity,
                entry_price=price,
                stop_loss=stop_loss,
                entry_date=datetime.now(),
            )
            self.db.update_candidate_status(ticker, "entered")

            logger.info(
                f"Created position: {ticker} x {quantity} @ ${price:.2f}"
            )

        except Exception as e:
            logger.error(f"Failed to handle trade executed event: {e}")

    async def handle_stop_hit(self, event: Event) -> None:
        """Close position from stop event

        Args:
            event: Event containing stop hit details
        """
        try:
            data = event.data or {}
            position_data = data.get("position", {})
            ticker = position_data.get("ticker", "")
            exit_price = position_data.get("exit_price", 0.0)

            if not ticker or exit_price <= 0:
                logger.warning(f"Invalid stop hit data: {position_data}")
                return

            positions = self.db.get_open_positions()
            for pos in positions:
                if (
                    pos.ticker.symbol == ticker
                    and pos.is_open
                    and pos.id is not None
                ):
                    self.db.close_position(
                        position_id=pos.id,
                        exit_price=exit_price,
                        exit_date=datetime.now().isoformat(),
                    )
                    logger.info(
                        f"Closed position: {ticker} @ ${exit_price:.2f}"
                    )
                    break

        except Exception as e:
            logger.error(f"Failed to handle stop hit event: {e}")
