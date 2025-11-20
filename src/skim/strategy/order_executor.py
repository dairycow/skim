"""Order execution strategy - centralizes entry and exit order placement logic"""

from datetime import datetime

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.data.database import Database
from skim.data.models import Candidate, Position
from skim.strategy.position_manager import (
    calculate_position_size,
    calculate_stop_loss,
)


class OrderExecutor:
    """Handles order execution for entries and exits"""

    def __init__(self, ib_client: IBKRClient, db: Database):
        """
        Initialize OrderExecutor

        Args:
            ib_client: IBKR client for placing orders
            db: Database for recording positions and trades
        """
        self.ib_client = ib_client
        self.db = db

    def execute_entry(
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
            # Get market data
            conid = self.ib_client._get_contract_id(ticker)
            market_data = self.ib_client.get_market_data(conid)

            if (
                not market_data
                or not market_data.last_price
                or market_data.last_price <= 0
            ):
                logger.warning(f"{ticker}: No valid market data available")
                return None

            current_price = market_data.last_price

            # Calculate position size
            quantity = calculate_position_size(
                current_price,
                max_shares=max_position_size,
                max_value=position_value,
            )

            if quantity < 1:
                logger.warning(f"{ticker}: Calculated quantity too small")
                return None

            # Calculate stop loss based on source
            if stop_loss_source == "or_low" and hasattr(candidate, "or_low"):
                stop_loss = calculate_stop_loss(
                    current_price, low_of_day=candidate.or_low
                )
            else:
                # Default to daily low
                stop_loss = calculate_stop_loss(
                    current_price,
                    low_of_day=market_data.low if market_data.low > 0 else None,
                )

            logger.info(
                f"{ticker}: Position size={quantity}, Stop loss=${stop_loss:.4f}"
            )

            # Place order
            order_result = self.ib_client.place_order(ticker, "BUY", quantity)

            if not order_result:
                logger.warning(f"Order placement failed for {ticker}")
                return None

            logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

            # Use filled price if available, otherwise use current price
            fill_price = (
                order_result.filled_price
                if order_result.filled_price
                else current_price
            )

            logger.info(
                f"Order {order_result.status}: {quantity} {ticker} @ ${fill_price:.4f}"
            )

            # Record position
            position_id = self.db.create_position(
                ticker=ticker,
                quantity=quantity,
                entry_price=fill_price,
                stop_loss=stop_loss,
                entry_date=datetime.now().isoformat(),
            )

            # Record trade
            self.db.create_trade(
                ticker=ticker,
                action="BUY",
                quantity=quantity,
                price=fill_price,
                position_id=position_id,
                notes=f"Entry via {stop_loss_source}",
            )

            # Update candidate status
            self.db.update_candidate_status(ticker, "entered")

            return position_id

        except Exception as e:
            logger.error(f"Error executing order for {ticker}: {e}")
            return None

    def execute_exit(
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
            # Place order
            order_result = self.ib_client.place_order(ticker, "SELL", quantity)

            if not order_result:
                logger.warning(f"Exit order failed for {ticker}")
                return None

            logger.info(f"Exit order placed: SELL {quantity} {ticker}")

            # Use filled price if available
            fill_price = (
                order_result.filled_price if order_result.filled_price else None
            )

            if fill_price:
                # Calculate PnL
                pnl = (fill_price - position.entry_price) * quantity

                logger.info(
                    f"Exit executed: {quantity} {ticker} @ ${fill_price:.4f}, PnL: ${pnl:.4f}"
                )

                # Record trade
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
            logger.error(f"Error executing exit for {ticker}: {e}")
            return None
