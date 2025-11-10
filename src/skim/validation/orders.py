"""Pydantic models for order management validation

This module provides validation models for order placement, status tracking,
and order management operations in the IBKR trading system.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderRequest(BaseModel):
    """Request model for order placement"""

    acctId: str = Field(..., min_length=1, description="Account ID")
    conid: int = Field(..., gt=0, description="Contract ID")
    orderType: Literal[
        "MKT", "STP", "STP LMT", "LMT", "MIT", "LOC", "REL", "TRAIL", "PEG MID"
    ] = Field(..., description="Order type")
    side: Literal["BUY", "SELL", "SSHORT"] = Field(
        ..., description="Order side"
    )
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: float | None = Field(
        None, gt=0, description="Limit price (for LMT orders)"
    )
    auxPrice: float | None = Field(
        None, gt=0, description="Stop price (for STP orders)"
    )
    tif: Literal["DAY", "IOC", "GTC", "OPG", "PAX"] = Field(
        "DAY", description="Time in force"
    )
    outsideRTH: bool = Field(
        False, description="Allow execution outside regular trading hours"
    )
    transmit: bool = Field(True, description="Transmit order immediately")
    parentId: int | None = Field(
        None, gt=0, description="Parent order ID for bracket orders"
    )

    @field_validator("price")
    @classmethod
    def validate_limit_price(cls, v, info):
        """Validate limit price is provided for limit orders"""
        order_type = info.data.get("orderType")
        if order_type in ["LMT", "STP LMT"] and v is None:
            raise ValueError(f"Price is required for {order_type} orders")
        return v

    @field_validator("auxPrice")
    @classmethod
    def validate_stop_price(cls, v, info):
        """Validate stop price is provided for stop orders"""
        order_type = info.data.get("orderType")
        if order_type in ["STP", "STP LMT", "TRAIL"] and v is None:
            raise ValueError(
                f"AuxPrice (stop price) is required for {order_type} orders"
            )
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        """Validate quantity is reasonable"""
        if v > 1000000:
            raise ValueError("Quantity too large - maximum 1,000,000 allowed")
        return v


class OrderStatus(BaseModel):
    """Order status information from IBKR"""

    order_id: int = Field(..., gt=0, description="Order ID")
    conid: int = Field(..., gt=0, description="Contract ID")
    symbol: str = Field(..., min_length=1, description="Symbol")
    side: Literal["BUY", "SELL", "SSHORT"] = Field(
        ..., description="Order side"
    )
    size: float = Field(..., gt=0, description="Order size")
    total_size: float = Field(..., gt=0, description="Total order size")
    order_status: Literal[
        "Inactive",
        "PendingSubmit",
        "PreSubmitted",
        "Submitted",
        "Filled",
        "PendingCancel",
        "Cancelled",
        "WarnState",
    ] = Field(..., description="Order status")
    order_type: str = Field(..., description="Order type")
    cum_fill: float = Field(..., ge=0, description="Cumulative filled quantity")
    average_price: float = Field(..., ge=0, description="Average fill price")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency"
    )
    last_fill_time: datetime | None = Field(None, description="Last fill time")
    remaining_qty: float = Field(..., ge=0, description="Remaining quantity")

    @field_validator("cum_fill")
    @classmethod
    def validate_cum_fill(cls, v, info):
        """Ensure cumulative fill doesn't exceed total size"""
        total_size = info.data.get("total_size", 0)
        if v > total_size:
            raise ValueError("Cumulative fill cannot exceed total order size")
        return v

    @field_validator("remaining_qty")
    @classmethod
    def validate_remaining_qty(cls, v, info):
        """Ensure remaining quantity is consistent"""
        total_size = info.data.get("total_size", 0)
        cum_fill = info.data.get("cum_fill", 0)
        expected_remaining = total_size - cum_fill
        if (
            abs(v - expected_remaining) > 0.01
        ):  # Allow small rounding differences
            raise ValueError(
                "Remaining quantity inconsistent with total size and cumulative fill"
            )
        return v


class OrderResult(BaseModel):
    """Result of order placement operation"""

    success: bool = Field(
        ..., description="Whether order was placed successfully"
    )
    order_id: int | None = Field(
        None, gt=0, description="Order ID if successful"
    )
    message: str = Field(..., description="Result message")
    error_code: str | None = Field(None, description="Error code if failed")
    order_status: OrderStatus | None = Field(
        None, description="Order status if available"
    )

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v, info):
        """Ensure order_id is provided for successful orders"""
        if info.data.get("success") and v is None:
            raise ValueError("Order ID is required for successful orders")
        return v


class OrderModificationRequest(BaseModel):
    """Request model for order modification"""

    order_id: int = Field(..., gt=0, description="Order ID to modify")
    quantity: float | None = Field(None, gt=0, description="New quantity")
    price: float | None = Field(None, gt=0, description="New limit price")
    auxPrice: float | None = Field(None, gt=0, description="New stop price")

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """Ensure at least one modification field is provided"""
        if not any(
            getattr(self, f) is not None
            for f in ["quantity", "price", "auxPrice"]
        ):
            raise ValueError("At least one modification field must be provided")
        return self


class OrderCancellationRequest(BaseModel):
    """Request model for order cancellation"""

    order_id: int = Field(..., gt=0, description="Order ID to cancel")
    account_id: str | None = Field(
        None, description="Account ID (optional for some endpoints)"
    )


class OrderValidationError(Exception):
    """Raised when order validation fails"""

    pass


class OrderExecutionError(Exception):
    """Raised when order execution fails"""

    pass
