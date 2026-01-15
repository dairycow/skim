"""Base database class with common connection logic."""

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import Session, SQLModel, create_engine

if TYPE_CHECKING:
    pass


class BaseDatabase:
    """Base database class with common connection logic.

    Provides shared database connection management for trading and historical databases.
    Subclasses should call super().__init__(db_path) and may override _create_schema().
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory DB
        """
        self.db_path = str(db_path)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        self._create_schema()
        logger.info(f"Database initialised: {self.db_path}")

    def _create_schema(self) -> None:
        """Create database tables if they don't exist.

        Override in subclasses to add SQLModel metadata creation.
        """
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLModel Session object

        Note:
            Caller is responsible for committing, rolling back on error,
            and closing the session.
        """
        return Session(self.engine)

    def close(self) -> None:
        """Dispose of the database engine.

        Call this when shutting down to release connections.
        """
        if self.engine:
            self.engine.dispose()
            logger.info(f"Database connection closed: {self.db_path}")

    def __enter__(self) -> "BaseDatabase":
        """Context manager entry - returns self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures connection is closed."""
        self.close()
