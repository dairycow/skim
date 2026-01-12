"""Database layer using SQLModel for Skim trading bot"""

from datetime import date
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import Session, SQLModel, col, create_engine, delete, select

from .models import Position

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

    def update_candidate_status(self, ticker: str, status: str) -> None:
        """Update candidate status

        Args:
            ticker: Stock ticker symbol
            status: New status ('watching' | 'entered' | 'closed')
        """
        from .models import Candidate

        with self.get_session() as session:
            candidate = session.exec(
                select(Candidate).where(Candidate.ticker == ticker)
            ).first()

            if candidate:
                candidate.status = status
                session.commit()

    def purge_candidates(
        self,
        only_before_utc_date: date | None = None,
        strategy_name: str | None = None,
    ) -> int:
        """Delete candidates, optionally filtering by date and strategy

        Args:
            only_before_utc_date: If provided, delete rows where DATE(scan_date)
                is before this date; otherwise delete all candidates.
            strategy_name: If provided, only delete candidates for this strategy

        Returns:
            Number of rows deleted.
        """
        from .models import Candidate

        with self.get_session() as session:
            conditions = []
            if strategy_name:
                conditions.append(col(Candidate.strategy_name) == strategy_name)
            if only_before_utc_date:
                conditions.append(
                    Candidate.scan_date < only_before_utc_date.isoformat()
                )

            if conditions:
                stmt = delete(Candidate).where(*conditions)
                logger.info(
                    f"Purged candidates before {only_before_utc_date.isoformat() if only_before_utc_date else 'all'}"
                )
            else:
                stmt = delete(Candidate)
                logger.info("Purged all candidates")

            result = session.exec(stmt)
            session.commit()
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
            results = session.exec(
                select(Position).where(Position.status == "open")
            ).all()
            return list(results)

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
