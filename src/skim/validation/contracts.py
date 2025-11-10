"""Pydantic models for contract and instrument validation

This module provides validation models for contract information and security
definitions, ensuring data quality for instrument lookup and validation.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ContractInfo(BaseModel):
    """Basic contract information from IBKR"""

    con_id: int = Field(..., gt=0, description="Contract ID")
    symbol: str = Field(..., min_length=1, max_length=10, description="Symbol")
    company_name: str | None = Field(None, description="Company name")
    instrument_type: Literal[
        "STK", "OPT", "FUT", "FOP", "CASH", "CRYPTO", "BOND", "WAR", "FUND"
    ] = Field(..., description="Instrument type")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency"
    )
    exchange: str = Field(..., min_length=1, description="Primary exchange")
    valid_exchanges: str = Field(
        ..., description="Valid exchanges for this contract"
    )
    is_zero_commission_security: bool = Field(
        default=False, description="Zero commission flag"
    )
    smart_available: bool = Field(
        default=True, description="Smart routing available"
    )
    multiplier: str | None = Field(None, description="Contract multiplier")
    primary_exchange: str | None = Field(None, description="Primary exchange")
    industry: str | None = Field(None, description="Industry sector")
    category: str | None = Field(None, description="Category")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format"""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        return v.upper()


class SecurityDefinition(BaseModel):
    """Detailed security definition from IBKR"""

    conid: int = Field(..., gt=0, description="Contract ID")
    ticker: str = Field(
        ..., min_length=1, max_length=10, description="Ticker symbol"
    )
    secType: Literal[
        "STK", "OPT", "FUT", "FOP", "CASH", "CRYPTO", "BOND", "WAR", "FUND"
    ] = Field(..., description="Security type")
    listingExchange: str = Field(..., description="Listing exchange")
    companyName: str | None = Field(None, description="Company name")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency"
    )
    maturityDate: str | None = Field(
        None, description="Maturity date for derivatives"
    )
    right: Literal["P", "C"] | None = Field(
        None, description="Option right (Put/Call)"
    )
    strike: float | None = Field(
        None, gt=0, description="Strike price for options"
    )
    multiplier: str | None = Field(None, description="Contract multiplier")
    tradingClass: str | None = Field(None, description="Trading class")
    minTick: float | None = Field(None, gt=0, description="Minimum tick size")
    priceMagnifier: int | None = Field(
        None, gt=0, description="Price magnifier"
    )
    underlyingConid: int | None = Field(
        None, gt=0, description="Underlying contract ID"
    )
    longName: str | None = Field(None, description="Long name/description")
    exchange: str | None = Field(None, description="Exchange")
    primaryExchange: str | None = Field(None, description="Primary exchange")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v):
        """Validate ticker format"""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        return v.upper()

    @field_validator("strike")
    @classmethod
    def validate_strike_for_options(cls, v, info):
        """Validate strike price is provided for options"""
        sec_type = info.data.get("secType")
        if sec_type in ["OPT", "FOP"] and v is None:
            raise ValueError("Strike price is required for options")
        return v

    @field_validator("right")
    @classmethod
    def validate_right_for_options(cls, v, info):
        """Validate right is provided for options"""
        sec_type = info.data.get("secType")
        if sec_type in ["OPT", "FOP"] and v is None:
            raise ValueError("Right (P/C) is required for options")
        return v

    @field_validator("maturityDate")
    @classmethod
    def validate_maturity_for_derivatives(cls, v, info):
        """Validate maturity date for derivative products"""
        sec_type = info.data.get("secType")
        if sec_type in ["OPT", "FUT", "FOP"] and v is None:
            raise ValueError(
                "Maturity date is required for derivative products"
            )
        return v


class ContractSearchRequest(BaseModel):
    """Request model for contract search"""

    symbol: str = Field(
        ..., min_length=1, max_length=10, description="Symbol to search"
    )
    secType: (
        Literal[
            "STK", "OPT", "FUT", "FOP", "CASH", "CRYPTO", "BOND", "WAR", "FUND"
        ]
        | None
    ) = Field(None, description="Security type filter")
    exchange: str | None = Field(None, description="Exchange filter")
    currency: str | None = Field(
        None, min_length=3, max_length=3, description="Currency filter"
    )
    isin: str | None = Field(
        None, min_length=12, max_length=12, description="ISIN identifier"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format"""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        if v:
            return v.upper()
        return v


class OptionChainRequest(BaseModel):
    """Request model for option chain data"""

    underlying_conid: int = Field(
        ..., gt=0, description="Underlying contract ID"
    )
    secType: Literal["OPT", "FOP"] = Field(
        "OPT", description="Option security type"
    )
    exchange: str | None = Field(None, description="Exchange")
    currency: str | None = Field(
        None, min_length=3, max_length=3, description="Currency"
    )
    expiration: str | None = Field(None, description="Specific expiration date")
    strike_range: Literal["OTM", "ITM", "ALL", "NEAR", "FAR"] | None = Field(
        "ALL", description="Strike range filter"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        if v:
            return v.upper()
        return v


class ContractValidationError(Exception):
    """Raised when contract validation fails"""

    pass


class ContractNotFoundError(Exception):
    """Raised when contract is not found"""

    pass
