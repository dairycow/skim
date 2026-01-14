"""IBKR order management operations with async support"""

from typing import Any

from loguru import logger

from skim.infrastructure.brokers.ibkr import IBKRClient
from skim.infrastructure.brokers.protocols import (
    MarketDataProvider,
    OrderManager,
)
from skim.trading.data.models import OrderResult, Position


class IBKROrdersError(Exception):
    """Raised when order operations fail"""

    pass


class IBKROrders(OrderManager):
    """IBKR order management operations

    Handles order placement, cancellation, and position/balance queries.
    """

    def __init__(
        self, client: IBKRClient, market_data: MarketDataProvider
    ) -> None:
        """Initialize orders service

        Args:
            client: A connected IBKRClient instance.
            market_data: A market data provider for contract lookups.
        """
        self.client = client
        self.market_data = market_data

    async def place_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "MKT",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult | None:
        """Place order with flexible order types"""
        if order_type not in ("MKT", "STP", "STP LMT"):
            raise IBKROrdersError(f"Invalid order type: {order_type}")

        if order_type in ("STP", "STP LMT") and stop_price is None:
            raise IBKROrdersError(
                f"stop_price required for {order_type} orders"
            )

        if order_type == "STP LMT" and limit_price is None:
            raise IBKROrdersError("limit_price required for STP LMT orders")

        try:
            account_id = self.client.get_account()
            conid = await self.market_data.get_contract_id(ticker)

            order_data = {
                "conid": int(conid),
                "orderType": order_type,
                "side": action.upper(),
                "quantity": quantity,
                "tif": "DAY",
            }

            if limit_price is not None:
                order_data["price"] = limit_price
            if stop_price is not None:
                order_data["auxPrice"] = stop_price

            logger.info(
                f"Placing {order_type} order: {action} {quantity} {ticker} @ {order_data}"
            )

            endpoint = f"/iserver/account/{account_id}/orders"
            orders_payload = {"orders": [order_data]}

            response = await self.client._request(
                "POST", endpoint, data=orders_payload
            )
            logger.debug(f"Order response: {response}")

            order_result = self._parse_order_response(
                response, ticker, action, quantity
            )

            if order_result:
                return order_result

            if isinstance(response, list) and len(response) > 0:
                first_response = response[0]
                if (
                    isinstance(first_response, dict)
                    and "message" in first_response
                ):
                    reply_id = first_response.get("id")
                    if reply_id:
                        logger.info(
                            f"Order requires confirmation: {first_response.get('message')}"
                        )
                        return await self._confirm_order(
                            reply_id, ticker, action, quantity
                        )

            logger.error(f"Unexpected order response format: {response}")
            return None

        except Exception as e:
            logger.error(f"Failed to place order for {ticker}: {e}")
            return None

    async def get_open_orders(self) -> list[dict]:
        """Query all open orders"""
        try:
            endpoint = "/iserver/account/orders"
            response = await self.client._request("GET", endpoint)

            orders: list[dict] = []

            if isinstance(response, dict) and "orders" in response:
                orders_list = response["orders"]
            elif isinstance(response, list):
                orders_list = response
            else:
                logger.warning(f"Unexpected orders response format: {response}")
                return orders

            for order in orders_list:
                if isinstance(order, dict):
                    order_dict = {
                        "order_id": order.get("orderId") or order.get("id"),
                        "ticker": order.get("ticker") or order.get("symbol"),
                        "quantity": order.get("totalSize")
                        or order.get("quantity", 0),
                        "order_type": order.get("orderType"),
                        "status": order.get("status"),
                        "limit_price": order.get("price"),
                        "stop_price": order.get("auxPrice"),
                    }
                    orders.append(order_dict)

            return orders

        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise IBKROrdersError(f"Could not retrieve open orders: {e}") from e

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel specific order"""
        try:
            account_id = self.client.get_account()
            endpoint = f"/iserver/account/{account_id}/order/{order_id}"

            response = await self.client._request("DELETE", endpoint)
            logger.info(f"Cancel order response: {response}")

            if isinstance(response, dict) and (
                response.get("msg") == "Order cancelled"
                or response.get("conid")
            ):
                logger.info(f"Order {order_id} cancelled successfully")
                return True

            logger.info(f"Order {order_id} cancellation submitted")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_positions(self) -> list[Position]:
        """Get current positions from IBKR and convert to Position objects."""
        try:
            account_id = self.client.get_account()
            endpoint = f"/portfolio/{account_id}/positions/0"
            response = await self.client._request("GET", endpoint)

            positions: list[Position] = []

            if isinstance(response, list):
                for pos_data in response:
                    if isinstance(pos_data, dict):
                        position = self._convert_ibkr_position_to_position(
                            pos_data
                        )
                        if position:
                            positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise IBKROrdersError(f"Could not retrieve positions: {e}") from e

    def _convert_ibkr_position_to_position(
        self, ibkr_position: dict
    ) -> Position | None:
        """Converts an IBKR position dictionary to a Position object."""
        try:
            ticker = (
                ibkr_position.get("contractDesc")
                or ibkr_position.get("ticker")
                or ibkr_position.get("symbol")
            )
            quantity = int(ibkr_position.get("position", 0))
            entry_price = float(ibkr_position.get("avgPrice", 0.0))

            # IBKR does not provide stop loss directly in position data,
            # so we'll use a placeholder or derive it if possible.
            # For now, setting to entry_price for simplicity, but this needs
            # to be managed by the trading strategy.
            stop_loss = entry_price

            # IBKR does not provide entry_date directly in position data.
            # This would typically be stored in a local database.
            entry_date = ""  # Placeholder

            if ticker and quantity > 0:
                return Position(
                    ticker=ticker,
                    quantity=quantity,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    entry_date=entry_date,
                    status="open",
                    exit_price=None,
                    exit_date=None,
                    id=None,  # ID is for local DB, not from IBKR
                )
            return None
        except Exception as e:
            logger.error(
                f"Error converting IBKR position: {ibkr_position}. Error: {e}"
            )
            return None

    async def get_account_balance(self) -> dict:
        """Get account balance for position sizing"""
        try:
            account_id = self.client.get_account()
            endpoint = f"/portfolio/{account_id}/summary"
            response = await self.client._request("GET", endpoint)

            balance = {}

            if isinstance(response, dict):
                if "availablefunds" in response:
                    balance["availableFunds"] = float(
                        response["availablefunds"].get("amount", 0)
                    )
                if "netliquidation" in response:
                    balance["netLiquidation"] = float(
                        response["netliquidation"].get("amount", 0)
                    )
                if "buyingpower" in response:
                    balance["buyingPower"] = float(
                        response["buyingpower"].get("amount", 0)
                    )

                if not balance:
                    logger.warning(
                        f"Could not parse balance from response: {response}"
                    )
                    return response

            return balance

        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            raise IBKROrdersError(
                f"Could not retrieve account balance: {e}"
            ) from e

    def _parse_order_response(
        self, response: Any, ticker: str, action: str, quantity: int
    ) -> OrderResult | None:
        """Parse order placement response"""
        if isinstance(response, list) and len(response) > 0:
            first_response = response[0]

            if isinstance(first_response, dict):
                order_id = first_response.get("order_id") or first_response.get(
                    "id"
                )
                status = first_response.get("order_status", "submitted")

                if order_id:
                    return OrderResult(
                        order_id=str(order_id),
                        ticker=ticker,
                        action=action,
                        quantity=quantity,
                        status=status,
                    )

        return None

    async def _confirm_order(
        self, reply_id: str, ticker: str, action: str, quantity: int
    ) -> OrderResult | None:
        """Confirm order after receiving confirmation request"""
        try:
            confirm_endpoint = f"/iserver/reply/{reply_id}"
            confirm_data = {"confirmed": True}

            response = await self.client._request(
                "POST", confirm_endpoint, data=confirm_data
            )
            logger.debug(f"Confirmation response: {response}")

            if isinstance(response, list) and len(response) > 0:
                confirmed_order = response[0]
                if isinstance(confirmed_order, dict):
                    order_id = confirmed_order.get(
                        "order_id"
                    ) or confirmed_order.get("id")
                    status = confirmed_order.get("order_status", "submitted")

                    return OrderResult(
                        order_id=str(order_id),
                        ticker=ticker,
                        action=action,
                        quantity=quantity,
                        status=status,
                    )

            return None

        except Exception as e:
            logger.error(f"Order confirmation failed: {e}")
            return None
