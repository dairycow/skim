"""Simplified database layer for Skim trading bot"""

import sqlite3
from datetime import date

from loguru import logger

from .models import Candidate, Position


class Database:
    """SQLite database manager - minimal schema"""

    def __init__(self, db_path: str):
        """Initialise database connection and create schema

        Args:
                db_path: Path to SQLite database file or ":memory:" for in-memory DB
        """
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row  # Enable dict-like row access
        self._create_schema()
        logger.info(f"Database initialised: {db_path}")

    def _create_schema(self):
        """Create database tables if they don't exist"""
        cursor = self.db.cursor()

        # Candidates table
        cursor.execute("""
			CREATE TABLE IF NOT EXISTS candidates (
				ticker TEXT PRIMARY KEY,
				or_high REAL,
				or_low REAL,
				scan_date TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'watching',
				created_at TEXT DEFAULT CURRENT_TIMESTAMP
			)
		""")

        # Positions table
        cursor.execute("""
			CREATE TABLE IF NOT EXISTS positions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				ticker TEXT NOT NULL,
				quantity INTEGER NOT NULL,
				entry_price REAL NOT NULL,
				stop_loss REAL NOT NULL,
				entry_date TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'open',
				exit_price REAL,
				exit_date TEXT,
				created_at TEXT DEFAULT CURRENT_TIMESTAMP
			)
		""")

        self.db.commit()

    # Candidate methods

    def save_candidate(self, candidate: Candidate) -> None:
        """Save or update a candidate

        Args:
                candidate: Candidate object to save
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
			INSERT OR REPLACE INTO candidates
			(ticker, or_high, or_low, scan_date, status)
			VALUES (?, ?, ?, ?, ?)
		""",
            (
                candidate.ticker,
                candidate.or_high,
                candidate.or_low,
                candidate.scan_date,
                candidate.status,
            ),
        )
        self.db.commit()

    def get_candidate(self, ticker: str) -> Candidate | None:
        """Get candidate by ticker

        Args:
                ticker: Stock ticker symbol

        Returns:
                Candidate object or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM candidates WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()

        if row:
            return Candidate.from_db_row(dict(row))
        return None

    def get_watching_candidates(self) -> list[Candidate]:
        """Get all candidates with status='watching'

        Returns:
                List of Candidate objects
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM candidates WHERE status = 'watching'")
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def update_candidate_status(self, ticker: str, status: str) -> None:
        """Update candidate status

        Args:
                ticker: Stock ticker symbol
                status: New status ('watching' | 'entered' | 'closed')
        """
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE candidates SET status = ? WHERE ticker = ?",
            (status, ticker),
        )
        self.db.commit()

    def update_candidate_ranges(
        self, ticker: str, or_high: float, or_low: float
    ) -> None:
        """Update candidate opening range values

        Args:
                ticker: Stock ticker symbol
                or_high: Opening range high
                or_low: Opening range low
        """
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE candidates SET or_high = ?, or_low = ? WHERE ticker = ?",
            (or_high, or_low, ticker),
        )
        self.db.commit()

    def get_candidates_without_ranges(self) -> list[Candidate]:
        """Get candidates where or_high or or_low is NULL

        Returns:
                List of Candidate objects missing range data
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE or_high IS NULL OR or_low IS NULL"
        )
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def purge_candidates(self, only_before_utc_date: date | None = None) -> int:
        """Delete candidates, optionally filtering to rows before a given UTC date.

        Args:
            only_before_utc_date: If provided, delete rows where DATE(scan_date)
                is before this date; otherwise delete all candidates.

        Returns:
            Number of rows deleted.
        """
        cursor = self.db.cursor()

        if only_before_utc_date:
            cursor.execute(
                "DELETE FROM candidates WHERE DATE(scan_date) < DATE(?)",
                (only_before_utc_date.isoformat(),),
            )
            logger.info(
                f"Purged candidates before {only_before_utc_date.isoformat()}"
            )
        else:
            cursor.execute("DELETE FROM candidates")
            logger.info("Purged all candidates")

        self.db.commit()
        return cursor.rowcount or 0

    # Position methods

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
        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO positions
            (ticker, quantity, entry_price, stop_loss, entry_date, status)
            VALUES (?, ?, ?, ?, ?, 'open')
        """,
            (ticker, quantity, entry_price, stop_loss, entry_date),
        )
        self.db.commit()
        return cursor.lastrowid or 0

    def get_position(self, position_id: int) -> Position | None:
        """Get position by ID

        Args:
                position_id: Position ID

        Returns:
                Position object or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        row = cursor.fetchone()

        if row:
            return Position.from_db_row(dict(row))
        return None

    def get_open_positions(self) -> list[Position]:
        """Get all open positions

        Returns:
                List of Position objects with status='open'
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM positions WHERE status = 'open'")
        rows = cursor.fetchall()
        return [Position.from_db_row(dict(row)) for row in rows]

    def count_open_positions(self) -> int:
        """Count open positions

        Returns:
                Number of positions with status='open'
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM positions WHERE status = 'open'"
        )
        row = cursor.fetchone()
        return row["count"] if row else 0

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        exit_date: str,
    ) -> None:
        """Close a position

        Args:
            position_id: Position ID
            exit_price: Exit price per share
            exit_date: ISO format datetime string
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            UPDATE positions
            SET status = 'closed', exit_price = ?, exit_date = ?
            WHERE id = ?
        """,
            (exit_price, exit_date, position_id),
        )
        self.db.commit()

    def close(self) -> None:
        """Close database connection"""
        if self.db:
            self.db.close()
