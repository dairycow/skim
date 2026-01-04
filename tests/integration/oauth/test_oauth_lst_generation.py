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


@pytest.fixture(scope="module")
def signature_keys(oauth_config):
    """Load RSA signature and encryption keys for testing."""
    print("Loading RSA keys...")

    with open(str(oauth_config["signature_key_path"])) as f:
        signature_key = RSA.importKey(f.read())
        print(
            f"✓ Loaded signature key from {str(oauth_config['signature_key_path']).split('/')[-1]}"
        )

    with open(str(oauth_config["encryption_key_path"])) as f:
        encryption_key = RSA.importKey(f.read())
        print(
            f"✓ Loaded encryption key from {str(oauth_config['encryption_key_path']).split('/')[-1]}"
        )

    assert signature_key is not None
    assert encryption_key is not None

    return signature_key, encryption_key


@pytest.mark.integration
@pytest.mark.manual
def test_load_rsa_keys(signature_keys):
    """Test loading RSA signature and encryption keys."""
    signature_key, encryption_key = signature_keys

    assert signature_key is not None
    assert encryption_key is not None
    print("✓ RSA keys loading test passed")


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


@pytest.fixture(scope="module")
def dh_challenge():
    """Generate Diffie-Hellman challenge for testing."""
    print("Generating Diffie-Hellman challenge...")

    dh_prime = int(
        "00f4c0ac1c6a120cffe7c0438769be9f35a721c6c7aed77a6a676a2811fb4277ab501bc686d644c32cb8ed232b7270fe59e31980f06334f847a21199fb4278469314be62ab11febde1de4279d698738b18ac878d6ba0bc9005888b0097a7bd0cdcac84b99605a9c4d910c340aa29ff1ec485365d21804972028c5766187c8b3fafa284af904bcd0b7e5641f61985c6e7e0d4f09f39f635c9afb12f0c0d5ac72946907c974f7dfb6a9f1c292a2864801738a98ac7d956c29aecab8f5ca14e920b376901b202582450dca5aa6fc77e155b87a10d58941ac6d5474e621fa8fbead777db9b2086db2712be183a2ff4192a05241e414ae6fa128819b1bc433d382a2787",
        16,
    )
    dh_generator = 2
    dh_random = random.getrandbits(256)

    print("✓ Generated 256-bit random value")

    # dh_challenge = (generator ^ dh_random) mod dh_prime
    challenge = hex(pow(dh_generator, dh_random, dh_prime))[2:]
    print(f"✓ DH Challenge calculated ({len(challenge)} hex chars)")

    assert len(challenge) > 0

    return challenge


@pytest.mark.integration
@pytest.mark.manual
def test_generate_dh_challenge():
    """Test generating Diffie-Hellman challenge."""
    # This test is now handled by the dh_challenge fixture
    pass


@pytest.fixture(scope="module")
def prepend(oauth_config):
    """Decrypt access token secret to get prepend for testing."""
    print("Decrypting access token secret...")

    with open(str(oauth_config["encryption_key_path"])) as f:
        encryption_key = RSA.importKey(f.read())

    decrypted_secret = PKCS1_v1_5_Cipher.new(key=encryption_key).decrypt(
        ciphertext=base64.b64decode(oauth_config["access_token_secret"]),
        sentinel=None,
    )
    assert decrypted_secret is not None, "Failed to decrypt access token secret"
    prepend_value = decrypted_secret.hex()
    print(f"✓ Prepend calculated ({len(prepend_value)} chars)")

    assert len(prepend_value) > 0

    return prepend_value


@pytest.mark.integration
@pytest.mark.manual
def test_decrypt_access_token_secret(prepend):
    """Test decrypting access token secret to get prepend."""
    assert prepend is not None
    assert len(prepend) > 0
    print("✓ Access token secret decryption test passed")


@pytest.fixture(scope="module")
def oauth_params(oauth_config, dh_challenge):
    """Build OAuth parameters for testing."""
    print("Building OAuth parameters...")

    params = {
        "diffie_hellman_challenge": dh_challenge,
        "oauth_consumer_key": oauth_config["consumer_key"],
        "oauth_nonce": hex(random.getrandbits(128))[2:],
        "oauth_signature_method": "RSA-SHA256",
        "oauth_timestamp": str(int(datetime.now().timestamp())),
        "oauth_token": oauth_config["access_token"],
    }

    print("✓ OAuth params created:")
    print(f"  - Consumer Key: {oauth_config['consumer_key'][:8]}...")
    print(f"  - Access Token: {oauth_config['access_token'][:8]}...")
    print(f"  - Timestamp: {params['oauth_timestamp']}")
    print(f"  - Nonce: {params['oauth_nonce']}")

    assert all(
        key in params
        for key in [
            "diffie_hellman_challenge",
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
        ]
    )

    return params


@pytest.fixture(scope="module")
def signature_base_string_data(oauth_config, oauth_params, prepend):
    """Create signature base string for testing."""
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


@pytest.fixture(scope="module")
def signed_oauth_params(oauth_config, oauth_params, signature_base_string_data):
    """Sign OAuth parameters for testing."""
    print("Signing request...")

    signature_key, _ = None, None  # We'll load fresh

    with open(str(oauth_config["signature_key_path"])) as f:
        signature_key = RSA.importKey(f.read())

    _, encoded_base_string, _ = signature_base_string_data

    sha256_hash = SHA256.new(data=encoded_base_string)
    bytes_pkcs115_signature = PKCS1_v1_5_Signature.new(
        rsa_key=signature_key
    ).sign(msg_hash=sha256_hash)
    b64_str_pkcs115_signature = base64.b64encode(
        bytes_pkcs115_signature
    ).decode("utf-8")

    signed_params = oauth_params.copy()
    signed_params["oauth_signature"] = quote_plus(b64_str_pkcs115_signature)
    signed_params["realm"] = REALM

    print("✓ Request signed with RSA-SHA256")

    assert "oauth_signature" in signed_params
    assert signed_params["realm"] == REALM

    return signed_params


@pytest.fixture(scope="module")
def oauth_headers(signed_oauth_params):
    """Build OAuth authorization header for testing."""
    print("Building authorization header...")

    oauth_header = "OAuth " + ", ".join(
        [f'{k}="{v}"' for k, v in sorted(signed_oauth_params.items())]
    )
    headers = {"authorization": oauth_header, "User-Agent": "python/3.12"}

    print("✓ Authorization header created")

    assert "authorization" in headers
    assert headers["authorization"].startswith("OAuth ")

    return headers


@pytest.fixture(scope="module")
def lst_response(oauth_headers, signature_base_string_data):
    """Generate Live Session Token by calling IBKR API."""
    _, _, url = signature_base_string_data

    # Send request
    response = requests.post(url=url, headers=oauth_headers, timeout=30)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}"
    )

    response_data = response.json()
    assert "diffie_hellman_response" in response_data

    print(
        f"✓ LST response received: {response_data.get('live_session_token_signature', 'N/A')}"
    )
    return response_data


@pytest.mark.integration
@pytest.mark.manual
def test_build_oauth_parameters():
    """Test building OAuth parameters."""
    # This test is now handled by the oauth_params fixture
    pass


@pytest.mark.integration
@pytest.mark.manual
def test_create_signature_base_string():
    """Test creating OAuth signature base string."""
    # This test is now handled by the signature_base_string_data fixture
    pass


@pytest.mark.integration
@pytest.mark.manual
def test_sign_request(signed_oauth_params):
    """Test signing the OAuth request."""
    assert signed_oauth_params is not None
    assert "oauth_signature" in signed_oauth_params
    assert signed_oauth_params["realm"] == REALM
    print("✓ OAuth request signing test passed")


@pytest.mark.integration
@pytest.mark.manual
def test_build_authorization_header(oauth_headers):
    """Test building OAuth authorization header."""
    assert oauth_headers is not None
    assert "authorization" in oauth_headers
    assert oauth_headers["authorization"].startswith("OAuth ")
    print("✓ OAuth authorization header test passed")


@pytest.mark.integration
@pytest.mark.manual
def test_send_oauth_request(oauth_headers, signature_base_string_data):
    """Test sending OAuth request to IBKR API."""
    _, _, url = signature_base_string_data

    print(f"\n{'=' * 60}")
    print("SENDING REQUEST TO IBKR API...")
    print(f"{'=' * 60}")
    print(f"URL: {url}")
    print("Method: POST")
    print(f"Headers: {oauth_headers.keys()}")

    response = requests.post(url=url, headers=oauth_headers, timeout=30)

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
        response_data = response.json()
        print(
            f"\nDiffie-Hellman Response: {response_data.get('diffie_hellman_response', 'N/A')[:50]}..."
        )
        print(
            f"LST Signature: {response_data.get('live_session_token_signature', 'N/A')}"
        )
        print(
            f"LST Expiration: {response_data.get('live_session_token_expiration', 'N/A')}"
        )

        # The LST is not directly in the response - it needs to be computed
        # from the DH response. We'll return to raw response data.
        assert "diffie_hellman_response" in response_data
        print("✓ OAuth request test passed")

    except (ValueError, KeyError) as e:
        pytest.fail(f"Failed to parse response JSON: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_full_oauth_flow(oauth_config):
    """Test the complete OAuth flow to generate LST."""
    print("Testing complete OAuth flow...")

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

    print(f"\n{'=' * 60}")
    print("✓ SUCCESS - OAuth authentication successful!")
    print(f"Live Session Token: {lst[:20]}...")
    print(f"Expiration: {expiration}")
    print(f"{'=' * 60}")

    assert lst is not None
    assert len(lst) > 0
    assert expiration > 0

    # No return value to keep pytest happy (warnings on non-None returns)


if __name__ == "__main__":
    # Allow running as script for manual testing
    import os

    from tests.integration.conftest import validate_oauth_environment

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
        # For script execution, we need to implement the flow directly
        # since the test functions are now designed for pytest fixtures

        # Load keys
        with open(config["signature_key_path"]) as f:
            signature_key = RSA.importKey(f.read())
        with open(config["encryption_key_path"]) as f:
            encryption_key = RSA.importKey(f.read())

        # Parse DH parameters
        script_dh_prime = int(config["dh_prime_hex"], 16)
        script_dh_generator = 2

        # Generate DH challenge
        script_dh_random = random.getrandbits(256)
        script_dh_challenge = hex(
            pow(script_dh_generator, script_dh_random, script_dh_prime)
        )[2:]

        # Decrypt access token secret
        script_decrypted_secret = PKCS1_v1_5_Cipher.new(
            key=encryption_key
        ).decrypt(
            ciphertext=base64.b64decode(config["access_token_secret"]),
            sentinel=None,
        )
        if script_decrypted_secret is None:
            raise RuntimeError("Failed to decrypt access token secret")
        script_prepend = script_decrypted_secret.hex()

        # Build OAuth parameters
        script_oauth_params = {
            "diffie_hellman_challenge": script_dh_challenge,
            "oauth_consumer_key": config["consumer_key"],
            "oauth_nonce": hex(random.getrandbits(128))[2:],
            "oauth_signature_method": "RSA-SHA256",
            "oauth_timestamp": str(int(datetime.now().timestamp())),
            "oauth_token": config["access_token"],
        }

        # Create signature base string
        script_url = f"https://{BASE_URL}/oauth/live_session_token"
        script_params_string = "&".join(
            [f"{k}={v}" for k, v in sorted(script_oauth_params.items())]
        )
        script_base_string = f"{script_prepend}POST&{quote_plus(script_url)}&{quote(script_params_string)}"
        script_encoded_base_string = script_base_string.encode("utf-8")

        # Sign request
        script_sha256_hash = SHA256.new(data=script_encoded_base_string)
        script_bytes_pkcs115_signature = PKCS1_v1_5_Signature.new(
            rsa_key=signature_key
        ).sign(msg_hash=script_sha256_hash)
        script_b64_str_pkcs115_signature = base64.b64encode(
            script_bytes_pkcs115_signature
        ).decode("utf-8")
        script_oauth_params["oauth_signature"] = quote_plus(
            script_b64_str_pkcs115_signature
        )
        script_oauth_params["realm"] = REALM

        # Build authorization header
        script_oauth_header = "OAuth " + ", ".join(
            [f'{k}="{v}"' for k, v in sorted(script_oauth_params.items())]
        )
        script_headers = {
            "authorization": script_oauth_header,
            "User-Agent": "python/3.12",
        }

        # Send request
        response = requests.post(
            url=script_url, headers=script_headers, timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(f"OAuth request failed: {response.status_code}")

        lst_data = response.json()
        print(
            f"✓ LST generated: {lst_data.get('live_session_token', 'N/A')[:20]}..."
        )

        print("\n✓ OAuth LST generation test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
