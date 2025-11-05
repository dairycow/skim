"""OAuth 1.0a authentication for IBKR Client Portal API

This module handles Live Session Token (LST) generation using OAuth 1.0a
with Diffie-Hellman key exchange and RSA signing.

Based on: https://www.interactivebrokers.com/campus/ibkr-api-page/oauth-1-0a-extended/
"""

import base64
import hmac
import random
from datetime import datetime
from hashlib import sha1, sha256
from pathlib import Path
from urllib.parse import quote, quote_plus

import requests
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_Cipher
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_Signature


def generate_lst(
    consumer_key: str,
    access_token: str,
    access_token_secret: str,
    dh_prime_hex: str,
    signature_key_path: str,
    encryption_key_path: str,
    realm: str = "limited_poa",
) -> tuple[str, int]:
    """Generate Live Session Token for IBKR API authentication

    This implements the full OAuth 1.0a flow with Diffie-Hellman key exchange:
    1. Load RSA keys (signature + encryption)
    2. Generate DH random value (256-bit)
    3. Calculate DH challenge: (2 ^ random) mod prime
    4. Decrypt access token secret to get prepend value
    5. Build OAuth params and sign request with RSA-SHA256
    6. POST to /oauth/live_session_token
    7. Compute final LST from DH response using HMAC-SHA1

    Args:
        consumer_key: OAuth consumer key (e.g., "PSKIMMILK")
        access_token: OAuth access token
        access_token_secret: Encrypted access token secret (base64)
        dh_prime_hex: Diffie-Hellman prime number (hex string)
        signature_key_path: Path to RSA signature private key (.pem)
        encryption_key_path: Path to RSA encryption private key (.pem)
        realm: OAuth realm ("limited_poa" for live/paper)

    Returns:
        Tuple of (live_session_token, expiration_timestamp_ms)

    Raises:
        RuntimeError: If OAuth request fails or LST validation fails
        FileNotFoundError: If RSA key files not found
        ValueError: If DH prime or keys are invalid
    """
    # Step 1: Load RSA keys
    signature_key = RSA.importKey(Path(signature_key_path).read_text())
    encryption_key = RSA.importKey(Path(encryption_key_path).read_text())

    # Step 2: Parse DH prime and generator
    dh_prime = int(dh_prime_hex, 16)
    dh_generator = 2  # Always 2 for IBKR

    # Step 3: Generate DH random value (256-bit)
    dh_random = random.getrandbits(256)

    # Step 4: Calculate DH challenge = (generator ^ dh_random) mod dh_prime
    dh_challenge = hex(pow(dh_generator, dh_random, dh_prime))[2:]

    # Step 5: Decrypt access token secret to get prepend value
    bytes_decrypted_secret = PKCS1_v1_5_Cipher.new(key=encryption_key).decrypt(
        ciphertext=base64.b64decode(access_token_secret),
        sentinel=None,
    )
    prepend = bytes_decrypted_secret.hex()

    # Step 6: Build OAuth parameters
    oauth_params = {
        "diffie_hellman_challenge": dh_challenge,
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": hex(random.getrandbits(128))[2:],
        "oauth_signature_method": "RSA-SHA256",
        "oauth_timestamp": str(int(datetime.now().timestamp())),
        "oauth_token": access_token,
    }

    # Step 7: Create signature base string with prepend
    url = "https://api.ibkr.com/v1/api/oauth/live_session_token"
    params_string = "&".join([f"{k}={v}" for k, v in sorted(oauth_params.items())])
    base_string = f"{prepend}POST&{quote_plus(url)}&{quote(params_string)}"

    # Step 8: Sign base string with RSA-SHA256
    sha256_hash = SHA256.new(data=base_string.encode("utf-8"))
    bytes_pkcs115_signature = PKCS1_v1_5_Signature.new(rsa_key=signature_key).sign(
        msg_hash=sha256_hash
    )
    b64_str_pkcs115_signature = base64.b64encode(bytes_pkcs115_signature).decode(
        "utf-8"
    )
    oauth_params["oauth_signature"] = quote_plus(b64_str_pkcs115_signature)
    oauth_params["realm"] = realm

    # Step 9: Build authorization header
    oauth_header = "OAuth " + ", ".join(
        [f'{k}="{v}"' for k, v in sorted(oauth_params.items())]
    )
    headers = {"authorization": oauth_header, "User-Agent": "skim-trading-bot/1.0"}

    # Step 10: Send request to IBKR API
    response = requests.post(url=url, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"OAuth LST request failed: {response.status_code} - {response.text}"
        )

    lst_data = response.json()
    dh_response = lst_data.get("diffie_hellman_response")
    lst_signature = lst_data.get("live_session_token_signature")
    lst_expiration = lst_data.get("live_session_token_expiration")

    # Step 11: Compute Live Session Token from DH response
    prepend_bytes = bytes.fromhex(prepend)

    # Calculate K = (B ^ a) mod p
    B = int(dh_response, 16)
    a = dh_random
    p = dh_prime
    K = pow(B, a, p)

    # Convert K to bytes with proper padding
    hex_str_K = hex(K)[2:]
    if len(hex_str_K) % 2:
        hex_str_K = "0" + hex_str_K
    hex_bytes_K = bytes.fromhex(hex_str_K)
    if len(bin(K)[2:]) % 8 == 0:
        hex_bytes_K = bytes(1) + hex_bytes_K

    # Compute LST = base64(HMAC-SHA1(K, prepend))
    bytes_hmac_hash_K = hmac.new(
        key=hex_bytes_K,
        msg=prepend_bytes,
        digestmod=sha1,
    ).digest()
    computed_lst = base64.b64encode(bytes_hmac_hash_K).decode("utf-8")

    # Step 12: Validate LST signature
    hex_str_hmac_hash_lst = hmac.new(
        key=base64.b64decode(computed_lst),
        msg=consumer_key.encode("utf-8"),
        digestmod=sha1,
    ).hexdigest()

    if hex_str_hmac_hash_lst != lst_signature:
        raise RuntimeError("LST validation failed: signature mismatch")

    return (computed_lst, lst_expiration)
