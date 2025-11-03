#!/usr/bin/env python3
"""Validate OAuth 1.0a configuration for IBKR API

This script checks that all required OAuth credentials and .pem files
are properly configured according to the IBind OAuth 1.0a guide:
https://github.com/Voyz/ibind/wiki/OAuth-1.0a
"""

import os
import re
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def check(condition: bool, success_msg: str, error_msg: str) -> bool:
    """Print check result with color"""
    if condition:
        print(f"{Colors.GREEN}✓{Colors.RESET} {success_msg}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.RESET} {error_msg}")
        return False


def warn(msg: str) -> None:
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET}  {msg}")


def info(msg: str) -> None:
    """Print info message"""
    print(f"{Colors.BLUE}ℹ{Colors.RESET}  {msg}")


def validate_oauth_configuration() -> bool:
    """Validate OAuth 1.0a configuration

    Returns:
        True if all checks pass, False otherwise
    """
    all_passed = True

    print(f"\n{Colors.BLUE}=== OAuth 1.0a Configuration Validation ==={Colors.RESET}\n")

    # 1. Check IBIND_USE_OAUTH
    use_oauth = os.getenv("IBIND_USE_OAUTH", "").lower()
    all_passed &= check(
        use_oauth == "true",
        "OAuth enabled (IBIND_USE_OAUTH=True)",
        "OAuth not enabled (IBIND_USE_OAUTH must be 'True')",
    )

    if use_oauth != "true":
        print(
            f"\n{Colors.YELLOW}OAuth is not enabled. "
            "Remaining checks are for OAuth configuration only.{Colors.RESET}\n"
        )
        return False

    # 2. Check consumer key
    consumer_key = os.getenv("IBIND_OAUTH1A_CONSUMER_KEY")
    all_passed &= check(
        bool(consumer_key),
        f"Consumer key present: {consumer_key}",
        "Consumer key missing (IBIND_OAUTH1A_CONSUMER_KEY)",
    )

    if consumer_key:
        if consumer_key.isupper() and consumer_key.isalnum():
            check(True, "Consumer key format valid (uppercase alphanumeric)", "")
        else:
            warn(
                f"Consumer key format unusual: '{consumer_key}' "
                "(expected uppercase alphanumeric)"
            )

        # Warn about paper trading
        warn(
            f"IMPORTANT: Verify consumer key '{consumer_key}' is for "
            "PAPER trading account (DU prefix)"
        )

    # 3. Check access token
    access_token = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN")
    all_passed &= check(
        bool(access_token),
        f"Access token present: {access_token[:10]}..." if access_token else "",
        "Access token missing (IBIND_OAUTH1A_ACCESS_TOKEN)",
    )

    # 4. Check access token secret
    secret = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN_SECRET")
    all_passed &= check(
        bool(secret),
        f"Access token secret present ({len(secret)} chars)" if secret else "",
        "Access token secret missing (IBIND_OAUTH1A_ACCESS_TOKEN_SECRET)",
    )

    # 5. Check signature key path
    sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
    all_passed &= check(
        bool(sig_path),
        f"Signature key path set: {sig_path}",
        "Signature key path missing (IBIND_OAUTH1A_SIGNATURE_KEY_FP)",
    )

    # 6. Check signature key file exists
    if sig_path:
        sig_file_exists = Path(sig_path).exists()
        all_passed &= check(
            sig_file_exists,
            f"Signature key file exists: {sig_path}",
            f"Signature key file NOT FOUND: {sig_path}",
        )

        # 7. Check signature key is readable and valid
        if sig_file_exists:
            try:
                content = Path(sig_path).read_text()
                is_private_key = (
                    "-----BEGIN RSA PRIVATE KEY-----" in content
                    or "-----BEGIN PRIVATE KEY-----" in content
                )
                all_passed &= check(
                    is_private_key,
                    "Signature key is valid RSA private key",
                    "Signature key does not appear to be an RSA private key",
                )

                size = Path(sig_path).stat().st_size
                check(
                    size >= 1000,
                    f"Signature key size OK ({size} bytes)",
                    f"Signature key seems too small ({size} bytes)",
                )
            except Exception as e:
                all_passed = False
                print(f"{Colors.RED}✗{Colors.RESET} Error reading signature key: {e}")

    # 8. Check encryption key path
    enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")
    all_passed &= check(
        bool(enc_path),
        f"Encryption key path set: {enc_path}",
        "Encryption key path missing (IBIND_OAUTH1A_ENCRYPTION_KEY_FP)",
    )

    # 9. Check encryption key file exists
    if enc_path:
        enc_file_exists = Path(enc_path).exists()
        all_passed &= check(
            enc_file_exists,
            f"Encryption key file exists: {enc_path}",
            f"Encryption key file NOT FOUND: {enc_path}",
        )

        # 10. Check encryption key is readable and valid
        if enc_file_exists:
            try:
                content = Path(enc_path).read_text()
                is_private_key = (
                    "-----BEGIN RSA PRIVATE KEY-----" in content
                    or "-----BEGIN PRIVATE KEY-----" in content
                )
                all_passed &= check(
                    is_private_key,
                    "Encryption key is valid RSA private key",
                    "Encryption key does not appear to be an RSA private key",
                )

                size = Path(enc_path).stat().st_size
                check(
                    size >= 1000,
                    f"Encryption key size OK ({size} bytes)",
                    f"Encryption key seems too small ({size} bytes)",
                )
            except Exception as e:
                all_passed = False
                print(f"{Colors.RED}✗{Colors.RESET} Error reading encryption key: {e}")

    # 11. Check DH prime
    dh_prime = os.getenv("IBIND_OAUTH1A_DH_PRIME")
    all_passed &= check(
        bool(dh_prime),
        f"DH prime present ({len(dh_prime)} chars)" if dh_prime else "",
        "DH prime missing (IBIND_OAUTH1A_DH_PRIME)",
    )

    # 12. Validate DH prime format
    if dh_prime:
        is_hex = bool(re.match(r"^[0-9a-fA-F]+$", dh_prime))
        all_passed &= check(
            is_hex,
            "DH prime format valid (hex string without spaces/colons)",
            "DH prime format invalid (must be hex string without spaces/colons)",
        )

        # Check length (2048-bit DH prime should be ~512 hex chars)
        if len(dh_prime) >= 256:
            check(
                True,
                f"DH prime length OK ({len(dh_prime)} chars, ~{len(dh_prime)*4}-bit)",
                "",
            )
        else:
            warn(
                f"DH prime seems short ({len(dh_prime)} chars), "
                "expected 512+ for 2048-bit DH params"
            )

    # Summary
    print(f"\n{Colors.BLUE}=== Summary ==={Colors.RESET}\n")

    if all_passed:
        print(
            f"{Colors.GREEN}✓ All OAuth configuration checks passed!{Colors.RESET}\n"
        )
        info("OAuth 1.0a authentication should work.")
        info("If you're still getting errors, check:")
        info("  1. Consumer key is for PAPER trading account (not live)")
        info("  2. OAuth credentials match what IBKR portal shows")
        info("  3. OAuth access was activated (can take up to 24 hours)")
        print()
        return True
    else:
        print(
            f"{Colors.RED}✗ Some OAuth configuration checks failed!{Colors.RESET}\n"
        )
        info("Fix the issues above and try again.")
        info(
            "Reference: https://github.com/Voyz/ibind/wiki/OAuth-1.0a"
        )
        print()
        return False


if __name__ == "__main__":
    success = validate_oauth_configuration()
    sys.exit(0 if success else 1)
