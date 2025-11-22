"""Order execution strategy - centralises entry and exit order placement logic"""

from datetime import datetime

from loguru import logger as default_logger

from skim.brokers.protocols import MarketDataProvider, OrderManager
from skim.data.database import Database
from skim.data.models import Candidate, Position
from skim.strategy.position_manager import (
    calculate_position_size,
    calculate_stop_loss,
)


class OrderExecutor:
    """Handles order execution for entries and exits"""

    def __init__(
        self,
        orders: OrderManager,
        market_data: MarketDataProvider,
        db: Database,
        logger=None,
    ):
        """
        Initialize OrderExecutor

        Args:
            orders: Order service for placing/cancelling orders
            market_data: Service for retrieving market data
            db: Database for recording positions and trades
            logger: Optional logger instance (defaults to loguru logger)
        """
        self.orders = orders
        self.market_data = market_data
        self.db = db
        self.logger = logger or default_logger

    async def execute_entry(
        self,
        candidate: Candidate,
        stop_loss_source: str = "daily_low",
        max_position_size: int = 1000,
        position_value: float = 5000.0,
    ) -> int | None:
        """
        Execute entry order for a candidate

        Args:
            candidate: Candidate to enter
            stop_loss_source: "daily_low" or "or_low" - where to get stop loss from
            max_position_size: Maximum shares per position
            position_value: Target dollar value per position

        Returns:
            position_id if successful, None if failed
        """
        ticker = candidate.ticker

        try:
            market_data = await self.market_data.get_market_data(ticker)

            if (
                not market_data
                or not market_data.last_price
                or market_data.last_price <= 0
            ):
                self.logger.warning(f"{ticker}: No valid market data available")
                return None

            current_price = market_data.last_price

            quantity = calculate_position_size(
                current_price,
                max_shares=max_position_size,
                max_value=position_value,
            )

            if quantity < 1:
                self.logger.warning(f"{ticker}: Calculated quantity too small")
                return None

            if stop_loss_source == "or_low" and hasattr(candidate, "or_low"):
                stop_loss = calculate_stop_loss(
                    current_price, low_of_day=candidate.or_low
                )
            else:
                daily_low = market_data.low if market_data.low > 0 else None
                stop_loss = calculate_stop_loss(
                    current_price,
                    low_of_day=daily_low,
                )

                if daily_low is None or daily_low <= 0:
                    self.logger.warning(
                        f"{ticker}: Using fallback stop loss: ${stop_loss:.4f} (daily low unavailable)"
                    )

            self.logger.info(
                f"{ticker}: Position size={quantity}, Stop loss=${stop_loss:.4f}"
            )

            order_result = await self.orders.place_order(
                ticker, "BUY", quantity
            )

            if not order_result:
                self.logger.warning(f"Order placement failed for {ticker}")
                return None

            self.logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

            fill_price = (
                order_result.filled_price
                if order_result.filled_price
                else current_price
            )

            self.logger.info(
                f"Order {order_result.status}: {quantity} {ticker} @ ${fill_price:.4f}"
            )

            position_id = self.db.create_position(
                ticker=ticker,
                quantity=quantity,
                entry_price=fill_price,
                stop_loss=stop_loss,
                entry_date=datetime.now().isoformat(),
            )

            self.db.create_trade(
                ticker=ticker,
                action="BUY",
                quantity=quantity,
                price=fill_price,
                position_id=position_id,
                notes=f"Entry via {stop_loss_source}",
            )

            self.db.update_candidate_status(ticker, "entered")

            return position_id

        except Exception as e:
            self.logger.error(f"Error executing order for {ticker}: {e}")
            return None

    async def execute_exit(
        self,
        position: Position,
        quantity: int,
        reason: str = "Manual exit",
    ) -> float | None:
        """
        Execute exit order for a position

        Args:
            position: Position to exit
            quantity: Quantity to sell
            reason: Reason for exit (for logging)

        Returns:
            Fill price if successful, None if failed
        """
        ticker = position.ticker

        try:
            order_result = await self.orders.place_order(
                ticker, "SELL", quantity
            )

            if not order_result:
                self.logger.warning(f"Exit order failed for {ticker}")
                return None

            self.logger.info(f"Exit order placed: SELL {quantity} {ticker}")

            fill_price = (
                order_result.filled_price if order_result.filled_price else None
            )

            if fill_price:
                pnl = (fill_price - position.entry_price) * quantity

                self.logger.info(
                    f"Exit executed: {quantity} {ticker} @ ${fill_price:.4f}, PnL: ${pnl:.4f}"
                )

                self.db.create_trade(
                    ticker=ticker,
                    action="SELL",
                    quantity=quantity,
                    price=fill_price,
                    position_id=position.id,
                    pnl=pnl,
                    notes=reason,
                )

            return fill_price

        except Exception as e:
            self.logger.error(f"Error executing exit for {ticker}: {e}")
            return None
