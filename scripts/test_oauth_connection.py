#!/usr/bin/env python3
"""Test OAuth 1.0a connection to IBKR API

This script tests the OAuth connection by:
1. Initializing IBind client with OAuth credentials
2. Checking API health
3. Verifying session authentication
4. Retrieving account information

Run periodically to monitor OAuth connection health.
Usage:
    docker-compose exec bot python /app/scripts/test_oauth_connection.py

Or inside container:
    python /app/scripts/test_oauth_connection.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ibind import IbkrClient
from loguru import logger


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_status(success: bool, message: str) -> None:
    """Print status message with color"""
    if success:
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_info(message: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.RESET}  {message}")


def print_warn(message: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {message}")


def test_oauth_connection() -> bool:
    """Test OAuth 1.0a connection to IBKR API

    Returns:
        True if connection successful, False otherwise
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Colors.BLUE}=== OAuth Connection Test ==={Colors.RESET}")
    print(f"{Colors.BLUE}Timestamp: {timestamp}{Colors.RESET}\n")

    # 1. Check OAuth is enabled
    use_oauth = os.getenv("IBIND_USE_OAUTH", "").lower()
    if use_oauth != "true":
        print_status(False, "OAuth not enabled (IBIND_USE_OAUTH must be 'True')")
        print_info("Set IBIND_USE_OAUTH=True in your environment")
        return False

    print_status(True, "OAuth enabled")

    # 2. Verify OAuth credentials are present
    consumer_key = os.getenv("IBIND_OAUTH1A_CONSUMER_KEY")
    access_token = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN")
    access_secret = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN_SECRET")
    sig_key_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
    enc_key_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")
    dh_prime = os.getenv("IBIND_OAUTH1A_DH_PRIME")

    if not all([consumer_key, access_token, access_secret, sig_key_path, enc_key_path, dh_prime]):
        print_status(False, "Missing OAuth credentials")
        print_info("Run: python /app/scripts/validate_oauth.py")
        return False

    print_status(True, f"OAuth credentials configured (Consumer: {consumer_key})")

    # 3. Initialize IBind client with OAuth
    try:
        print_info("Initializing IBind client with OAuth 1.0a...")
        client = IbkrClient()  # OAuth mode - no URL needed
        print_status(True, "IBind client initialized")
    except Exception as e:
        print_status(False, f"Failed to initialize client: {e}")
        return False

    # 4. Check API health
    try:
        print_info("Checking IBKR API health...")
        health = client.check_health()

        if not health.ok:
            print_status(False, f"API health check failed: {health.error}")
            return False

        print_status(True, "API is healthy")
    except Exception as e:
        print_status(False, f"Health check error: {e}")
        return False

    # 5. Verify session authentication (tickle)
    try:
        print_info("Verifying OAuth session authentication...")
        tickle = client.tickle()

        if not tickle.ok:
            print_status(False, "Session not authenticated - OAuth handshake failed")
            print_warn("This could mean:")
            print_warn("  - OAuth credentials are incorrect")
            print_warn("  - Consumer key doesn't match account type (paper vs live)")
            print_warn("  - OAuth access not yet activated (can take up to 24 hours)")
            return False

        print_status(True, "OAuth session authenticated successfully")
    except Exception as e:
        print_status(False, f"Session authentication error: {e}")
        return False

    # 6. Retrieve account information
    try:
        print_info("Retrieving account information...")
        accounts = client.portfolio_accounts()

        if not accounts.ok or not accounts.data:
            print_status(False, f"Failed to retrieve accounts: {accounts.error}")
            return False

        account_id = accounts.data[0]["accountId"]
        print_status(True, f"Connected to account: {account_id}")

        # Check paper trading
        is_paper = account_id.startswith("DU")
        if is_paper:
            print_status(True, f"Account is PAPER TRADING (DU prefix)")
        else:
            print_warn(f"Account is LIVE TRADING (not DU prefix)")

        # Display account type
        account_type = accounts.data[0].get("type", "unknown")
        print_info(f"Account type: {account_type}")

    except Exception as e:
        print_status(False, f"Error retrieving accounts: {e}")
        return False

    # 7. Test market data endpoint (optional but good validation)
    try:
        print_info("Testing market data access (optional check)...")
        # Try to get a contract ID for a common stock
        test_ticker = "AAPL"
        conid_response = client.stock_conid_by_symbol(test_ticker)

        if conid_response.ok and conid_response.data:
            print_status(True, f"Market data access verified ({test_ticker} contract found)")
        else:
            print_warn("Market data access may be limited (non-critical)")
    except Exception as e:
        print_warn(f"Market data test skipped: {e}")

    # Summary
    print(f"\n{Colors.GREEN}=== Connection Test Passed ==={Colors.RESET}\n")
    print_info("OAuth 1.0a connection is working correctly")
    print_info(f"Account: {account_id} ({'PAPER' if is_paper else 'LIVE'})")
    print_info(f"Timestamp: {timestamp}")
    print()

    return True


def main():
    """Main entry point"""
    # Configure logger to be less verbose
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level="WARNING",  # Only show warnings and errors
        format="<level>{level}</level>: {message}",
    )

    try:
        success = test_oauth_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
