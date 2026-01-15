"""Database layer using SQLModel for Skim trading bot.

Inherits from BaseDatabase for common connection logic.
"""

from datetime import date, datetime

from loguru import logger
from sqlmodel import col, delete, select

from skim.domain.models import Position
from skim.infrastructure.database.base import BaseDatabase
from skim.infrastructure.database.trading.mappers import (
    map_table_to_position,
)
from skim.infrastructure.database.trading.models import CandidateTable


class Database(BaseDatabase):
    """SQLite database manager using SQLModel for trading data.

    Inherits connection management from BaseDatabase.
    """

    def update_candidate_status(self, ticker: str, status: str) -> None:
        """Update candidate status

        Args:
            ticker: Stock ticker symbol
            status: New status ('watching' | 'entered' | 'closed')
        """
        with self.get_session() as session:
            candidate = session.exec(
                select(CandidateTable).where(CandidateTable.ticker == ticker)
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
        from skim.infrastructure.database.trading.models import (
            ORHCandidateTable,
        )

        with self.get_session() as session:
            conditions = []
            if strategy_name:
                conditions.append(
                    col(CandidateTable.strategy_name) == strategy_name
                )
            if only_before_utc_date:
                date_str = (
                    only_before_utc_date.isoformat()
                    if isinstance(only_before_utc_date, datetime)
                    else only_before_utc_date.isoformat()
                )
                conditions.append(CandidateTable.scan_date < date_str)

            if conditions:
                stmt = delete(CandidateTable).where(*conditions)
                date_str = (
                    only_before_utc_date.isoformat()
                    if only_before_utc_date
                    else "all"
                )
                logger.info(f"Purged candidates before {date_str}")
            else:
                stmt = delete(CandidateTable)
                logger.info("Purged all candidates")

            result = session.exec(stmt)
            session.commit()

            # Also delete ORH candidates for orh_breakout strategy
            if strategy_name == "orh_breakout" or (
                not strategy_name and not only_before_utc_date
            ):
                if only_before_utc_date:
                    orh_stmt = delete(ORHCandidateTable).where(
                        col(ORHCandidateTable.ticker).in_(
                            select(CandidateTable.ticker).where(*conditions)
                        )
                    )
                else:
                    orh_stmt = delete(ORHCandidateTable)
                orh_result = session.exec(orh_stmt)
                session.commit()
                return result.rowcount + orh_result.rowcount

            return result.rowcount

    def create_position(
        self,
        ticker: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        entry_date: datetime,
    ) -> Position:
        """Create a new position

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            entry_price: Entry price per share
            stop_loss: Stop loss price per share
            entry_date: Entry date

        Returns:
            Position object (domain type)
        """

        from skim.infrastructure.database.trading.models import PositionTable

        with self.get_session() as session:
            position_table = PositionTable(
                ticker=ticker,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss=stop_loss,
                entry_date=entry_date.isoformat(),
                status="open",
            )
            session.add(position_table)
            session.commit()
            session.refresh(position_table)
            return map_table_to_position(position_table)

    def get_position(self, position_id: int) -> Position | None:
        """Get position by ID

        Args:
            position_id: Position ID

        Returns:
            Position object or None if not found
        """
        from skim.infrastructure.database.trading.models import PositionTable

        with self.get_session() as session:
            table = session.exec(
                select(PositionTable).where(PositionTable.id == position_id)
            ).first()
            return map_table_to_position(table) if table else None

    def get_open_positions(self) -> list[Position]:
        """Get all open positions

        Returns:
            List of Position objects with status='open'
        """
        from skim.infrastructure.database.trading.models import PositionTable

        with self.get_session() as session:
            results = session.exec(
                select(PositionTable).where(PositionTable.status == "open")
            ).all()
            return [map_table_to_position(table) for table in results]

    def count_open_positions(self) -> int:
        """Count open positions

        Returns:
            Number of positions with status='open'
        """
        from skim.infrastructure.database.trading.models import PositionTable

        with self.get_session() as session:
            open_positions = session.exec(
                select(PositionTable).where(PositionTable.status == "open")
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
        from skim.infrastructure.database.trading.models import PositionTable

        with self.get_session() as session:
            position = session.exec(
                select(PositionTable).where(PositionTable.id == position_id)
            ).first()

            if position:
                position.status = "closed"
                position.exit_price = exit_price
                position.exit_date = exit_date
                session.commit()
