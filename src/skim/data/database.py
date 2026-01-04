"""Simplified database layer for Skim trading bot"""

import sqlite3
from datetime import date

from loguru import logger

from .models import (
    GapStockInPlay,
    NewsStockInPlay,
    OpeningRange,
    Position,
    StockInPlay,
    TradeableCandidate,
)


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

        # Candidates table (simplified, no ORH/ORL, no candidate_type)
        cursor.execute("""
			CREATE TABLE IF NOT EXISTS candidates (
				ticker TEXT PRIMARY KEY,
				scan_date TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'watching',
				gap_percent REAL,
				conid INTEGER,
				headline TEXT,
				announcement_type TEXT DEFAULT 'pricesens',
				announcement_timestamp TEXT,
				created_at TEXT DEFAULT CURRENT_TIMESTAMP
			)
		""")

        # Opening ranges table (new, separate from candidates)
        cursor.execute("""
			CREATE TABLE IF NOT EXISTS opening_ranges (
				ticker TEXT PRIMARY KEY,
				or_high REAL NOT NULL,
				or_low REAL NOT NULL,
				sample_date TEXT NOT NULL,
				created_at TEXT DEFAULT CURRENT_TIMESTAMP,
				FOREIGN KEY (ticker) REFERENCES candidates(ticker) ON DELETE CASCADE
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

    def save_stock_in_play(self, stock_in_play: StockInPlay) -> None:
        """Save or update a stock in play (any subclass)

        Args:
            stock_in_play: StockInPlay object or any subclass to save
        """
        cursor = self.db.cursor()

        if isinstance(stock_in_play, GapStockInPlay):
            cursor.execute(
                """
            INSERT OR REPLACE INTO candidates
            (ticker, scan_date, status, gap_percent, conid, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
                (
                    stock_in_play.ticker,
                    stock_in_play.scan_date,
                    stock_in_play.status,
                    stock_in_play.gap_percent,
                    stock_in_play.conid,
                    stock_in_play.scan_date,  # Use scan_date as created_at
                ),
            )
        elif isinstance(stock_in_play, NewsStockInPlay):
            # Check if candidate already exists (has gap data)
            existing = cursor.execute(
                "SELECT ticker FROM candidates WHERE ticker = ?",
                (stock_in_play.ticker,),
            ).fetchone()

            if existing:
                # Update existing candidate with news fields (preserve gap data)
                cursor.execute(
                    """
                    UPDATE candidates
                    SET headline = ?, announcement_type = ?, announcement_timestamp = ?
                    WHERE ticker = ?
                """,
                    (
                        stock_in_play.headline,
                        stock_in_play.announcement_type,
                        stock_in_play.announcement_timestamp,
                        stock_in_play.ticker,
                    ),
                )
            else:
                # Insert new news candidate
                cursor.execute(
                    """
                    INSERT INTO candidates
                    (ticker, scan_date, status, headline, announcement_type, announcement_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        stock_in_play.ticker,
                        stock_in_play.scan_date,
                        stock_in_play.status,
                        stock_in_play.headline,
                        stock_in_play.announcement_type,
                        stock_in_play.announcement_timestamp,
                        stock_in_play.scan_date,  # Use scan_date as created_at
                    ),
                )
        else:
            raise ValueError(f"Unknown StockInPlay type: {type(stock_in_play)}")

        self.db.commit()

    def get_stock_in_play(self, ticker: str) -> StockInPlay | None:
        """Get stock in play by ticker (polymorphic)

        Args:
                ticker: Stock ticker symbol

        Returns:
                StockInPlay object or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM candidates WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()

        if not row:
            return None

        # Infer type from field presence
        if row["gap_percent"] is not None:
            return GapStockInPlay(
                ticker=row["ticker"],
                scan_date=row["scan_date"],
                status=row["status"],
                gap_percent=row["gap_percent"],
                conid=row["conid"],
            )
        elif row["headline"] is not None:
            return NewsStockInPlay(
                ticker=row["ticker"],
                scan_date=row["scan_date"],
                status=row["status"],
                headline=row["headline"],
                announcement_type=row["announcement_type"],
                announcement_timestamp=row["announcement_timestamp"],
            )

    def get_gap_candidates(self) -> list[GapStockInPlay]:
        """Get all gap-only candidates with status='watching'

        Returns:
                List of GapStockInPlay objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE gap_percent IS NOT NULL AND status = 'watching'"
        )
        rows = cursor.fetchall()
        return [
            GapStockInPlay(
                ticker=row["ticker"],
                scan_date=row["scan_date"],
                status=row["status"],
                gap_percent=row["gap_percent"],
                conid=row["conid"] if "conid" in row else None,
            )
            for row in rows
        ]

    def get_news_candidates(self) -> list[NewsStockInPlay]:
        """Get all news-only candidates with status='watching'

        Returns:
                List of NewsStockInPlay objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM candidates WHERE headline IS NOT NULL AND status = 'watching'"
        )
        rows = cursor.fetchall()
        return [
            NewsStockInPlay(
                ticker=row["ticker"],
                scan_date=row["scan_date"],
                status=row["status"],
                headline=row["headline"],
                announcement_type=row["announcement_type"]
                if "announcement_type" in row
                else "pricesens",
                announcement_timestamp=row["announcement_timestamp"]
                if "announcement_timestamp" in row
                else None,
            )
            for row in rows
        ]

    def get_tradeable_candidates(self) -> list[TradeableCandidate]:
        """Get candidates with both gap and news AND opening ranges

        Returns tradeable candidates with ORH/ORL for trading.
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT c.*, o.or_high, o.or_low
            FROM candidates c
            JOIN opening_ranges o ON c.ticker = o.ticker
            WHERE c.gap_percent IS NOT NULL
              AND c.headline IS NOT NULL
              AND c.status = 'watching'
        """)
        rows = cursor.fetchall()
        return [
            TradeableCandidate(
                ticker=row["ticker"],
                scan_date=row["scan_date"],
                status=row["status"],
                gap_percent=row["gap_percent"],
                conid=row["conid"] if "conid" in row else None,
                headline=row["headline"],
                or_high=row["or_high"],
                or_low=row["or_low"],
            )
            for row in rows
        ]

    def get_watching_candidates(self) -> list[StockInPlay]:
        """Get all candidates with status='watching' (all types)

        Returns:
                List of StockInPlay objects
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM candidates WHERE status = 'watching'")
        rows = cursor.fetchall()
        result = [self.get_stock_in_play(row["ticker"]) for row in rows]
        return [s for s in result if s is not None]

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

    # Opening range methods

    def save_opening_range(self, opening_range: OpeningRange) -> None:
        """Save or update opening range for a ticker

        Args:
            opening_range: OpeningRange object to save
        """
        cursor = self.db.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO opening_ranges
            (ticker, or_high, or_low, sample_date)
            VALUES (?, ?, ?, ?)""",
            (
                opening_range.ticker,
                opening_range.or_high,
                opening_range.or_low,
                opening_range.sample_date,
            ),
        )
        self.db.commit()

    def get_opening_range(self, ticker: str) -> OpeningRange | None:
        """Get opening range for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            OpeningRange object or None if not found
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM opening_ranges WHERE ticker = ?", (ticker,)
        )
        row = cursor.fetchone()

        if row:
            return OpeningRange.from_db_row(dict(row))
        return None

    def get_candidates_needing_ranges(self) -> list[StockInPlay]:
        """Get gap+news candidates that need opening ranges

        Returns:
                List of StockInPlay objects (will be GapStockInPlay)
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT c.*
            FROM candidates c
            LEFT JOIN opening_ranges o ON c.ticker = o.ticker
            WHERE c.gap_percent IS NOT NULL
              AND c.headline IS NOT NULL
              AND c.status = 'watching'
              AND o.ticker IS NULL
        """)
        rows = cursor.fetchall()
        result = [self.get_stock_in_play(row["ticker"]) for row in rows]
        return [s for s in result if s is not None]

    def purge_opening_ranges(self) -> int:
        """Delete all opening ranges

        Returns:
            Number of rows deleted.
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM opening_ranges")
        logger.info("Purged all opening ranges")
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

    # Backward compatibility
    def save_candidate(self, stock_in_play: StockInPlay) -> None:
        """Backward compatibility alias for save_stock_in_play"""
        self.save_stock_in_play(stock_in_play)
