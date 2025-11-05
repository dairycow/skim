# Test RSA Keys

These are **test-only** RSA keys used for unit and integration testing. They are **NOT** production keys and contain no sensitive information.

## Purpose

- Used by unit tests to mock OAuth 1.0a signature and encryption operations
- Allows tests to run without requiring real IBKR credentials
- Safe to commit to version control

## Files

- `test_signature_key.pem`: Test private key for RSA-SHA256 OAuth signatures
- `test_encryption_key.pem`: Test private key for decrypting access token secrets

## Security Note

**These keys are for testing only and should never be used in production.**

Real production keys should:
- Be generated via IBKR portal
- Never be committed to version control
- Be stored in `.gitignore`d directories (`oauth_keys/`)
- Be managed as secrets in deployment environments
