"""ORH-specific candidate repository implementation"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import col, delete, select

from skim.domain.models import Candidate, GapCandidate, NewsCandidate, Ticker
from skim.infrastructure.database.trading.mappers import (
    map_candidate_to_table,
    map_orh_data_to_table,
    map_table_to_candidate,
)
from skim.infrastructure.database.trading.models import (
    CandidateTable,
    ORHCandidateTable,
)

if TYPE_CHECKING:
    from skim.trading.data.database import Database


class ORHCandidateRepository:
    """Repository for ORH breakout strategy candidates"""

    STRATEGY_NAME = "orh_breakout"

    def __init__(self, db: Database):
        """Initialise ORH repository

        Args:
            db: Database instance for database operations
        """
        self.db = db

    def save_candidate(self, candidate: GapCandidate | NewsCandidate) -> None:
        """Save or update a candidate (generic method for protocol compliance)

        Args:
            candidate: Candidate object to save
        """
        if isinstance(candidate, GapCandidate):
            self.save_gap_candidate(candidate)
        elif isinstance(candidate, NewsCandidate):
            self.save_news_candidate(candidate)
        else:
            raise ValueError(f"Unknown candidate type: {type(candidate)}")

    def save_gap_candidate(self, candidate: GapCandidate) -> None:
        """Save or update a gap candidate

        Args:
            candidate: GapCandidate object to save
        """
        with self.db.get_session() as session:
            base_candidate = session.exec(
                select(CandidateTable).where(
                    CandidateTable.ticker == candidate.ticker.symbol
                )
            ).first()

            if not base_candidate:
                base_candidate = map_candidate_to_table(candidate)
                session.add(base_candidate)
            else:
                base_candidate.scan_date = candidate.scan_date.isoformat()
                base_candidate.status = candidate.status

            existing_orh = session.exec(
                select(ORHCandidateTable).where(
                    ORHCandidateTable.ticker == candidate.ticker.symbol
                )
            ).first()

            if existing_orh:
                existing_orh.gap_percent = candidate.orh_data.gap_percent
                existing_orh.conid = candidate.orh_data.conid
            else:
                existing_orh = map_orh_data_to_table(
                    candidate.ticker.symbol, candidate.orh_data
                )
                session.add(existing_orh)

            session.commit()
            logger.debug(f"Saved gap candidate: {candidate.ticker.symbol}")

    def save_news_candidate(self, candidate: NewsCandidate) -> None:
        """Save or update a news candidate

        Args:
            candidate: NewsCandidate object to save
        """
        with self.db.get_session() as session:
            base_candidate = session.exec(
                select(CandidateTable).where(
                    CandidateTable.ticker == candidate.ticker.symbol
                )
            ).first()

            if not base_candidate:
                base_candidate = map_candidate_to_table(candidate)
                session.add(base_candidate)
            else:
                base_candidate.scan_date = candidate.scan_date.isoformat()
                base_candidate.status = candidate.status

            orh_candidate = session.exec(
                select(ORHCandidateTable).where(
                    ORHCandidateTable.ticker == candidate.ticker.symbol
                )
            ).first()

            if orh_candidate:
                orh_candidate.headline = candidate.orh_data.headline
                orh_candidate.announcement_type = (
                    candidate.orh_data.announcement_type
                )
                orh_candidate.announcement_timestamp = (
                    candidate.orh_data.announcement_timestamp.isoformat()
                    if candidate.orh_data.announcement_timestamp
                    else None
                )
            else:
                orh_candidate = map_orh_data_to_table(
                    candidate.ticker.symbol, candidate.orh_data
                )
                session.add(orh_candidate)

            session.commit()
            logger.debug(f"Saved news candidate: {candidate.ticker.symbol}")

    def get_gap_candidates(self) -> list[GapCandidate]:
        """Get all gap candidates with status='watching'

        Returns:
            List of GapCandidate objects
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidateTable, CandidateTable)
                .join(CandidateTable)
                .where(col(ORHCandidateTable.gap_percent).is_not(None))
                .where(CandidateTable.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                GapCandidate(
                    ticker=Ticker(candidate.ticker),
                    scan_date=datetime.fromisoformat(candidate.scan_date),
                    status=candidate.status,
                    strategy_name=candidate.strategy_name,
                    gap_percent=orh.gap_percent or 0.0,
                    conid=orh.conid,
                    created_at=datetime.fromisoformat(candidate.created_at),
                )
                for orh, candidate in results
            ]

    def get_news_candidates(self) -> list[NewsCandidate]:
        """Get all news candidates with status='watching'

        Returns:
            List of NewsCandidate objects
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidateTable, CandidateTable)
                .join(CandidateTable)
                .where(col(ORHCandidateTable.headline).is_not(None))
                .where(CandidateTable.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                NewsCandidate(
                    ticker=Ticker(candidate.ticker),
                    scan_date=datetime.fromisoformat(candidate.scan_date),
                    status=candidate.status,
                    strategy_name=candidate.strategy_name,
                    headline=orh.headline or "",
                    announcement_type=orh.announcement_type,
                    announcement_timestamp=(
                        datetime.fromisoformat(orh.announcement_timestamp)
                        if orh.announcement_timestamp
                        else None
                    ),
                    created_at=datetime.fromisoformat(candidate.created_at),
                )
                for orh, candidate in results
            ]

    def get_tradeable_candidates(self) -> list[Candidate]:
        """Get candidates with gap, news, and opening ranges

        Returns:
            List of Candidate objects ready for trading
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidateTable, CandidateTable)
                .join(CandidateTable)
                .where(col(ORHCandidateTable.gap_percent).is_not(None))
                .where(col(ORHCandidateTable.headline).is_not(None))
                .where(col(ORHCandidateTable.or_high).is_not(None))
                .where(CandidateTable.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                map_table_to_candidate(candidate, orh)
                for orh, candidate in results
            ]

    def get_alertable_candidates(self) -> list[Candidate]:
        """Get candidates with gap and news (no range requirement)

        Returns:
            List of Candidate objects ready for alerting
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidateTable, CandidateTable)
                .join(CandidateTable)
                .where(col(ORHCandidateTable.gap_percent).is_not(None))
                .where(col(ORHCandidateTable.headline).is_not(None))
                .where(CandidateTable.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                map_table_to_candidate(candidate, orh)
                for orh, candidate in results
            ]

    def get_candidates_needing_ranges(self) -> list[GapCandidate]:
        """Get gap+news candidates without opening ranges

        Returns:
            List of GapCandidate objects that need opening range tracking
        """
        with self.db.get_session() as session:
            statement = (
                select(ORHCandidateTable, CandidateTable)
                .join(CandidateTable)
                .where(col(ORHCandidateTable.gap_percent).is_not(None))
                .where(col(ORHCandidateTable.headline).is_not(None))
                .where(col(ORHCandidateTable.or_high).is_(None))
                .where(CandidateTable.status == "watching")
            )
            results = session.exec(statement).all()

            return [
                GapCandidate(
                    ticker=Ticker(candidate.ticker),
                    scan_date=datetime.fromisoformat(candidate.scan_date),
                    status=candidate.status,
                    strategy_name=candidate.strategy_name,
                    gap_percent=orh.gap_percent or 0.0,
                    conid=orh.conid,
                    created_at=datetime.fromisoformat(candidate.created_at),
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
                select(ORHCandidateTable).where(
                    ORHCandidateTable.ticker == ticker
                )
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
            orh_deleted = session.exec(delete(ORHCandidateTable))
            candidate_deleted = session.exec(
                delete(CandidateTable).where(
                    col(CandidateTable.strategy_name) == self.STRATEGY_NAME
                )
            )
            session.commit()
            total = orh_deleted.rowcount + candidate_deleted.rowcount
            logger.info(
                f"Purged {orh_deleted.rowcount} ORH candidates, {candidate_deleted.rowcount} base candidates"
            )
            return total
