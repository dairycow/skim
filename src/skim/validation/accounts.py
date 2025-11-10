"""Pydantic models for account and portfolio validation

This module provides validation models for account information, portfolio
positions, and account-related operations in the IBKR trading system.
"""

from pydantic import BaseModel, Field, field_validator


class AccountBalance(BaseModel):
    """Account balance and margin information"""

    account_id: str = Field(..., min_length=1, description="Account ID")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency"
    )
    available_funds: float = Field(
        ..., description="Available funds for trading"
    )
    net_liquidation: float = Field(..., description="Net liquidation value")
    buying_power: float = Field(..., description="Total buying power")
    gross_position_value: float = Field(..., description="Gross position value")
    net_trading_liquidation: float = Field(
        ..., description="Net trading liquidation"
    )
    total_cash_balance: float = Field(..., description="Total cash balance")
    accrued_cash: float = Field(..., description="Accrued cash")
    futures_pnl: float = Field(..., description="Futures P&L")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    realized_pnl: float = Field(..., description="Realized P&L")
    exchange_rate: float | None = Field(
        None, gt=0, description="Exchange rate to base currency"
    )
    fund_ratio: float | None = Field(None, ge=0, le=1, description="Fund ratio")
    maintenance_margin: float | None = Field(
        None, description="Maintenance margin requirement"
    )
    initial_margin: float | None = Field(
        None, description="Initial margin requirement"
    )
    excess_liquidity: float | None = Field(None, description="Excess liquidity")
    cushion: float | None = Field(
        None, ge=0, le=100, description="Cushion percentage"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        return v.upper()

    @field_validator("cushion")
    @classmethod
    def validate_cushion_range(cls, v):
        """Validate cushion is within reasonable range"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Cushion must be between 0 and 100 percent")
        return v


class Position(BaseModel):
    """Portfolio position information"""

    account_id: str = Field(..., min_length=1, description="Account ID")
    conid: int = Field(..., gt=0, description="Contract ID")
    symbol: str = Field(..., min_length=1, max_length=10, description="Symbol")
    position: float = Field(
        ..., description="Position size (positive for long, negative for short)"
    )
    avg_price: float = Field(..., ge=0, description="Average price")
    mkt_price: float = Field(..., ge=0, description="Current market price")
    unrealized_pnl: float = Field(..., description="Unrealized P&L")
    realized_pnl: float = Field(..., description="Realized P&L")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Position currency"
    )
    market_value: float = Field(..., description="Market value")
    market_price: float = Field(
        ..., ge=0, description="Market price (alias for mkt_price)"
    )
    average_cost: float = Field(
        ..., ge=0, description="Average cost (alias for avg_price)"
    )
    sec_type: str | None = Field(None, description="Security type")

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

    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.position > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.position < 0

    @property
    def is_flat(self) -> bool:
        """Check if position is flat"""
        return abs(self.position) < 0.0001  # Allow for small rounding errors


class PortfolioSummary(BaseModel):
    """Portfolio summary information"""

    account_id: str = Field(..., min_length=1, description="Account ID")
    total_value: float = Field(..., description="Total portfolio value")
    total_cash: float = Field(..., description="Total cash")
    total_margin_used: float = Field(..., description="Total margin used")
    positions: list[Position] = Field(
        default_factory=list, description="List of positions"
    )
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Base currency"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        return v.upper()

    @property
    def total_positions_value(self) -> float:
        """Calculate total value of all positions"""
        return sum(pos.market_value for pos in self.positions)

    @property
    def total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        return sum(pos.unrealized_pnl for pos in self.positions)


class AccountRequest(BaseModel):
    """Request model for account information"""

    account_id: str | None = Field(
        None, description="Specific account ID (if not provided, returns all)"
    )
    portfolio: bool = Field(True, description="Include portfolio information")
    ledger: bool = Field(False, description="Include ledger information")
    performance: bool = Field(
        False, description="Include performance information"
    )


class Transaction(BaseModel):
    """Account transaction information"""

    account_id: str = Field(..., min_length=1, description="Account ID")
    transaction_id: str = Field(..., min_length=1, description="Transaction ID")
    datetime: str = Field(..., description="Transaction datetime")
    symbol: str | None = Field(None, description="Symbol if applicable")
    conid: int | None = Field(
        None, gt=0, description="Contract ID if applicable"
    )
    action: str | None = Field(None, description="Action (BUY/SELL/etc)")
    quantity: float | None = Field(None, description="Quantity")
    price: float | None = Field(None, ge=0, description="Price")
    commission: float | None = Field(None, description="Commission")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency"
    )
    description: str = Field(..., description="Transaction description")
    type: str = Field(..., description="Transaction type")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format"""
        if v:
            return v.upper().strip()
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency format"""
        return v.upper()


class AccountValidationError(Exception):
    """Raised when account validation fails"""

    pass


class InsufficientFundsError(Exception):
    """Raised when account has insufficient funds for operation"""

    pass


class PositionNotFoundError(Exception):
    """Raised when position is not found"""

    pass
