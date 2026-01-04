"""Database layer using SQLModel for Skim trading bot"""

from datetime import date
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import (
    Session,
    SQLModel,
    col,
    create_engine,
    delete,
    select,
)

# SQLModel model imports for dataclass conversion
from .models import (
    Candidate,
    GapStockInPlay,
    NewsStockInPlay,
    OpeningRange,
    Position,
    StockInPlay,
    TradeableCandidate,
)

if TYPE_CHECKING:
    from sqlmodel import Session


class Database:
    """SQLite database manager using SQLModel"""

    def __init__(self, db_path: str):
        """Initialise database connection and create schema

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory DB
        """
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self._create_schema()
        logger.info(f"Database initialised: {db_path}")

    def _create_schema(self):
        """Create database tables if they don't exist"""
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session

        Returns:
            Session: SQLModel session
        """
        return Session(self.engine)

    def save_stock_in_play(self, stock_in_play: StockInPlay) -> None:
        """Save or update a stock in play (any subclass)

        Args:
            stock_in_play: StockInPlay object or any subclass to save
        """
        with self.get_session() as session:
            if isinstance(stock_in_play, GapStockInPlay):
                candidate = session.exec(
                    select(Candidate).where(
                        Candidate.ticker == stock_in_play.ticker
                    )
                ).first()

                if candidate:
                    candidate.gap_percent = stock_in_play.gap_percent
                    candidate.conid = stock_in_play.conid
                    candidate.scan_date = stock_in_play.scan_date
                else:
                    candidate = Candidate(
                        ticker=stock_in_play.ticker,
                        scan_date=stock_in_play.scan_date,
                        status=stock_in_play.status,
                        gap_percent=stock_in_play.gap_percent,
                        conid=stock_in_play.conid,
                    )
                    session.add(candidate)
            elif isinstance(stock_in_play, NewsStockInPlay):
                candidate = session.exec(
                    select(Candidate).where(
                        Candidate.ticker == stock_in_play.ticker
                    )
                ).first()

                if candidate:
                    candidate.headline = stock_in_play.headline
                    candidate.announcement_type = (
                        stock_in_play.announcement_type
                    )
                    candidate.announcement_timestamp = (
                        stock_in_play.announcement_timestamp
                    )
                else:
                    candidate = Candidate(
                        ticker=stock_in_play.ticker,
                        scan_date=stock_in_play.scan_date,
                        status=stock_in_play.status,
                        headline=stock_in_play.headline,
                        announcement_type=stock_in_play.announcement_type,
                        announcement_timestamp=stock_in_play.announcement_timestamp,
                    )
                    session.add(candidate)
            else:
                raise ValueError(
                    f"Unknown StockInPlay type: {type(stock_in_play)}"
                )

            session.commit()

    def get_stock_in_play(self, ticker: str) -> StockInPlay | None:
        """Get stock in play by ticker (polymorphic)

        Args:
            ticker: Stock ticker symbol

        Returns:
            StockInPlay object or None if not found
        """
        with self.get_session() as session:
            candidate = session.exec(
                select(Candidate).where(Candidate.ticker == ticker)
            ).first()

            if not candidate:
                return None

            if candidate.gap_percent is not None:
                return GapStockInPlay(
                    ticker=candidate.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    gap_percent=candidate.gap_percent,
                    conid=candidate.conid,
                )
            elif candidate.headline is not None:
                return NewsStockInPlay(
                    ticker=candidate.ticker,
                    scan_date=candidate.scan_date,
                    status=candidate.status,
                    headline=candidate.headline,
                    announcement_type=candidate.announcement_type,
                    announcement_timestamp=candidate.announcement_timestamp,
                )

    def get_gap_candidates(self) -> list[GapStockInPlay]:
        """Get all gap-only candidates with status='watching'

        Returns:
            List of GapStockInPlay objects
        """
        with self.get_session() as session:
            candidates = session.exec(
                select(Candidate)
                .where(col(Candidate.gap_percent).is_not(None))
                .where(Candidate.status == "watching")
            ).all()

            return [
                GapStockInPlay(
                    ticker=c.ticker,
                    scan_date=c.scan_date,
                    status=c.status,
                    gap_percent=c.gap_percent,
                    conid=c.conid,
                )
                for c in candidates
            ]

    def get_news_candidates(self) -> list[NewsStockInPlay]:
        """Get all news-only candidates with status='watching'

        Returns:
            List of NewsStockInPlay objects
        """
        with self.get_session() as session:
            candidates = session.exec(
                select(Candidate)
                .where(col(Candidate.headline).is_not(None))
                .where(Candidate.status == "watching")
            ).all()

            return [
                NewsStockInPlay(
                    ticker=c.ticker,
                    scan_date=c.scan_date,
                    status=c.status,
                    headline=c.headline,
                    announcement_type=c.announcement_type,
                    announcement_timestamp=c.announcement_timestamp,
                )
                for c in candidates
            ]

    def get_tradeable_candidates(self) -> list[TradeableCandidate]:
        """Get candidates with both gap and news AND opening ranges

        Returns tradeable candidates with ORH/ORL for trading.
        """
        with self.get_session() as session:
            candidates = session.exec(
                select(Candidate)
                .join(OpeningRange)
                .where(col(Candidate.gap_percent).is_not(None))
                .where(col(Candidate.headline).is_not(None))
                .where(Candidate.status == "watching")
            ).all()

            return [
                TradeableCandidate(
                    ticker=c.ticker,
                    scan_date=c.scan_date,
                    status=c.status,
                    gap_percent=c.gap_percent,
                    conid=c.conid,
                    headline=c.headline,
                    or_high=c.opening_range.or_high,
                    or_low=c.opening_range.or_low,
                )
                for c in candidates
            ]

    def get_watching_candidates(self) -> list[StockInPlay]:
        """Get all candidates with status='watching' (all types)

        Returns:
            List of StockInPlay objects
        """
        with self.get_session() as session:
            candidates = session.exec(
                select(Candidate).where(Candidate.status == "watching")
            ).all()

            result = [self.get_stock_in_play(c.ticker) for c in candidates]
            return [s for s in result if s is not None]

    def update_candidate_status(self, ticker: str, status: str) -> None:
        """Update candidate status

        Args:
            ticker: Stock ticker symbol
            status: New status ('watching' | 'entered' | 'closed')
        """
        with self.get_session() as session:
            candidate = session.exec(
                select(Candidate).where(Candidate.ticker == ticker)
            ).first()

            if candidate:
                candidate.status = status
                session.commit()

    def purge_candidates(self, only_before_utc_date: date | None = None) -> int:
        """Delete candidates, optionally filtering to rows before a given UTC date.

        Args:
            only_before_utc_date: If provided, delete rows where DATE(scan_date)
                is before this date; otherwise delete all candidates.

        Returns:
            Number of rows deleted.
        """
        with self.get_session() as session:
            if only_before_utc_date:
                stmt = delete(Candidate).where(
                    Candidate.scan_date < only_before_utc_date.isoformat()
                )
                logger.info(
                    f"Purged candidates before {only_before_utc_date.isoformat()}"
                )
            else:
                stmt = delete(Candidate)
                logger.info("Purged all candidates")

            result = session.exec(stmt)
            session.commit()
            return result.rowcount

    def save_opening_range(self, opening_range: OpeningRange) -> None:
        """Save or update opening range for a ticker

        Args:
            opening_range: OpeningRange object to save
        """
        with self.get_session() as session:
            existing = session.exec(
                select(OpeningRange).where(
                    OpeningRange.ticker == opening_range.ticker
                )
            ).first()

            if existing:
                existing.or_high = opening_range.or_high
                existing.or_low = opening_range.or_low
                existing.sample_date = opening_range.sample_date
            else:
                session.add(opening_range)

            session.commit()

    def get_opening_range(self, ticker: str) -> OpeningRange | None:
        """Get opening range for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            OpeningRange object or None if not found
        """
        with self.get_session() as session:
            return session.exec(
                select(OpeningRange).where(OpeningRange.ticker == ticker)
            ).first()

    def get_candidates_needing_ranges(self) -> list[StockInPlay]:
        """Get gap+news candidates that need opening ranges

        Returns:
            List of StockInPlay objects (will be GapStockInPlay)
        """
        with self.get_session() as session:
            candidates = session.exec(
                select(Candidate)
                .outerjoin(OpeningRange)
                .where(col(Candidate.gap_percent).is_not(None))
                .where(col(Candidate.headline).is_not(None))
                .where(Candidate.status == "watching")
                .where(col(OpeningRange.ticker).is_(None))
            ).all()

            result = [self.get_stock_in_play(c.ticker) for c in candidates]
            return [s for s in result if s is not None]

    def purge_opening_ranges(self) -> int:
        """Delete all opening ranges

        Returns:
            Number of rows deleted.
        """
        with self.get_session() as session:
            result = session.exec(delete(OpeningRange))
            session.commit()
            logger.info("Purged all opening ranges")
            return result.rowcount

    def create_position(
        self,
        ticker: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        entry_date: str,
    ) -> int:
        """Create a new position

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            entry_price: Entry price per share
            stop_loss: Stop loss price per share
            entry_date: ISO format datetime string

        Returns:
            Position ID
        """
        with self.get_session() as session:
            position = Position(
                ticker=ticker,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss=stop_loss,
                entry_date=entry_date,
                status="open",
            )
            session.add(position)
            session.commit()
            session.refresh(position)
            return position.id if position.id is not None else 0

    def get_position(self, position_id: int) -> Position | None:
        """Get position by ID

        Args:
            position_id: Position ID

        Returns:
            Position object or None if not found
        """
        with self.get_session() as session:
            return session.exec(
                select(Position).where(Position.id == position_id)
            ).first()

    def get_open_positions(self) -> list[Position]:
        """Get all open positions

        Returns:
            List of Position objects with status='open'
        """
        with self.get_session() as session:
            return session.exec(
                select(Position).where(Position.status == "open")
            ).all()

    def count_open_positions(self) -> int:
        """Count open positions

        Returns:
            Number of positions with status='open'
        """
        with self.get_session() as session:
            open_positions = session.exec(
                select(Position).where(Position.status == "open")
            ).all()
            return len(open_positions)

    def close_position(
        self, position_id: int, exit_price: float, exit_date: str
    ) -> None:
        """Close a position

        Args:
            position_id: Position ID
            exit_price: Exit price per share
            exit_date: ISO format datetime string
        """
        with self.get_session() as session:
            position = session.exec(
                select(Position).where(Position.id == position_id)
            ).first()

            if position:
                position.status = "closed"
                position.exit_price = exit_price
                position.exit_date = exit_date
                session.commit()

    def close(self) -> None:
        """Dispose of database engine"""
        if self.engine:
            self.engine.dispose()

    def save_candidate(self, stock_in_play: StockInPlay) -> None:
        """Backward compatibility alias for save_stock_in_play"""
        self.save_stock_in_play(stock_in_play)
