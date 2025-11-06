"""Unit tests for IBKR OAuth 1.0a implementation

Tests the OAuth LST (Live Session Token) generation without requiring
real IBKR API access or production credentials.
"""

import pytest
import responses
from freezegun import freeze_time

from skim.brokers.ibkr_oauth import generate_lst


@pytest.mark.unit
class TestGenerateLST:
    """Tests for generate_lst() function"""

    @responses.activate
    @freeze_time("2025-11-06 12:00:00")
    def test_generate_lst_success(
        self, test_rsa_keys, mock_lst_response, mocker
    ):
        """Test successful LST generation with mocked HTTP response"""
        sig_path, enc_path = test_rsa_keys

        # Mock HTTP response from IBKR
        responses.post(
            "https://api.ibkr.com/v1/api/oauth/live_session_token",
            json=mock_lst_response,
            status=200,
        )

        # Mock random for deterministic DH challenge
        mocker.patch("random.getrandbits", return_value=12345678)

        # Mock base64 decode
        mocker.patch("skim.brokers.ibkr_oauth.base64.b64decode", return_value=b"test_ciphertext")

        # Mock the decrypt to return test bytes
        mock_cipher = mocker.MagicMock()
        mock_cipher.decrypt.return_value = b"test_prepend_value"
        mocker.patch("skim.brokers.ibkr_oauth.PKCS1_v1_5_Cipher.new", return_value=mock_cipher)

        # Mock HMAC for LST computation and validation
        def mock_hmac_new(*args, **kwargs):
            mock = mocker.MagicMock()
            mock.digest.return_value = b"test_hmac_digest"
            mock.hexdigest.return_value = mock_lst_response["live_session_token_signature"]
            return mock
        mocker.patch("skim.brokers.ibkr_oauth.hmac.new", side_effect=mock_hmac_new)

        # Call function with test credentials
        lst, expiration = generate_lst(
            consumer_key="TEST_CONSUMER",
            access_token="test_token",
            access_token_secret="dGVzdA==",
            dh_prime_hex="00f4c0ac1c6a120cffe7c0438769be9f35a721",
            signature_key_path=sig_path,
            encryption_key_path=enc_path,
        )

        # Verify return values
        assert isinstance(lst, str)
        assert len(lst) > 0
        assert expiration == mock_lst_response["live_session_token_expiration"]
        assert len(responses.calls) == 1

        # Verify request headers contain OAuth authorization
        request = responses.calls[0].request
        assert "authorization" in request.headers
        auth_header = request.headers["authorization"]
        assert "OAuth" in auth_header
        assert "oauth_consumer_key" in auth_header
        assert 'oauth_signature_method="RSA-SHA256"' in auth_header

    def test_generate_lst_missing_signature_key_file(self, test_rsa_keys):
        """Test LST generation with missing signature key file"""
        _, enc_path = test_rsa_keys

        with pytest.raises(FileNotFoundError):
            generate_lst(
                consumer_key="TEST",
                access_token="test",
                access_token_secret="secret",
                dh_prime_hex="00f4c0ac1c6a120c",
                signature_key_path="/nonexistent/signature_key.pem",
                encryption_key_path=enc_path,
            )

    def test_generate_lst_missing_encryption_key_file(self, test_rsa_keys):
        """Test LST generation with missing encryption key file"""
        sig_path, _ = test_rsa_keys

        with pytest.raises(FileNotFoundError):
            generate_lst(
                consumer_key="TEST",
                access_token="test",
                access_token_secret="secret",
                dh_prime_hex="00f4c0ac1c6a120c",
                signature_key_path=sig_path,
                encryption_key_path="/nonexistent/encryption_key.pem",
            )

    def test_generate_lst_invalid_dh_prime_format(self, test_rsa_keys):
        """Test LST generation with invalid DH prime format"""
        sig_path, enc_path = test_rsa_keys

        with pytest.raises(ValueError):
            generate_lst(
                consumer_key="TEST",
                access_token="test",
                access_token_secret="secret",
                dh_prime_hex="not_a_hex_string!@#",
                signature_key_path=sig_path,
                encryption_key_path=enc_path,
            )

    @responses.activate
    def test_generate_lst_network_timeout(self, test_rsa_keys, mocker):
        """Test LST generation handles network timeout"""
        sig_path, enc_path = test_rsa_keys

        # Mock base64 decode
        mocker.patch("skim.brokers.ibkr_oauth.base64.b64decode", return_value=b"test_ciphertext")

        # Mock the decrypt to return test bytes
        mock_cipher = mocker.MagicMock()
        mock_cipher.decrypt.return_value = b"test_prepend_value"
        mocker.patch("skim.brokers.ibkr_oauth.PKCS1_v1_5_Cipher.new", return_value=mock_cipher)

        # Mock requests.post to raise timeout exception
        import requests
        mocker.patch(
            "requests.post",
            side_effect=requests.exceptions.Timeout("Connection timeout")
        )

        with pytest.raises(requests.exceptions.Timeout):
            generate_lst(
                consumer_key="TEST",
                access_token="test",
                access_token_secret="dGVzdA==",
                dh_prime_hex="00f4c0ac1c6a120c",
                signature_key_path=sig_path,
                encryption_key_path=enc_path,
            )

    @responses.activate
    @freeze_time("2025-11-06 12:00:00")
    def test_generate_lst_deterministic_with_seeded_random(
        self, test_rsa_keys, mock_lst_response, mocker
    ):
        """Test that LST generation is deterministic when random is seeded"""
        sig_path, enc_path = test_rsa_keys

        # Mock base64 decode
        mocker.patch("skim.brokers.ibkr_oauth.base64.b64decode", return_value=b"test_ciphertext")

        # Mock the decrypt to return test bytes
        mock_cipher = mocker.MagicMock()
        mock_cipher.decrypt.return_value = b"test_prepend_value"
        mocker.patch("skim.brokers.ibkr_oauth.PKCS1_v1_5_Cipher.new", return_value=mock_cipher)

        responses.post(
            "https://api.ibkr.com/v1/api/oauth/live_session_token",
            json=mock_lst_response,
            status=200,
        )

        # Seed random for deterministic behavior
        mocker.patch("random.getrandbits", return_value=42)

        # Generate LST twice with same parameters
        lst1, exp1 = generate_lst(
            consumer_key="TEST",
            access_token="test",
            access_token_secret="dGVzdA==",
            dh_prime_hex="00f4c0ac1c6a120c",
            signature_key_path=sig_path,
            encryption_key_path=enc_path,
        )

        # Reset responses for second call
        responses.reset()
        responses.post(
            "https://api.ibkr.com/v1/api/oauth/live_session_token",
            json=mock_lst_response,
            status=200,
        )

        lst2, exp2 = generate_lst(
            consumer_key="TEST",
            access_token="test",
            access_token_secret="dGVzdA==",
            dh_prime_hex="00f4c0ac1c6a120c",
            signature_key_path=sig_path,
            encryption_key_path=enc_path,
        )

        # With seeded random, results should be identical
        assert lst1 == lst2
        assert exp1 == exp2
