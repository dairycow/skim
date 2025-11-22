"""Pydantic models for market data validation

This module provides validation models for market data requests and responses,
ensuring data quality and type safety for market data operations.
"""

from datetime import datetime, timedelta
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field, field_validator


class MarketDataRequest(BaseModel):
    """Request model for market data snapshot"""

    conid: int = Field(..., gt=0, description="Contract ID")
    fields: (
        list[
            Literal[
                "31",
                "84",
                "86",
                "87",
                "7",
                "70",
                "65",
                "88",
                "68",
                "69",
                "75",
                "60",
            ]
        ]
        | None
    ) = Field(None, description="Specific market data fields to request")
    exchange: str | None = Field(None, description="Exchange for data")
    currency: str | None = Field(
        None, min_length=3, max_length=3, description="Currency"
    )

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v):
        """Validate fields list is not too long"""
        if v and len(v) > 20:
            raise ValueError("Too many fields requested - maximum 20 allowed")
        return v


class MarketDataSnapshot(BaseModel):
    """Market data snapshot response from IBKR"""

    conid: int = Field(..., gt=0, description="Contract ID")
    last_price: float | None = Field(
        None, ge=0, description="Last price (Field 31)"
    )
    bid: float | None = Field(None, ge=0, description="Bid price (Field 84)")
    ask: float | None = Field(None, ge=0, description="Ask price (Field 86)")
    volume: int | None = Field(None, ge=0, description="Volume (Field 87)")
    low: float | None = Field(None, ge=0, description="Low price (Field 7)")
    change_percent: float | None = Field(
        None, description="Change percent (Field 70)"
    )
    previous_close: float | None = Field(
        None, ge=0, description="Previous close (Field 65)"
    )
    today_open: float | None = Field(
        None, ge=0, description="Today's open (Field 88)"
    )
    high: float | None = Field(None, ge=0, description="High price (Field 68)")
    close: float | None = Field(
        None, ge=0, description="Close price (Field 69)"
    )
    trade_date: datetime | None = Field(
        None, description="Trade date (Field 75)"
    )
    trading_class: str | None = Field(
        None, description="Trading class (Field 60)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Data timestamp"
    )

    @field_validator("ask")
    @classmethod
    def validate_bid_ask_spread(cls, v, info):
        """Validate bid-ask relationship"""
        bid = info.data.get("bid")
        if bid and v and bid > v:
            raise ValueError("Bid price cannot be higher than ask price")
        return v

    @field_validator("high", "low")
    @classmethod
    def validate_high_low(cls, v, info):
        """Validate high-low relationship"""
        if (
            info.data.get("high")
            and info.data.get("low")
            and info.data["high"] < info.data["low"]
        ):
            raise ValueError("High price cannot be lower than low price")
        return v

    @property
    def mid_price(self) -> float | None:
        """Calculate mid price from bid/ask"""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return None

    @property
    def spread(self) -> float | None:
        """Calculate bid-ask spread"""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None

    @property
    def spread_percent(self) -> float | None:
        """Calculate bid-ask spread as percentage of mid price"""
        mid = self.mid_price
        spread = self.spread
        if mid is not None and spread is not None and mid > 0:
            return (spread / mid) * 100
        return None


class RealTimeBar(BaseModel):
    """Real-time bar data"""

    conid: int = Field(..., gt=0, description="Contract ID")
    timestamp: datetime = Field(..., description="Bar timestamp")
    open: float = Field(..., gt=0, description="Open price")
    high: float = Field(..., gt=0, description="High price")
    low: float = Field(..., gt=0, description="Low price")
    close: float = Field(..., gt=0, description="Close price")
    volume: int = Field(..., ge=0, description="Volume")
    bar_size: Literal[
        "1 secs",
        "5 secs",
        "10 secs",
        "30 secs",
        "1 min",
        "5 mins",
        "15 mins",
        "30 mins",
        "1 hour",
        "1 day",
    ] = Field(..., description="Bar size")

    @field_validator("low")
    @classmethod
    def validate_high_low(cls, v, info):
        """Validate high-low relationship"""
        high = info.data.get("high")
        if high and v and high < v:
            raise ValueError("High price cannot be lower than low price")
        return v

    @field_validator("close")
    @classmethod
    def validate_close_range(cls, v, info):
        """Validate close is within high-low range"""
        high = info.data.get("high")
        low = info.data.get("low")
        if high and low and not (low <= v <= high):
            raise ValueError("Close price must be between high and low")
        return v


class HistoricalDataRequest(BaseModel):
    """Request model for historical market data"""

    conid: int = Field(..., gt=0, description="Contract ID")
    period: Literal[
        "1d", "1w", "1m", "3m", "6m", "1y", "2y", "3y", "5y", "10y"
    ] = Field(..., description="Time period")
    bar_size: Literal[
        "1 min", "5 mins", "15 mins", "30 mins", "1 hour", "1 day"
    ] = Field(..., description="Bar size")
    outside_rth: bool = Field(
        False, description="Include data outside regular trading hours"
    )
    currency: str | None = Field(
        None, min_length=3, max_length=3, description="Currency"
    )


class IBKRMarketDataResponse(BaseModel):
    """IBKR market data snapshot response with enhanced validation"""

    conid: int = Field(..., gt=0, description="Contract ID")
    last_price: float | None = Field(
        None, ge=0.0001, description="Last price (Field 31)"
    )
    bid: float | None = Field(
        None, ge=0.0001, description="Bid price (Field 84)"
    )
    ask: float | None = Field(
        None, ge=0.0001, description="Ask price (Field 86)"
    )
    volume: int | None = Field(None, ge=0, description="Volume (Field 87)")
    low: float | None = Field(
        None, ge=0.0001, description="Low price (Field 7)"
    )
    change_percent: float | None = Field(
        None, description="Change percent (Field 70)"
    )
    previous_close: float | None = Field(
        None, ge=0.0001, description="Previous close (Field 65)"
    )
    today_open: float | None = Field(
        None, ge=0.0001, description="Today's open (Field 88)"
    )
    high: float | None = Field(
        None, ge=0.0001, description="High price (Field 68)"
    )
    close: float | None = Field(
        None, ge=0.0001, description="Close price (Field 69)"
    )
    trade_date: datetime | None = Field(
        None, description="Trade date (Field 75)"
    )
    trading_class: str | None = Field(
        None, description="Trading class (Field 60)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Data timestamp"
    )

    @field_validator("ask")
    @classmethod
    def validate_bid_ask_spread(cls, v, info):
        """Validate bid-ask relationship"""
        bid = info.data.get("bid")
        if bid and v and bid > v:
            raise ValueError("Bid price cannot be higher than ask price")
        return v

    @field_validator("high", "low")
    @classmethod
    def validate_high_low(cls, v, info):
        """Validate high-low relationship"""
        if (
            info.data.get("high")
            and info.data.get("low")
            and info.data["high"] < info.data["low"]
        ):
            raise ValueError("High price cannot be lower than low price")
        return v

    @property
    def mid_price(self) -> float | None:
        """Calculate mid price from bid/ask"""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return None

    @property
    def spread(self) -> float | None:
        """Calculate bid-ask spread"""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None

    @property
    def spread_percent(self) -> float | None:
        """Calculate bid-ask spread as percentage of mid price"""
        mid = self.mid_price
        spread = self.spread
        if mid is not None and spread is not None and mid > 0:
            return (spread / mid) * 100
        return None

    @classmethod
    def from_ibkr_snapshot(
        cls, snapshot_data: dict, conid: int
    ) -> "IBKRMarketDataResponse":
        """Create IBKRMarketDataResponse from raw IBKR snapshot data

        Args:
            snapshot_data: Raw snapshot data from IBKR API
            conid: Contract ID

        Returns:
            IBKRMarketDataResponse instance
        """
        try:
            from .price_parsing import clean_ibkr_price, safe_parse_price
        except ImportError:
            # Fallback implementations
            def clean_ibkr_price(value):
                if isinstance(value, str) and value and value[0].isalpha():
                    return float(value[1:])
                return float(value) if value else 0.0

            def safe_parse_price(value, default=0.0):
                try:
                    return clean_ibkr_price(value)
                except (ValueError, TypeError):
                    return default

        # Extract and clean price fields
        cleaned_data = {
            "conid": conid,
            "last_price": clean_ibkr_price(snapshot_data.get("31"))
            if snapshot_data.get("31")
            else 0.0,
            "bid": safe_parse_price(snapshot_data.get("84"), 0.0),
            "ask": safe_parse_price(snapshot_data.get("86"), 0.0),
            "volume": int(safe_parse_price(snapshot_data.get("87"), 0))
            if snapshot_data.get("87")
            else 0,
            "low": safe_parse_price(snapshot_data.get("7"), 0.0),
            "change_percent": safe_parse_price(snapshot_data.get("70"), 0.0),
            "previous_close": safe_parse_price(snapshot_data.get("65"), 0.0),
            "today_open": safe_parse_price(snapshot_data.get("88"), 0.0),
            "high": safe_parse_price(snapshot_data.get("68"), 0.0),
            "close": safe_parse_price(snapshot_data.get("69"), 0.0),
            "trading_class": snapshot_data.get("60"),
        }

        return cls(**cleaned_data)


class MarketDataValidationError(Exception):
    """Raised when market data validation fails"""

    pass


class MarketDataUnavailableError(Exception):
    """Raised when requested market data is unavailable"""

    pass


# =============================================================================
# Enhanced Market Data Validation Functions
# =============================================================================


def validate_candidate_market_data_completeness(candidate) -> bool:
    """Validate that the minimal OR data on a candidate is sensible."""
    try:
        if candidate.or_high is None or candidate.or_low is None:
            return False
        if candidate.or_high <= 0 or candidate.or_low <= 0:
            return False
        return not candidate.or_high <= candidate.or_low
    except AttributeError:
        return False


def validate_candidate_market_data_freshness(
    candidate, max_age_minutes: int = 30
) -> bool:
    """Validate candidate recency using scan_date when available."""
    scan_date = getattr(candidate, "scan_date", None)
    if not scan_date:
        return False

    try:
        data_time = datetime.fromisoformat(scan_date)
    except ValueError:
        logger.debug(
            f"Candidate {getattr(candidate, 'ticker', '?')}: invalid scan_date {scan_date}"
        )
        return False

    age = datetime.now() - data_time
    return age <= timedelta(minutes=max_age_minutes)


def validate_candidate_for_or_tracking(candidate) -> bool:
    """Validate candidate suitability for opening range tracking."""
    return validate_candidate_market_data_completeness(
        candidate
    ) and validate_candidate_market_data_freshness(candidate)


def filter_candidates_by_market_data_quality(
    candidates: list, max_age_minutes: int = 30
) -> tuple[list, list]:
    """Filter candidates by market data quality

    Args:
        candidates: List of candidates to filter
        max_age_minutes: Maximum age of market data in minutes

    Returns:
        Tuple of (valid_candidates, invalid_candidates)
    """
    valid_candidates = []
    invalid_candidates = []

    for candidate in candidates:
        if validate_candidate_for_or_tracking(candidate):
            valid_candidates.append(candidate)
        else:
            invalid_candidates.append(candidate)

    return valid_candidates, invalid_candidates


def get_candidate_market_data_age_minutes(candidate) -> float | None:
    """Get the age of market data in minutes

    Args:
        candidate: Candidate object

    Returns:
        Age in minutes, or None if timestamp is invalid/missing
    """
    scan_date = getattr(candidate, "scan_date", None)
    if not scan_date:
        return None

    try:
        data_time = datetime.fromisoformat(scan_date)
    except ValueError:
        return None

    age = datetime.now() - data_time
    return age.total_seconds() / 60
