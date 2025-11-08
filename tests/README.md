# Skim Trading Bot - Test Suite

This directory contains the test suite for the Skim trading bot.

## Complete Testing Guide

For comprehensive testing documentation, including:
- Test structure and categories
- Running tests and coverage
- Writing new tests
- Mocking strategies
- CI/CD integration

**See the main testing guide: [docs/TESTING.md](../docs/TESTING.md)**

## Quick Test Commands

```bash
# Run all tests (unit + integration)
pytest

# Run only unit tests
pytest tests/unit/ -v

# Run with coverage
pytest --cov=src/skim --cov-report=html
```

## Test Structure

```
tests/
├── conftest.py                  # Shared pytest fixtures and environment setup
├── fixtures/                    # Test data and mock responses
├── unit/                        # Fast, isolated unit tests
├── integration/                 # Integration tests with real services
│   ├── oauth/                   # OAuth authentication tests
│   ├── client/                  # Client operation tests
│   └── workflow/                # End-to-end workflow tests
└── docs/                        # Test documentation and results
```

See [docs/TESTING.md](../docs/TESTING.md) for detailed information.