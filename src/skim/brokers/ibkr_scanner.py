"""IBKR scanner operations with async support"""

import logging
from typing import Any

from ..core.config import ScannerConfig
from ..validation.scanners import GapStock, ScannerValidationError
from .ibkr_client import IBKRClient
from .protocols import ScannerService

logger = logging.getLogger(__name__)


class IBKRScannerError(Exception):
    """Raised when scanner operations fail"""

    pass


class IBKRScanner(ScannerService):
    """IBKR market scanner operations

    Handles low-level scanner execution and gap scanning.
    """

    def __init__(
        self,
        client: IBKRClient,
        scanner_config: ScannerConfig | None = None,
    ) -> None:
        """Initialize scanner service

        Args:
            client: A connected IBKRClient instance.
            scanner_config: Scanner configuration parameters.
        """
        self.client = client
        self.scanner_config = scanner_config or ScannerConfig()

    async def run_scanner(self, scan_params: dict) -> list[dict]:
        """Run market scanner with specified parameters"""
        if not self.client.is_connected():
            raise IBKRScannerError("Not connected - call connect() first")

        if not scan_params:
            raise IBKRScannerError("Scan parameters cannot be empty")

        logger.info(f"Running scanner with parameters: {scan_params}")

        try:
            response = await self.client._request(
                "POST", "/iserver/scanner/run", data=scan_params
            )
        except Exception as e:
            logger.error(f"Scanner request failed: {e}")
            raise IBKRScannerError(f"Failed to run scanner: {e}") from e

        return self._parse_scanner_response(response)

    async def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Scan for ASX stocks with gaps using IBKR scanner"""
        if not self.client.is_connected():
            raise IBKRScannerError("Not connected - call connect() first")

        logger.info(f"Scanning for ASX gaps > {min_gap}%")

        try:
            scan_params = self._create_gap_scan_params(min_gap)
            logger.debug(f"Scanner parameters: {scan_params}")

            scanner_results = await self.run_scanner(scan_params)
            logger.info(f"IBKR scanner returned {len(scanner_results)} results")

            gap_stocks = []
            for result in scanner_results:
                try:
                    gap_stock = self._validate_and_create_gap_stock(
                        result, min_gap
                    )
                    if gap_stock:
                        gap_stocks.append(gap_stock)
                except Exception as e:
                    logger.warning(
                        f"Gap stock validation failed for {result.get('symbol')}: {e}"
                    )
                    continue

            gap_stocks.sort(key=lambda x: x.gap_percent, reverse=True)

            logger.info(f"Found {len(gap_stocks)} gap stocks > {min_gap}%")
            return gap_stocks

        except Exception as e:
            if isinstance(e, IBKRScannerError):
                raise
            logger.error(f"Error scanning for gaps: {e}")
            raise IBKRScannerError(f"Gap scan failed: {e}") from e

    async def get_scanner_params(self) -> dict:
        """Get available scanner parameters from IBKR"""
        if not self.client.is_connected():
            raise IBKRScannerError("Not connected - call connect() first")

        logger.info("Retrieving scanner parameters")

        try:
            response = await self.client._request(
                "GET", "/iserver/scanner/params"
            )

            if not isinstance(response, dict):
                logger.warning(
                    f"Unexpected scanner params response format: {type(response)}"
                )
                return {}

            instrument_types = list(response.keys())
            logger.info(
                f"Scanner parameters retrieved for instruments: {instrument_types}"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to retrieve scanner parameters: {e}")
            raise IBKRScannerError(
                f"Failed to get scanner parameters: {e}"
            ) from e

    def _create_gap_scan_params(self, min_gap: float) -> dict:
        """Create IBKR scanner parameters for gap scanning"""
        try:
            scan_params = {
                "instrument": "STOCK.HK",
                "type": "HIGH_OPEN_GAP",
                "filter": [
                    {
                        "code": "price",
                        "value": self.scanner_config.price_filter,
                    },
                    {
                        "code": "volume",
                        "value": self.scanner_config.volume_filter,
                    },
                ],
                "location": "STK.HK.ASX",
            }
            logger.debug(f"Created ASX gap scan parameters: {scan_params}")
            return scan_params
        except Exception as e:
            logger.error(f"Failed to create scanner parameters: {e}")
            raise ScannerValidationError(
                f"Invalid scanner parameters: {e}"
            ) from e

    def _parse_scanner_response(self, response: Any) -> list[dict]:
        """Parse IBKR scanner response into standardized format"""
        if isinstance(response, dict) and "contracts" in response:
            return self._parse_new_format(response["contracts"])

        if not isinstance(response, list):
            logger.warning(
                f"Unexpected scanner response format: {type(response)}"
            )
            return []

        return self._parse_old_format(response)

    def _parse_new_format(self, contracts: list) -> list[dict]:
        """Parse new IBKR scanner response format"""
        results = []
        logger.info(f"Scanner returned {len(contracts)} contracts (new format)")

        for contract in contracts:
            if not isinstance(contract, dict):
                continue

            result = {
                "conid": contract.get("con_id"),
                "symbol": contract.get("symbol"),
                "companyHeader": contract.get("company_name"),
            }

            scan_data = contract.get("scan_data")
            if scan_data and isinstance(scan_data, str):
                try:
                    gap_pct = float(scan_data.replace("+", "").replace("%", ""))
                    result["change_percent"] = gap_pct
                except ValueError:
                    logger.debug(f"Could not parse gap percentage: {scan_data}")

            results.append(result)

        return results

    def _parse_old_format(self, response: list) -> list[dict]:
        """Parse old IBKR scanner response format"""
        results = []

        for item in response:
            if not isinstance(item, dict):
                logger.debug(f"Skipping non-dict scanner result: {item}")
                continue

            result = {
                "conid": item.get("conid"),
                "symbol": item.get("symbol"),
                "companyHeader": item.get("companyHeader"),
            }

            field_mapping = {
                "31": "last_price",
                "83": "change_percent",
                "86": "ask",
                "87": "volume",
                "7741": "previous_close",
                "7295": "today_open",
            }

            for field_code, field_name in field_mapping.items():
                if field_code in item:
                    value = item[field_code]
                    if field_name == "volume":
                        result[field_name] = int(value) if value else 0
                    elif field_name in [
                        "last_price",
                        "change_percent",
                        "previous_close",
                        "today_open",
                    ]:
                        result[field_name] = float(value) if value else 0.0
                    else:
                        result[field_name] = value

            if result.get("conid") and result.get("symbol"):
                results.append(result)
            else:
                logger.debug(f"Skipping incomplete scanner result: {result}")

        logger.info(
            f"Scanner returned {len(results)} valid results (old format)"
        )
        return results

    def _validate_and_create_gap_stock(
        self, result: dict, min_gap: float
    ) -> GapStock | None:
        """Validate scanner result and create GapStock object"""
        symbol = result.get("symbol")
        conid = result.get("conid")
        gap_percent = result.get("change_percent", 0.0)

        if not symbol or not conid:
            logger.debug(f"Skipping result with missing symbol/conid: {result}")
            return None

        if gap_percent < min_gap:
            logger.debug(
                f"Filtered {symbol}: gap={gap_percent:.2f}% < min_gap={min_gap}%"
            )
            return None

        try:
            gap_stock = GapStock(
                ticker=str(symbol),
                gap_percent=float(gap_percent),
                conid=int(conid),
            )
            logger.debug(f"Added gap stock: {symbol} gap={gap_percent:.2f}%")
            return gap_stock
        except Exception as validation_error:
            logger.warning(
                f"Gap stock validation failed for {symbol}: {validation_error}"
            )
            raise
