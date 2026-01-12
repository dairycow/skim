"""Global pytest configuration and setup for Skim trading bot tests"""

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


def pytest_configure(config):
    """Configure pytest-timeout to skip integration tests"""
    config.addinivalue_line(
        "markers",
        "timeout: set test timeout in seconds (integration tests have no limit)",
    )


@pytest.fixture
def _disable_timeout_for_integration(request):
    """Disable timeout for integration tests that need real API calls"""
    if "integration" in request.keywords or "manual" in request.keywords:
        request.getfixturevalue("_disallow_timeout")


@pytest.hookimpl
def pytest_collection_modifyitems(config, items):
    """Mark integration tests to not have timeouts"""
    for item in items:
        if item.get_closest_marker("integration") or item.get_closest_marker(
            "manual"
        ):
            item.add_marker(pytest.mark.timeout(300))
