"""Pydantic models for scanner request/response validation

This module provides validation models for IBKR scanner operations and ASX
announcement scraping, ensuring data quality and type safety throughout
the scanning pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ScannerFilter(BaseModel):
    """Individual filter for IBKR scanner requests"""

    code: Literal[
        "priceAbove",
        "volumeAbove",
        "marketCapAbove",
        "priceBelow",
        "volumeBelow",
        "marketCapBelow",
    ]
    value: int | float

    @field_validator("value")
    @classmethod
    def validate_filter_value(cls, v, info):
        """Validate filter value based on filter code"""
        if info.data.get("code") in ["priceAbove", "priceBelow"]:
            return float(v)
        elif info.data.get("code") in ["volumeAbove", "volumeBelow"]:
            return int(v)
        elif info.data.get("code") in ["marketCapAbove", "marketCapBelow"]:
            return float(v)
        return v


class ScannerRequest(BaseModel):
    """Request parameters for IBKR market scanner"""

    instrument: Literal[
        "STK", "OPT", "FUT", "FOP", "CASH", "CRYPTO", "BOND", "WAR", "FUND"
    ] = "STK"
    scan_type: Literal[
        "TOP_PERC_GAIN",
        "TOP_PERC_LOSE",
        "MOST_ACTIVE",
        "HIGHEST_VOLUME",
        "TOP_TRADE_RATE",
        "MOST_VOLATILE",
        "HOT_BY_PRICE",
        "HOT_BY_VOLUME",
    ] = "TOP_PERC_GAIN"
    location: Literal[
        "STK.HK.ASX",
        "STK.US.MAJOR",
        "STK.EU.MAIN",
        "STK.ASIA.MAIN",
        "STK.CANADA.MAIN",
    ] = "STK.HK.ASX"
    filters: list[ScannerFilter] = Field(default_factory=list)

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v):
        """Ensure filters list is not too long"""
        if len(v) > 10:
            raise ValueError("Too many filters - maximum 10 allowed")
        return v


class GapStock(BaseModel):
    """Stock with gap data from IBKR scanner"""

    ticker: str = Field(
        ..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$"
    )
    gap_percent: float = Field(
        ..., ge=-100, le=1000, description="Gap percentage from previous close"
    )
    conid: int = Field(..., gt=0, description="IBKR contract ID")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        """Validate ticker symbol format"""
        return v.upper().strip()


class OpeningRangeData(BaseModel):
    """Opening range tracking data for a gap stock"""

    ticker: str = Field(
        ..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$"
    )
    conid: int = Field(..., gt=0)
    or_high: float = Field(..., gt=0, description="Opening range high")
    or_low: float = Field(..., gt=0, description="Opening range low")
    open_price: float = Field(..., gt=0, description="Opening price")
    prev_close: float = Field(..., gt=0, description="Previous day close")
    current_price: float = Field(..., gt=0, description="Current market price")
    gap_holding: bool = Field(description="Whether gap is still holding")

    @field_validator("or_high")
    @classmethod
    def validate_or_high(cls, v, info):
        """Ensure OR high is >= OR low"""
        if "or_low" in info.data and v < info.data["or_low"]:
            raise ValueError("Opening range high must be >= opening range low")
        return v

    @field_validator("or_low")
    @classmethod
    def validate_or_low(cls, v, info):
        """Ensure OR low is <= OR high"""
        if "or_high" in info.data and v > info.data["or_high"]:
            raise ValueError("Opening range low must be <= opening range high")
        return v


class BreakoutSignal(BaseModel):
    """Breakout signal for gap stock holding and ORH breakout"""

    ticker: str = Field(
        ..., min_length=1, max_length=10, pattern=r"^[A-Z0-9]+$"
    )
    conid: int = Field(..., gt=0)
    gap_pct: float = Field(..., ge=-100, le=1000, description="Gap percentage")
    or_high: float = Field(..., gt=0, description="Opening range high")
    or_low: float = Field(..., gt=0, description="Opening range low")
    or_size_pct: float = Field(
        ..., ge=0, le=100, description="Opening range size as percentage"
    )
    current_price: float = Field(
        ..., gt=0, description="Current price at breakout"
    )
    entry_signal: Literal[
        "ORB_HIGH_BREAKOUT",
        "ORB_LOW_BREAKOUT",
        "GAP_HOLD_CONFIRMED",
    ] = "ORB_HIGH_BREAKOUT"
    timestamp: datetime = Field(description="Time breakout was detected")

    @model_validator(mode="after")
    def validate_breakout_price(self):
        """Ensure breakout price makes sense relative to OR levels"""
        if (
            self.entry_signal == "ORB_HIGH_BREAKOUT"
            and self.current_price <= self.or_high
        ):
            raise ValueError(
                "Breakout price must be > OR high for ORH breakout"
            )
        elif (
            self.entry_signal == "ORB_LOW_BREAKOUT"
            and self.current_price >= self.or_low
        ):
            raise ValueError("Breakout price must be < OR low for ORL breakout")
        return self


class ASXAnnouncement(BaseModel):
    """ASX price-sensitive announcement data"""

    ticker: str = Field(..., min_length=3, max_length=6, pattern=r"^[A-Z0-9]+$")
    headline: str = Field(
        ..., min_length=1, max_length=500, description="Announcement headline"
    )
    announcement_type: Literal["pricesens", "other"] = "other"
    timestamp: datetime = Field(description="Announcement timestamp")
    pdf_url: str | None = Field(
        default=None, description="URL to announcement PDF"
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        """Validate ASX ticker format"""
        return v.upper().strip()


class PriceSensitiveFilter(BaseModel):
    """Configuration for filtering ASX price-sensitive announcements"""

    min_ticker_length: int = Field(
        default=3, ge=1, le=6, description="Minimum ticker length"
    )
    max_ticker_length: int = Field(
        default=6, ge=1, le=6, description="Maximum ticker length"
    )
    exclude_tickers: list[str] = Field(
        default_factory=list, description="Tickers to exclude"
    )
    include_only_tickers: list[str] | None = Field(
        default=None, description="Only include these tickers"
    )
    min_headline_length: int = Field(
        default=10, ge=1, description="Minimum headline length"
    )
    max_headline_length: int = Field(
        default=200, ge=1, description="Maximum headline length"
    )

    @field_validator("exclude_tickers", "include_only_tickers")
    @classmethod
    def validate_ticker_lists(cls, v):
        """Validate ticker lists format"""
        if v is None:
            return v
        return [ticker.upper().strip() for ticker in v if ticker.strip()]

    @field_validator("include_only_tickers")
    @classmethod
    def validate_mutually_exclusive(cls, v, info):
        """Ensure include_only and exclude are not both used"""
        if v and info.data.get("exclude_tickers"):
            raise ValueError(
                "Cannot specify both include_only_tickers and exclude_tickers"
            )
        return v


class ScannerValidationError(Exception):
    """Raised when scanner parameters or data fail validation"""

    pass


class GapCalculationError(Exception):
    """Raised when gap calculation fails due to invalid data"""

    pass


@dataclass
class GapScanResult:
    """Result from gap scanning with announcement filtering

    Attributes:
        gap_stocks: List of GapStock objects with gap information
        new_candidates: List of candidate dicts for new gaps (for notifications)
    """

    gap_stocks: list["GapStock"]
    new_candidates: list[dict]


@dataclass
class MonitoringResult:
    """Result from monitoring existing candidates for gap triggering

    Attributes:
        gap_stocks: List of GapStock objects meeting threshold
        triggered_candidates: List of dicts with triggered candidate info
    """

    gap_stocks: list["GapStock"]
    triggered_candidates: list[dict]


@dataclass
class ORTrackingResult:
    """Result from OR tracking scan

    Attributes:
        gap_stocks: List of GapStock objects for OR tracking
        or_tracking_candidates: List of dicts with candidate info
    """

    gap_stocks: list["GapStock"]
    or_tracking_candidates: list[dict]
