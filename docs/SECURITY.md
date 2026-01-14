# Security Setup

This project uses `detect-secrets` to prevent accidental commits of secrets and sensitive information.

## What's Protected

- API keys and tokens
- Passwords and secrets
- RSA private keys
- High-entropy strings that look like secrets
- OAuth credentials (IBKR, Discord, CoolTrader)

## How It Works

1. **Baseline file**: `.secrets.baseline` contains known "safe" secrets (test data, example values)
2. **Pre-commit hook**: Scans changes for new secrets not in the baseline
3. **Exclusions**: `tests/` and `docs/` directories are excluded from scanning

## Protected Secrets

### IBKR OAuth 1.0a
```bash
OAUTH_CONSUMER_KEY=your_consumer_key
OAUTH_ACCESS_TOKEN=your_access_token
OAUTH_ACCESS_TOKEN_SECRET=your_encrypted_access_token_secret
OAUTH_DH_PRIME=your_dh_prime_hex_string
OAUTH_SIGNATURE_KEY_PATH=oauth_keys/private_signature.pem
OAUTH_ENCRYPTION_KEY_PATH=oauth_keys/private_encryption.pem
```

### Notifications
```bash
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

### Historical Data
```bash
COOLTRADER_USERNAME=your_username
COOLTRADER_PASSWORD=your_password
```

## Adding New Secrets

If you need to add a legitimate secret (e.g., new test data):

```bash
# Update baseline with new secrets
uv run detect-secrets scan --baseline .secrets.baseline

# Review and commit the updated baseline
git add .secrets.baseline
git commit -m "Update secrets baseline"
```

## False Positives

For legitimate false positives, use inline allowlisting:

```python
api_key = "fake_key_for_testing"  # pragma: allowlist secret
```

## Testing

To test the secret detection:

```bash
# Create test file with fake secret
echo 'api_key = "sk-1234567890abcdef1234567890abcdef12345678"' > test.py

# Run pre-commit hook (should fail)
uv run pre-commit run detect-secrets --files test.py

# Clean up
rm test.py
```

## File Permissions

Ensure proper permissions on sensitive files:

```bash
# OAuth keys
chmod 600 oauth_keys/*.pem

# Environment file
chmod 600 .env

# Verify permissions
ls -la oauth_keys/
ls -la .env
```

## Security Best Practices

1. Never commit `.env` file or `.pem` keys to version control
2. Use `.env.example` for template only (no real values)
3. Rotate credentials periodically (IBKR OAuth tokens, Discord webhooks)
4. Monitor logs for authentication failures
5. Use HTTPS for all API calls
6. Validate all API responses before processing
7. Restrict production server access (SSH key-based auth)
