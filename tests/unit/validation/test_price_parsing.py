"""Tests for price parsing utilities.

Tests robust price parsing for penny stocks and various price formats.
Follows TDD approach - tests are written first, then implementation.
"""

import pytest

from skim.validation.price_parsing import (
    PriceParsingError,
    clean_ibkr_price,
    parse_price_string,
    validate_minimum_price,
)


@pytest.mark.unit
class TestPriceParsing:
    """Tests for price parsing utilities"""

    def test_parse_price_string_normal_prices(self):
        """Test parsing normal price strings"""
        assert parse_price_string("1.50") == 1.50
        assert parse_price_string("100.00") == 100.00
        assert parse_price_string("0.99") == 0.99
        assert parse_price_string("25") == 25.0

    def test_parse_price_string_penny_stocks(self):
        """Test parsing penny stock price strings"""
        assert parse_price_string("0.005") == 0.005
        assert parse_price_string("0.001") == 0.001
        assert parse_price_string("0.009") == 0.009
        assert parse_price_string("0.0001") == 0.0001

    def test_parse_price_string_scientific_notation(self):
        """Test parsing scientific notation"""
        assert parse_price_string("5e-3") == 0.005
        assert parse_price_string("1.2E-4") == 0.00012
        assert parse_price_string("1e-3") == 0.001
        assert parse_price_string("2.5e-2") == 0.025

    def test_parse_price_string_with_commas(self):
        """Test parsing price strings with comma separators"""
        assert parse_price_string("1,234.56") == 1234.56
        assert parse_price_string("0,005") == 0.005  # European format
        assert parse_price_string("1,000.00") == 1000.00

    def test_parse_price_string_with_whitespace(self):
        """Test parsing price strings with whitespace"""
        assert parse_price_string(" 1.50 ") == 1.50
        assert parse_price_string("\t0.005\n") == 0.005
        assert parse_price_string("  100.00  ") == 100.00

    def test_parse_price_string_invalid_inputs(self):
        """Test parsing invalid price strings"""
        with pytest.raises(PriceParsingError):
            parse_price_string("")

        with pytest.raises(PriceParsingError):
            parse_price_string("abc")

        with pytest.raises(PriceParsingError):
            parse_price_string("1.2.3")

        with pytest.raises(PriceParsingError):
            parse_price_string(None)

    def test_clean_ibkr_price_normal_prices(self):
        """Test cleaning normal IBKR price strings"""
        assert clean_ibkr_price("1.50") == 1.50
        assert clean_ibkr_price("100.00") == 100.00
        assert clean_ibkr_price("0.99") == 0.99

    def test_clean_ibkr_price_with_prefixes(self):
        """Test cleaning IBKR price strings with prefixes"""
        assert clean_ibkr_price("C1.50") == 1.50  # Closed
        assert clean_ibkr_price("H0.005") == 0.005  # High
        assert clean_ibkr_price("L0.001") == 0.001  # Low
        assert clean_ibkr_price("O0.009") == 0.009  # Open

    def test_clean_ibkr_price_penny_stocks(self):
        """Test cleaning IBKR penny stock price strings"""
        assert clean_ibkr_price("0.005") == 0.005
        assert clean_ibkr_price("C0.001") == 0.001
        assert clean_ibkr_price("H5e-3") == 0.005
        assert clean_ibkr_price("L1.2E-4") == 0.00012

    def test_clean_ibkr_price_invalid_inputs(self):
        """Test cleaning invalid IBKR price strings"""
        with pytest.raises(PriceParsingError):
            clean_ibkr_price("")

        with pytest.raises(PriceParsingError):
            clean_ibkr_price("Cabc")

        with pytest.raises(PriceParsingError):
            clean_ibkr_price(None)

        with pytest.raises(PriceParsingError):
            clean_ibkr_price("X1.50")  # Invalid prefix

    def test_validate_minimum_price_valid_prices(self):
        """Test validation of valid minimum prices"""
        assert validate_minimum_price(0.001) is True
        assert validate_minimum_price(0.005) is True
        assert validate_minimum_price(0.01) is True
        assert validate_minimum_price(1.0) is True
        assert validate_minimum_price(100.0) is True

    def test_validate_minimum_price_threshold(self):
        """Test validation with custom threshold"""
        assert validate_minimum_price(0.001, min_threshold=0.0001) is True
        assert validate_minimum_price(0.0001, min_threshold=0.0001) is True
        assert validate_minimum_price(0.00005, min_threshold=0.0001) is False

    def test_validate_minimum_price_invalid_prices(self):
        """Test validation of invalid prices"""
        assert validate_minimum_price(0) is False
        assert validate_minimum_price(-0.001) is False
        assert validate_minimum_price(-1.0) is False

        # Test special float values
        assert validate_minimum_price(float("inf")) is False
        assert validate_minimum_price(float("-inf")) is False
        assert validate_minimum_price(float("nan")) is False

    def test_validate_minimum_price_edge_cases(self):
        """Test validation edge cases"""
        # Very small but valid prices
        assert validate_minimum_price(0.0001) is True
        assert validate_minimum_price(0.00001, min_threshold=0.00001) is True

        # Zero and negative prices
        assert validate_minimum_price(0.0) is False
        assert validate_minimum_price(-0.0001) is False


@pytest.mark.unit
class TestPriceParsingIntegration:
    """Integration tests for price parsing utilities"""

    def test_penny_stock_parsing_workflow(self):
        """Test complete workflow for parsing penny stock prices"""
        # Simulate IBKR API response for CR9
        raw_prices = {
            "31": "C0.005",  # Last price with prefix
            "84": "H0.004",  # Bid with prefix
            "86": "0.006",  # Ask without prefix
            "7": "L0.003",  # Low with prefix
        }

        # Parse each price
        last_price = clean_ibkr_price(raw_prices["31"])
        bid = clean_ibkr_price(raw_prices["84"])
        ask = clean_ibkr_price(raw_prices["86"])
        low = clean_ibkr_price(raw_prices["7"])

        # Validate parsed prices
        assert validate_minimum_price(last_price) is True
        assert validate_minimum_price(bid) is True
        assert validate_minimum_price(ask) is True
        assert validate_minimum_price(low) is True

        # Check final values
        assert last_price == 0.005
        assert bid == 0.004
        assert ask == 0.006
        assert low == 0.003

    def test_scientific_notation_workflow(self):
        """Test workflow with scientific notation prices"""
        # Simulate IBKR API response with scientific notation
        raw_prices = {
            "31": "5e-3",  # Last price
            "84": "4e-3",  # Bid
            "86": "6e-3",  # Ask
            "7": "3e-3",  # Low
        }

        # Parse each price
        last_price = clean_ibkr_price(raw_prices["31"])
        bid = clean_ibkr_price(raw_prices["84"])
        ask = clean_ibkr_price(raw_prices["86"])
        low = clean_ibkr_price(raw_prices["7"])

        # Validate and check
        assert validate_minimum_price(last_price) is True
        assert last_price == 0.005
        assert bid == 0.004
        assert ask == 0.006
        assert low == 0.003
