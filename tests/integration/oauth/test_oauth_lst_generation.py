#!/usr/bin/env python3
"""Test OAuth LST generation with IBKR API.
This script creates a Live Session Token (LST) to authenticate with IBKR API.

Based on: https://www.interactivebrokers.com/campus/ibkr-api-page/oauth-1-0a-extended/
"""

import base64
import random
from datetime import datetime
from urllib.parse import quote, quote_plus

import pytest
import requests
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_Cipher
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_Signature

# API Configuration
BASE_URL = "api.ibkr.com/v1/api"
REALM = "limited_poa"  # or "test_realm" for testing


@pytest.mark.integration
@pytest.mark.manual
def test_load_rsa_keys(oauth_config):
    """Test loading RSA signature and encryption keys."""
    print("Loading RSA keys...")

    with open(oauth_config["signature_key_path"]) as f:
        signature_key = RSA.importKey(f.read())
        print(
            f"✓ Loaded signature key from {oauth_config['signature_key_path']}"
        )

    with open(oauth_config["encryption_key_path"]) as f:
        encryption_key = RSA.importKey(f.read())
        print(
            f"✓ Loaded encryption key from {oauth_config['encryption_key_path']}"
        )

    assert signature_key is not None
    assert encryption_key is not None

    return signature_key, encryption_key


@pytest.mark.integration
@pytest.mark.manual
def test_parse_dh_parameters(oauth_config):
    """Test parsing Diffie-Hellman parameters."""
    print("Parsing DH parameters...")

    dh_prime = int(oauth_config["dh_prime_hex"], 16)
    dh_generator = 2  # Always 2 for IBKR

    print(
        f"✓ DH Prime: {len(oauth_config['dh_prime_hex'])} hex chars (~{len(oauth_config['dh_prime_hex']) * 4}-bit)"
    )
    print(f"✓ DH Generator: {dh_generator}")

    assert dh_prime > 0
    assert dh_generator == 2

    return dh_prime, dh_generator


@pytest.mark.integration
@pytest.mark.manual
def test_generate_dh_challenge():
    """Test generating Diffie-Hellman challenge."""
    print("Generating Diffie-Hellman challenge...")

    dh_prime = int(
        "00f4c0ac1c6a120cffe7c0438769be9f35a721c6c7aed77a6a676a2811fb4277ab501bc686d644c32cb8ed232b7270fe59e31980f06334f847a21199fb4278469314be62ab11febde1de4279d698738b18ac878d6ba0bc9005888b0097a7bd0cdcac84b99605a9c4d910c340aa29ff1ec485365d21804972028c5766187c8b3fafa284af904bcd0b7e5641f61985c6e7e0d4f09f39f635c9afb12f0c0d5ac72946907c974f7dfb6a9f1c292a2864801738a98ac7d956c29aecab8f5ca14e920b376901b202582450dca5aa6fc77e155b87a10d58941ac6d5474e621fa8fbead777db9b2086db2712be183a2ff4192a05241e414ae6fa128819b1bc433d382a2787",
        16,
    )
    dh_generator = 2
    dh_random = random.getrandbits(256)

    print("✓ Generated 256-bit random value")

    # dh_challenge = (generator ^ dh_random) mod dh_prime
    dh_challenge = hex(pow(dh_generator, dh_random, dh_prime))[2:]
    print(f"✓ DH Challenge calculated ({len(dh_challenge)} hex chars)")

    assert len(dh_challenge) > 0

    return dh_challenge


@pytest.mark.integration
@pytest.mark.manual
def test_decrypt_access_token_secret(oauth_config):
    """Test decrypting access token secret to get prepend."""
    print("Decrypting access token secret...")

    with open(oauth_config["encryption_key_path"]) as f:
        encryption_key = RSA.importKey(f.read())

    decrypted_secret = PKCS1_v1_5_Cipher.new(key=encryption_key).decrypt(
        ciphertext=base64.b64decode(oauth_config["access_token_secret"]),
        sentinel=None,
    )
    assert decrypted_secret is not None, "Failed to decrypt access token secret"
    prepend = decrypted_secret.hex()
    print(f"✓ Prepend calculated ({len(prepend)} chars)")

    assert len(prepend) > 0

    return prepend


@pytest.mark.integration
@pytest.mark.manual
def test_build_oauth_parameters(oauth_config, dh_challenge):
    """Test building OAuth parameters."""
    print("Building OAuth parameters...")

    oauth_params = {
        "diffie_hellman_challenge": dh_challenge,
        "oauth_consumer_key": oauth_config["consumer_key"],
        "oauth_nonce": hex(random.getrandbits(128))[2:],
        "oauth_signature_method": "RSA-SHA256",
        "oauth_timestamp": str(int(datetime.now().timestamp())),
        "oauth_token": oauth_config["access_token"],
    }

    print("✓ OAuth params created:")
    print(f"  - Consumer Key: {oauth_config['consumer_key']}")
    print(f"  - Access Token: {oauth_config['access_token']}")
    print(f"  - Timestamp: {oauth_params['oauth_timestamp']}")
    print(f"  - Nonce: {oauth_params['oauth_nonce']}")

    assert all(
        key in oauth_params
        for key in [
            "diffie_hellman_challenge",
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
        ]
    )

    return oauth_params


@pytest.mark.integration
@pytest.mark.manual
def test_create_signature_base_string(oauth_config, oauth_params, prepend):
    """Test creating OAuth signature base string."""
    print("Creating signature base string...")

    url = f"https://{BASE_URL}/oauth/live_session_token"
    params_string = "&".join(
        [f"{k}={v}" for k, v in sorted(oauth_params.items())]
    )
    base_string = f"{prepend}POST&{quote_plus(url)}&{quote(params_string)}"
    encoded_base_string = base_string.encode("utf-8")

    print(f"✓ Base string created ({len(base_string)} chars)")
    print("  Method: POST")
    print(f"  URL: {url}")

    assert len(base_string) > 0

    return base_string, encoded_base_string, url


@pytest.mark.integration
@pytest.mark.manual
def test_sign_request(oauth_config, oauth_params, encoded_base_string):
    """Test signing the OAuth request."""
    print("Signing request...")

    with open(oauth_config["signature_key_path"]) as f:
        signature_key = RSA.importKey(f.read())

    sha256_hash = SHA256.new(data=encoded_base_string)
    bytes_pkcs115_signature = PKCS1_v1_5_Signature.new(
        rsa_key=signature_key
    ).sign(msg_hash=sha256_hash)
    b64_str_pkcs115_signature = base64.b64encode(
        bytes_pkcs115_signature
    ).decode("utf-8")
    oauth_params["oauth_signature"] = quote_plus(b64_str_pkcs115_signature)
    oauth_params["realm"] = REALM

    print("✓ Request signed with RSA-SHA256")

    assert "oauth_signature" in oauth_params
    assert oauth_params["realm"] == REALM

    return oauth_params


@pytest.mark.integration
@pytest.mark.manual
def test_build_authorization_header(oauth_params):
    """Test building OAuth authorization header."""
    print("Building authorization header...")

    oauth_header = "OAuth " + ", ".join(
        [f'{k}="{v}"' for k, v in sorted(oauth_params.items())]
    )
    headers = {"authorization": oauth_header, "User-Agent": "python/3.12"}

    print("✓ Authorization header created")

    assert "authorization" in headers
    assert headers["authorization"].startswith("OAuth ")

    return headers


@pytest.mark.integration
@pytest.mark.manual
def test_send_oauth_request(headers, url):
    """Test sending OAuth request to IBKR API."""
    print(f"\n{'=' * 60}")
    print("SENDING REQUEST TO IBKR API...")
    print(f"{'=' * 60}")
    print(f"URL: {url}")
    print("Method: POST")
    print(f"Headers: {headers.keys()}")

    response = requests.post(url=url, headers=headers, timeout=30)

    print(f"\n{'=' * 60}")
    print("RESPONSE RECEIVED")
    print(f"{'=' * 60}")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("\nResponse Body:")
    print(response.text)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )

    try:
        lst_data = response.json()
        print(
            f"\nLive Session Token: {lst_data.get('live_session_token', 'N/A')}"
        )
        print(
            f"Diffie-Hellman Response: {lst_data.get('diffie_hellman_response', 'N/A')[:50]}..."
        )

        assert "live_session_token" in lst_data
        return lst_data

    except (ValueError, KeyError) as e:
        pytest.fail(f"Failed to parse response JSON: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_full_oauth_flow(oauth_config):
    """Test the complete OAuth flow to generate LST."""
    print("Testing complete OAuth flow...")

    # Load keys
    signature_key, encryption_key = test_load_rsa_keys(oauth_config)

    # Parse DH parameters
    dh_prime, dh_generator = test_parse_dh_parameters(oauth_config)

    # Generate DH challenge
    dh_challenge = test_generate_dh_challenge()

    # Decrypt access token secret
    prepend = test_decrypt_access_token_secret(oauth_config)

    # Build OAuth parameters
    oauth_params = test_build_oauth_parameters(oauth_config, dh_challenge)

    # Create signature base string
    base_string, encoded_base_string, url = test_create_signature_base_string(
        oauth_config, oauth_params, prepend
    )

    # Sign request
    oauth_params = test_sign_request(
        oauth_config, oauth_params, encoded_base_string
    )

    # Build authorization header
    headers = test_build_authorization_header(oauth_params)

    # Send request
    lst_data = test_send_oauth_request(headers, url)

    print(f"\n{'=' * 60}")
    print("✓ SUCCESS - OAuth authentication successful!")
    print(f"{'=' * 60}")

    return lst_data


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
        test_full_oauth_flow(config)
        print("\n✓ OAuth LST generation test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
