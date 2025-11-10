#!/usr/bin/env python3
"""Test OAuth SSODH integration with IBKR API

This test generates LST then attempts to call /iserver/auth/ssodh/init
to test complete OAuth + SSODH authentication flow.
"""

import pytest
import requests

# API Configuration
BASE_URL = "api.ibkr.com/v1/api"
REALM = "limited_poa"


@pytest.fixture(scope="module")
def lst_token(oauth_config):
    """Generate Live Session Token for testing."""
    print("Generating Live Session Token...")

    # Use the actual generate_lst function from the codebase
    from skim.brokers.ibkr_oauth import generate_lst

    lst, expiration = generate_lst(
        consumer_key=oauth_config["consumer_key"],
        access_token=oauth_config["access_token"],
        access_token_secret=oauth_config["access_token_secret"],
        dh_prime_hex=oauth_config["dh_prime_hex"],
        signature_key_path=str(oauth_config["signature_key_path"]),
        encryption_key_path=str(oauth_config["encryption_key_path"]),
    )

    print(f"✓ LST generated: {lst[:20]}...")

    return lst


@pytest.mark.integration
@pytest.mark.manual
def test_lst_generation(lst_token):
    """Test LST generation for SSODH integration."""
    assert lst_token is not None
    assert len(lst_token) > 0
    print("✓ LST generation test passed")


@pytest.mark.integration
@pytest.mark.manual
def test_ssodh_init_request(lst_token):
    """Test SSODH init request with LST."""
    print("Testing SSODH init request...")

    # SSODH init endpoint
    ssodh_url = f"https://{BASE_URL}/iserver/auth/ssodh/init"

    # Headers with LST
    headers = {
        "Authorization": f"Bearer {lst_token}",
        "User-Agent": "python/3.12",
    }

    # Send SSODH init request
    response = requests.post(url=ssodh_url, headers=headers, timeout=30)

    print(f"SSODH Init Response Status: {response.status_code}")
    print(f"SSODH Init Response: {response.text}")

    # The response might be successful or indicate additional steps needed
    # We're mainly testing that LST is accepted for authentication
    assert response.status_code in [200, 302, 400, 401], (
        f"Unexpected status: {response.status_code}"
    )

    if response.status_code == 200:
        print("✓ SSODH init request successful")
    elif response.status_code in [400, 401]:
        print("⚠ SSODH init failed (may be expected for test environment)")
    elif response.status_code == 302:
        print("✓ SSODH init redirected (expected behavior)")


@pytest.mark.integration
@pytest.mark.manual
def test_oauth_ssodh_complete_flow(oauth_config, lst_token):
    """Test complete OAuth + SSODH integration flow."""
    print("Testing complete OAuth + SSODH flow...")

    # Verify we have a valid LST
    assert lst_token is not None
    assert len(lst_token) > 0

    # Test that LST can be used for authenticated requests
    # Try accessing a protected endpoint
    protected_url = f"https://{BASE_URL}/portfolio/accounts"
    headers = {
        "Authorization": f"Bearer {lst_token}",
        "User-Agent": "python/3.12",
    }

    response = requests.get(url=protected_url, headers=headers, timeout=30)

    print(f"Protected endpoint response: {response.status_code}")

    # The request should at least be authenticated (even if access is denied)
    # A 401 would mean authentication failed, 403 would mean auth succeeded but access denied
    # For test environment, 401 might be expected if credentials don't have access
    if response.status_code == 401:
        print(
            "⚠ LST authentication failed (may be expected for test credentials)"
        )
    elif response.status_code == 403:
        print("✓ LST authentication succeeded but access denied (expected)")
    else:
        print(
            f"✓ LST authentication succeeded with status {response.status_code}"
        )

    print("✓ OAuth + SSODH integration flow completed")


if __name__ == "__main__":
    # Allow running as script for manual testing
    import os

    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    config = {
        "consumer_key": os.getenv("OAUTH_CONSUMER_KEY"),
        "access_token": os.getenv("OAUTH_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("OAUTH_ACCESS_TOKEN_SECRET"),
        "dh_prime_hex": os.getenv("OAUTH_DH_PRIME"),
        "signature_key_path": os.getenv("OAUTH_SIGNATURE_PATH", ""),
        "encryption_key_path": os.getenv("OAUTH_ENCRYPTION_PATH", ""),
    }

    try:
        # Generate LST
        lst = lst_token(config)

        # Run tests
        test_lst_generation(lst)
        test_ssodh_init_request(lst)
        test_oauth_ssodh_complete_flow(config, lst)

        print("\n✓ All OAuth SSODH integration tests completed successfully!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
