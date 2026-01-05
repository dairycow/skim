"""ORH-specific candidate repository implementation"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import col, delete, select

from skim.data.models import (
    Candidate,
    GapStockInPlay,
    NewsStockInPlay,
    ORHCandidate,
    TradeableCandidate,
)

if TYPE_CHECKING:
    from skim.data.database import Database


class ORHCandidateRepository:
    """Repository for ORH breakout strategy candidates"""

    STRATEGY_NAME = "orh_breakout"

    def __init__(self, db: Database):
        """Initialise ORH repository

        Args:
            db: Database instance for database operations
        """
        self.db = db

    def save_candidate(
        self, candidate: GapStockInPlay | NewsStockInPlay
    ) -> None:
        """Save or update a candidate (generic method for protocol compliance)

        Args:
            candidate: Candidate object to save
        """
        if isinstance(candidate, GapStockInPlay):
            self.save_gap_candidate(candidate)
        elif isinstance(candidate, NewsStockInPlay):
            self.save_news_candidate(candidate)
        else:
            raise ValueError(f"Unknown candidate type: {type(candidate)}")

    def save_gap_candidate(self, candidate: GapStockInPlay) -> None:
        """Save or update a gap candidate

        Args:
            candidate: GapStockInPlay object to save
        """
        with self.db.get_session() as session:
            base_candidate = session.exec(
                select(Candidate).where(Candidate.ticker == candidate.ticker)
            ).first()

            if not base_candidate:
                base_candidate = Candidate(
                    ticker=candidate.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    strategy_name=self.STRATEGY_NAME,
                )
                session.add(base_candidate)
            else:
                base_candidate.scan_date = candidate.scan_date
                base_candidate.status = candidate.status

            orh_candidate = session.exec(
                select(ORHCandidate).where(
                    ORHCandidate.ticker == candidate.ticker
                )
            ).first()

            if orh_candidate:
                orh_candidate.gap_percent = candidate.gap_percent
                orh_candidate.conid = candidate.conid
            else:
                orh_candidate = ORHCandidate(
                    ticker=candidate.ticker,
                    gap_percent=candidate.gap_percent,
                    conid=candidate.conid,
                )
                session.add(orh_candidate)

            session.commit()
            logger.debug(f"Saved gap candidate: {candidate.ticker}")

    def save_news_candidate(self, candidate: NewsStockInPlay) -> None:
        """Save or update a news candidate

        Args:
            candidate: NewsStockInPlay object to save
        """
        with self.db.get_session() as session:
            base_candidate = session.exec(
                select(Candidate).where(Candidate.ticker == candidate.ticker)
            ).first()

            if not base_candidate:
                base_candidate = Candidate(
                    ticker=candidate.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    strategy_name=self.STRATEGY_NAME,
                )
                session.add(base_candidate)
            else:
                base_candidate.scan_date = candidate.scan_date
                base_candidate.status = candidate.status

            orh_candidate = session.exec(
                select(ORHCandidate).where(
                    ORHCandidate.ticker == candidate.ticker
                )
            ).first()

            if orh_candidate:
                orh_candidate.headline = candidate.headline
                orh_candidate.announcement_type = candidate.announcement_type
                orh_candidate.announcement_timestamp = (
                    candidate.announcement_timestamp
                )
            else:
                orh_candidate = ORHCandidate(
                    ticker=candidate.ticker,
                    headline=candidate.headline,
                    announcement_type=candidate.announcement_type,
                    announcement_timestamp=candidate.announcement_timestamp,
                )
                session.add(orh_candidate)

            session.commit()
            logger.debug(f"Saved news candidate: {candidate.ticker}")

    def get_gap_candidates(self) -> list[GapStockInPlay]:
        """Get all gap candidates with status='watching'

        Returns:
            List of GapStockInPlay objects
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidate, Candidate)
                .join(Candidate)
                .where(col(ORHCandidate.gap_percent).is_not(None))
                .where(Candidate.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                GapStockInPlay(
                    ticker=orh.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    gap_percent=orh.gap_percent or 0.0,
                    conid=orh.conid,
                )
                for orh, candidate in results
            ]

    def get_news_candidates(self) -> list[NewsStockInPlay]:
        """Get all news candidates with status='watching'

        Returns:
            List of NewsStockInPlay objects
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidate, Candidate)
                .join(Candidate)
                .where(col(ORHCandidate.headline).is_not(None))
                .where(Candidate.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                NewsStockInPlay(
                    ticker=orh.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    headline=orh.headline or "",
                    announcement_type=orh.announcement_type,
                    announcement_timestamp=orh.announcement_timestamp,
                )
                for orh, candidate in results
            ]

    def get_tradeable_candidates(self) -> list[TradeableCandidate]:
        """Get candidates with gap, news, and opening ranges

        Returns:
            List of TradeableCandidate objects ready for trading
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidate, Candidate)
                .join(Candidate)
                .where(col(ORHCandidate.gap_percent).is_not(None))
                .where(col(ORHCandidate.headline).is_not(None))
                .where(col(ORHCandidate.or_high).is_not(None))
                .where(Candidate.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                TradeableCandidate(
                    ticker=orh.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    gap_percent=orh.gap_percent or 0.0,
                    conid=orh.conid,
                    headline=orh.headline or "",
                    or_high=float(orh.or_high or 0.0),
                    or_low=float(orh.or_low or 0.0),
                )
                for orh, candidate in results
            ]

    def get_candidates_needing_ranges(self) -> list[GapStockInPlay]:
        """Get gap+news candidates without opening ranges

        Returns:
            List of GapStockInPlay objects that need opening range tracking
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidate, Candidate)
                .join(Candidate)
                .where(col(ORHCandidate.gap_percent).is_not(None))
                .where(col(ORHCandidate.headline).is_not(None))
                .where(col(ORHCandidate.or_high).is_(None))
                .where(Candidate.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                GapStockInPlay(
                    ticker=orh.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    gap_percent=orh.gap_percent or 0.0,
                    conid=orh.conid,
                )
                for orh, candidate in results
            ]

    def save_opening_range(
        self, ticker: str, or_high: float, or_low: float
    ) -> None:
        """Save or update opening range for a candidate

        Args:
            ticker: Stock ticker symbol
            or_high: Opening range high price
            or_low: Opening range low price
        """
        with self.db.get_session() as session:
            orh_candidate = session.exec(
                select(ORHCandidate).where(ORHCandidate.ticker == ticker)
            ).first()

            if orh_candidate:
                orh_candidate.or_high = or_high
                orh_candidate.or_low = or_low
                orh_candidate.sample_date = datetime.now().isoformat()
                session.commit()
                logger.debug(
                    f"Saved opening range for {ticker}: ORH=${or_high:.2f}, ORL=${or_low:.2f}"
                )

    def purge(self) -> int:
        """Purge all ORH candidates

        Returns:
            Number of candidates deleted
        """
        with self.db.get_session() as session:
            orh_deleted = session.exec(delete(ORHCandidate))
            candidate_deleted = session.exec(
                delete(Candidate).where(
                    col(Candidate.strategy_name) == self.STRATEGY_NAME
                )
            )
            session.commit()
            total = orh_deleted.rowcount + candidate_deleted.rowcount
            logger.info(f"Purged {total} ORH candidates")
            return total
