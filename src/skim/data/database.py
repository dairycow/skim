"""Database layer for Skim trading bot"""

import sqlite3
from datetime import datetime

from loguru import logger

from .models import Candidate, Position, Trade


class Database:
    """SQLite database manager for trading bot"""

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
                headline TEXT NOT NULL,
                scan_date TEXT NOT NULL,
                status TEXT NOT NULL,
                gap_percent REAL,
                prev_close REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                or_high REAL,
                or_low REAL,
                or_timestamp TEXT,
                conid INTEGER,
                source TEXT DEFAULT 'ibkr',
                open_price REAL,
                session_high REAL,
                session_low REAL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                market_data_timestamp TEXT
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
                status TEXT NOT NULL,
                half_sold INTEGER DEFAULT 0,
                exit_date TEXT,
                exit_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                position_id INTEGER,
                pnl REAL,
                notes TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id)
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
            (ticker, headline, scan_date, status, gap_percent, prev_close,
             or_high, or_low, or_timestamp, conid, source,
             open_price, session_high, session_low, volume, bid, ask, market_data_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                candidate.ticker,
                candidate.headline,
                candidate.scan_date,
                candidate.status,
                candidate.gap_percent,
                candidate.prev_close,
                candidate.or_high,
                candidate.or_low,
                candidate.or_timestamp,
                candidate.conid,
                candidate.source,
                candidate.open_price,
                candidate.session_high,
                candidate.session_low,
                candidate.volume,
                candidate.bid,
                candidate.ask,
                candidate.market_data_timestamp,
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
        cursor.execute(
            "SELECT * FROM candidates WHERE status = ?", ("watching",)
        )
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def get_triggered_candidates(self) -> list[Candidate]:
        """Get all candidates with status='triggered'

        Returns:
            List of Candidate objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE status = ?", ("triggered",)
        )
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def update_candidate_status(
        self, ticker: str, status: str, gap_percent: float | None = None
    ) -> None:
        """Update candidate status and optionally gap percent

        Args:
            ticker: Stock ticker symbol
            status: New status
            gap_percent: Optional new gap percent
        """
        cursor = self.db.cursor()
        if gap_percent is not None:
            cursor.execute(
                "UPDATE candidates SET status = ?, gap_percent = ? WHERE ticker = ?",
                (status, gap_percent, ticker),
            )
        else:
            cursor.execute(
                "UPDATE candidates SET status = ? WHERE ticker = ?",
                (status, ticker),
            )
        self.db.commit()

    def count_watching_candidates(self) -> int:
        """Count candidates with status='watching'

        Returns:
            Number of watching candidates
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM candidates WHERE status = ?",
            ("watching",),
        )
        row = cursor.fetchone()
        return row["count"]

    def get_or_tracking_candidates(self) -> list[Candidate]:
        """Get all candidates with status='watching' for opening range tracking.

        Retrieves candidates identified by the scan() method that are ready for
        opening range (OR) tracking and breakout detection.

        Returns:
            List of Candidate objects with status='watching'
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE status = ?", ("watching",)
        )
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def get_orh_breakout_candidates(self) -> list[Candidate]:
        """Get all candidates with status='orh_breakout'

        Returns:
            List of Candidate objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE status = ?", ("orh_breakout",)
        )
        rows = cursor.fetchall()
        return [Candidate.from_db_row(dict(row)) for row in rows]

    def update_candidate_or_data(
        self, ticker: str, or_high: float, or_low: float, or_timestamp: str
    ) -> None:
        """Update candidate OR tracking data

        Args:
            ticker: Stock ticker symbol
            or_high: Opening range high price
            or_low: Opening range low price
            or_timestamp: Opening range timestamp

        Raises:
            ValueError: If or_high <= or_low or timestamp is invalid
        """
        # Validate inputs
        if or_high <= or_low:
            raise ValueError(
                f"or_high ({or_high}) must be greater than or_low ({or_low})"
            )

        if not or_timestamp:
            raise ValueError("or_timestamp cannot be empty")

        cursor = self.db.cursor()
        cursor.execute(
            """
            UPDATE candidates
            SET or_high = ?, or_low = ?, or_timestamp = ?
            WHERE ticker = ?
        """,
            (or_high, or_low, or_timestamp, ticker),
        )
        self.db.commit()

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
            stop_loss: Stop loss price
            entry_date: Entry timestamp

        Returns:
            Position ID
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO positions
            (ticker, quantity, entry_price, stop_loss, entry_date, status, half_sold)
            VALUES (?, ?, ?, ?, ?, 'open', 0)
        """,
            (ticker, quantity, entry_price, stop_loss, entry_date),
        )
        self.db.commit()
        return cursor.lastrowid or 0

    def get_open_positions(self) -> list[Position]:
        """Get all open and half-exited positions

        Returns:
            List of Position objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM positions WHERE status IN ('open', 'half_exited')"
        )
        rows = cursor.fetchall()
        return [Position.from_db_row(dict(row)) for row in rows]

    def count_open_positions(self) -> int:
        """Count open and half-exited positions

        Returns:
            Number of open positions
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM positions WHERE status IN ('open', 'half_exited')"
        )
        row = cursor.fetchone()
        return row["count"]

    def update_position_exit(
        self, position_id: int, status: str, exit_price: float, exit_date: str
    ) -> None:
        """Update position with exit information

        Args:
            position_id: Position ID
            status: New status (closed or half_exited)
            exit_price: Exit price
            exit_date: Exit timestamp
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            UPDATE positions
            SET status = ?, exit_price = ?, exit_date = ?
            WHERE id = ?
        """,
            (status, exit_price, exit_date, position_id),
        )
        self.db.commit()

    def update_position_half_sold(
        self, position_id: int, half_sold: bool
    ) -> None:
        """Update position half_sold flag

        Args:
            position_id: Position ID
            half_sold: Whether half position was sold
        """
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE positions SET half_sold = ? WHERE id = ?",
            (1 if half_sold else 0, position_id),
        )
        self.db.commit()

    # Trade methods

    def create_trade(
        self,
        ticker: str,
        action: str,
        quantity: int,
        price: float,
        position_id: int | None = None,
        pnl: float | None = None,
        notes: str | None = None,
    ) -> int:
        """Create a trade record

        Args:
            ticker: Stock ticker symbol
            action: BUY or SELL
            quantity: Number of shares
            price: Execution price
            position_id: Associated position ID (optional)
            pnl: Profit/loss for this trade (optional)
            notes: Trade notes (optional)

        Returns:
            Trade ID
        """
        cursor = self.db.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO trades
            (ticker, action, quantity, price, timestamp, position_id, pnl, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ticker,
                action,
                quantity,
                price,
                timestamp,
                position_id,
                pnl,
                notes,
            ),
        )
        self.db.commit()
        return cursor.lastrowid or 0

    def get_recent_trades(self, hours: int = 24) -> list[Trade]:
        """Get trades from the last specified hours

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent trades
        """
        cursor = self.db.cursor()
        cursor.execute(
            f"""
            SELECT * FROM trades
            WHERE timestamp >= datetime('now', '-{hours} hours')
            ORDER BY TIMESTAMP DESC
            """
        )
        rows = cursor.fetchall()
        return [Trade(**row) for row in rows]

    def get_total_pnl(self) -> float:
        """Get total profit/loss from all trades

        Returns:
            Total PnL
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT SUM(pnl) as total FROM trades WHERE pnl IS NOT NULL"
        )
        row = cursor.fetchone()
        return row["total"] if row["total"] is not None else 0.0

    def close(self):
        """Close database connection"""
        self.db.close()
        logger.info("Database connection closed")
