# Security Setup

This project uses `detect-secrets` to prevent accidental commits of secrets and sensitive information.

## How it works

1. **Baseline file**: `.secrets.baseline` contains known "safe" secrets (mostly test data)
2. **Pre-commit hook**: Scans changes for new secrets not in the baseline
3. **Exclusions**: Test files and documentation are excluded from scanning

## What's protected

- API keys and tokens
- Passwords and secrets
- RSA private keys
- High-entropy strings that look like secrets
- OAuth credentials

## Adding new secrets

If you need to add a legitimate secret (e.g., new test data):

```bash
# Update baseline with new secrets
uv run detect-secrets scan --baseline .secrets.baseline

# Review and commit the updated baseline
git add .secrets.baseline
git commit -m "Update secrets baseline"
```

## False positives

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