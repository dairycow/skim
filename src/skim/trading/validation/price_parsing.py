"""Price parsing utilities for IBKR market data.

Provides robust parsing of price strings including penny stocks,
scientific notation, and IBKR-specific prefixes.
"""

import re


class PriceParsingError(Exception):
    """Raised when price parsing fails"""

    pass


def parse_price_string(value: str | int | float | None) -> float:
    """Parse a price string into a float.

    Args:
        value: Price value to parse (string, int, float, or None)

    Returns:
        Parsed price as float

    Raises:
        PriceParsingError: If parsing fails
    """
    if value is None:
        raise PriceParsingError("Cannot parse None value")

    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        raise PriceParsingError(f"Unsupported type: {type(value)}")

    # Remove whitespace
    cleaned = value.strip()

    if not cleaned:
        raise PriceParsingError("Empty string cannot be parsed")

    # Handle comma separators (both thousand separators and decimal commas)
    # European format: 1.234,56 -> 1234.56
    # US format: 1,234.56 -> 1234.56
    if "," in cleaned:
        # If there's both comma and period, assume European format
        if "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) == 2 and "," in parts[1]:
                # European format: 1.234,56
                integer_part = parts[0].replace(",", "")
                decimal_part = parts[1].replace(",", "")
                cleaned = f"{integer_part}.{decimal_part}"
            else:
                # US format: 1,234.56
                cleaned = cleaned.replace(",", "")
        else:
            # Only comma, could be decimal separator or thousands
            # If it's at the end and there are digits before, treat as decimal
            if re.match(r"^\d+,\d{1,3}$", cleaned):
                cleaned = cleaned.replace(",", ".")
            else:
                # Thousands separator
                cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError as e:
        raise PriceParsingError(f"Cannot parse price '{value}': {e}") from e


def clean_ibkr_price(value: str | int | float | None) -> float:
    """Clean and parse IBKR price strings with prefixes.

    IBKR sometimes prefixes prices with:
    - C: Closed price
    - H: High price
    - L: Low price
    - O: Open price

    Args:
        value: IBKR price value to clean

    Returns:
        Cleaned price as float

    Raises:
        PriceParsingError: If cleaning fails
    """
    if value is None:
        raise PriceParsingError("Cannot parse None value")

    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        raise PriceParsingError(f"Unsupported type: {type(value)}")

    # Remove whitespace
    cleaned = value.strip()

    if not cleaned:
        raise PriceParsingError("Empty string cannot be parsed")

    # Remove IBKR prefixes (first character if it's a letter)
    if len(cleaned) > 1 and cleaned[0].isalpha():
        # Valid prefixes are C, H, L, O
        if cleaned[0] in ["C", "H", "L", "O"]:
            cleaned = cleaned[1:]
        else:
            raise PriceParsingError(f"Invalid IBKR prefix: {cleaned[0]}")

    # Parse the remaining price
    return parse_price_string(cleaned)


def validate_minimum_price(price: float, min_threshold: float = 0.0001) -> bool:
    """Validate that a price meets minimum requirements.

    Args:
        price: Price to validate
        min_threshold: Minimum allowed price (default: 0.0001)

    Returns:
        True if price is valid, False otherwise
    """
    # Check for special float values
    if not isinstance(price, (int, float)):
        return False

    # Check for NaN
    if price != price:
        return False

    # Check for infinity
    if price in (float("inf"), float("-inf")):
        return False

    # Check minimum threshold
    return price > 0 and price >= min_threshold


def safe_parse_price(
    value: str | int | float | None, default: float = 0.0
) -> float:
    """Safely parse a price with fallback to default value.

    Args:
        value: Price value to parse
        default: Default value if parsing fails

    Returns:
        Parsed price or default value
    """
    try:
        return clean_ibkr_price(value)
    except PriceParsingError:
        return default
