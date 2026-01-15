"""IBKR market data operations with async support

Handles:
- Contract ID lookups and caching
- Single and batch market data fetching
- Price parsing and validation
- Field mapping
"""

import asyncio

from loguru import logger

from skim.infrastructure.brokers.ibkr import IBKRClient
from skim.infrastructure.brokers.protocols import MarketDataProvider
from skim.domain.models import MarketData

from ..validation.price_parsing import (
    clean_ibkr_price,
    safe_parse_price,
    validate_minimum_price,
)


class IBKRMarketDataError(Exception):
    """Raised when market data operations fail"""

    pass


class IBKRMarketData(MarketDataProvider):
    """IBKR market data operations

    Handles contract lookups, market data snapshots, and batch operations.
    Internally manages contract ID caching to reduce API calls.
    """

    def __init__(self, client: IBKRClient) -> None:
        """Initialize market data service

        Args:
            client: A connected IBKRClient instance.
        """
        self.client = client
        self._contract_cache: dict[str, str] = {}  # ticker -> conid
        self._market_data_streams: set[str] = (
            set()
        )  # conids with established streams
        self._warmup_delay_seconds: float = 1.0

    async def get_market_data(
        self,
        tickers: str | list[str],
    ) -> MarketData | dict[str, MarketData | None] | None:
        """Get market data for one or more tickers (handles contract lookup internally)

        - Pass a string for single ticker → returns MarketData | None
        - Pass a list for multiple tickers → returns dict with concurrent fetching

        Args:
            tickers: Stock ticker symbol (e.g., "BHP") or list of symbols

        Returns:
            - If tickers is str: MarketData object if successful, None on failure
            - If tickers is list: dict mapping ticker -> MarketData (or None if failed)
        """
        if isinstance(tickers, str):
            return await self._fetch_single_market_data(tickers)

        if not tickers:
            return {}

        logger.info(
            f"Fetching market data for {len(tickers)} tickers concurrently"
        )

        tasks = [self._fetch_single_market_data(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        market_data_dict = {}
        for ticker, result in zip(tickers, results, strict=True):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {ticker}: {result}")
                market_data_dict[ticker] = None
            else:
                market_data_dict[ticker] = result

        return market_data_dict

    async def _fetch_single_market_data(self, ticker: str) -> MarketData | None:
        """Fetch market data for a single ticker"""
        try:
            conid = await self._get_contract_id(ticker)

            if conid not in self._market_data_streams:
                await self._establish_market_data_stream(conid)
                self._market_data_streams.add(conid)

            market_data = await self._fetch_market_snapshot(conid, ticker)

            if self._should_warmup_snapshot(market_data):
                logger.info(
                    f"{ticker}: retrying snapshot after IBKR pre-flight warm-up"
                )
                await asyncio.sleep(self._warmup_delay_seconds)
                await self._establish_market_data_stream(conid)
                market_data = await self._fetch_market_snapshot(conid, ticker)

            return market_data

        except Exception as e:
            logger.error(f"Failed to get market data for {ticker}: {e}")
            return None

    async def get_contract_id(self, ticker: str) -> str:
        """Public method to look up IBKR contract ID for a ticker (with caching)."""
        return await self._get_contract_id(ticker)

    async def _get_contract_id(self, ticker: str) -> str:
        """Look up contract ID with caching."""
        if ticker in self._contract_cache:
            logger.debug(
                f"Contract ID for {ticker} found in cache: {self._contract_cache[ticker]}"
            )
            return self._contract_cache[ticker]

        logger.info(f"Looking up contract ID for {ticker}")

        try:
            endpoint = "/iserver/secdef/search"
            params = {"symbol": ticker}
            response = await self.client._request(
                "GET", endpoint, params=params
            )

            logger.debug(f"Contract search response for {ticker}: {response}")

            conid = self._parse_contract_response(response, ticker)

            if not conid:
                raise IBKRMarketDataError(
                    f"Could not find contract ID for ticker: {ticker}. Response: {response}"
                )

            self._contract_cache[ticker] = conid
            logger.debug(f"Cached contract ID for {ticker}: {conid}")

            return conid

        except Exception as e:
            if isinstance(e, IBKRMarketDataError):
                raise
            raise IBKRMarketDataError(
                f"Contract lookup failed for {ticker}: {e}"
            ) from e

    def _parse_contract_response(
        self, response: list | dict | None, ticker: str
    ) -> str | None:
        """Parse contract ID from IBKR search response."""
        if not isinstance(response, list):
            return None

        conid = None
        asx_conid = None

        for contract in response:
            if not isinstance(contract, dict):
                continue

            description = contract.get("description", "")
            sections = contract.get("sections", [])

            has_stk = any(
                isinstance(section, dict) and section.get("secType") == "STK"
                for section in sections
            )

            if has_stk:
                current_conid = str(contract.get("conid"))
                logger.debug(
                    f"Found STK contract: {contract.get('companyHeader')} - conid: {current_conid}"
                )

                if "ASX" in description.upper():
                    asx_conid = current_conid
                    logger.debug(
                        f"Found ASX contract: {contract.get('companyHeader')}"
                    )
                    break

                if not conid:
                    conid = current_conid

        return asx_conid or conid

    async def _establish_market_data_stream(self, conid: str) -> None:
        """Establish market data stream for a contract via preflight request."""
        logger.info(f"Establishing market data stream for conid: {conid}")

        try:
            endpoint = "/iserver/marketdata/snapshot"
            params = {"conids": conid, "fields": "31"}

            response = await self.client._request(
                "GET", endpoint, params=params
            )
            logger.debug(f"Pre-flight response for {conid}: {response}")

            if not (
                isinstance(response, list)
                and len(response) > 0
                and isinstance(response[0], dict)
                and str(response[0].get("conid")) == conid
            ):
                raise IBKRMarketDataError(
                    f"Failed to establish market data stream for {conid}"
                )

            logger.info(f"Market data stream established for {conid}")

        except Exception as e:
            if isinstance(e, IBKRMarketDataError):
                raise
            raise IBKRMarketDataError(
                f"Pre-flight request failed for {conid}: {e}"
            ) from e

    async def _fetch_market_snapshot(
        self, conid: str, ticker: str | None = None
    ) -> MarketData | None:
        """Fetch market data snapshot for a contract."""
        try:
            endpoint = "/iserver/marketdata/snapshot"
            params = {
                "conids": conid,
                "fields": "31,70,71,84,85,86,87,88,7295,7741,83",
            }

            response = await self.client._request(
                "GET", endpoint, params=params
            )
            logger.debug(f"Market data response for {conid}: {response}")

            if not isinstance(response, list) or len(response) == 0:
                logger.warning(
                    f"Invalid market data response for {conid}: {response}"
                )
                return None

            data = response[0]
            if not isinstance(data, dict):
                logger.warning(
                    f"Invalid market data format for {conid}: {data}"
                )
                return None

            market_data_dict = self._parse_market_data_fields(data)

            if not validate_minimum_price(
                market_data_dict.get("last_price", 0.0), min_threshold=0.0001
            ):
                logger.warning(
                    f"Invalid last price for {conid}: {market_data_dict.get('last_price')}"
                )
                return None

            if not ticker:
                ticker = str(data.get("55", f"CONID_{conid}"))
            if not ticker:
                ticker = f"CONID_{conid}"

            return MarketData(
                ticker=ticker,
                conid=conid,
                last_price=market_data_dict.get("last_price", 0.0),
                high=market_data_dict.get("high", 0.0),
                low=market_data_dict.get("low", 0.0),
                bid=market_data_dict.get("bid", 0.0),
                ask=market_data_dict.get("ask", 0.0),
                bid_size=market_data_dict.get("bid_size", 0),
                ask_size=market_data_dict.get("ask_size", 0),
                volume=market_data_dict.get("volume", 0),
                open=market_data_dict.get("open", 0.0),
                prior_close=market_data_dict.get("prior_close", 0.0),
                change_percent=market_data_dict.get("change_percent", 0.0),
            )

        except Exception as e:
            logger.error(f"Market data fetch failed for {conid}: {e}")
            return None

    def _parse_market_data_fields(self, data: dict) -> dict:
        """Parse IBKR market data fields to human-readable format."""
        field_mappings = {
            "31": ("last_price", float),
            "70": ("high", float),
            "71": ("low", float),
            "84": ("bid", float),
            "85": ("ask_size", int),
            "86": ("ask", float),
            "87": ("volume", int),
            "88": ("bid_size", int),
            "7295": ("open", float),
            "7741": ("prior_close", float),
            "83": ("change_percent", float),
        }

        result = {}
        for field_code, (field_name, field_type) in field_mappings.items():
            raw_value = data.get(field_code)
            if raw_value is not None:
                try:
                    if field_type is float:
                        if field_name in [
                            "last_price",
                            "bid",
                            "ask",
                            "high",
                            "low",
                            "open",
                            "prior_close",
                        ]:
                            result[field_name] = clean_ibkr_price(raw_value)
                        else:
                            result[field_name] = safe_parse_price(
                                raw_value, 0.0
                            )
                    elif field_type is int:
                        result[field_name] = int(safe_parse_price(raw_value, 0))
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to parse {field_name} ({field_code}): {e}"
                    )
                    result[field_name] = 0 if field_type is int else 0.0
            else:
                result[field_name] = 0 if field_type is int else 0.0

        return result

    def clear_cache(self) -> None:
        """Clear contract ID cache (useful for testing)"""
        self._contract_cache.clear()
        self._market_data_streams.clear()
        logger.info("Cleared market data caches")

    def _should_warmup_snapshot(self, market_data: MarketData | None) -> bool:
        """Determine if a warm-up retry is needed (first snapshot often empty)."""
        if market_data is None:
            return True
        if market_data.last_price <= 0:
            return True
        return (
            market_data.high <= 0
            and market_data.low <= 0
            and market_data.volume <= 0
        )
