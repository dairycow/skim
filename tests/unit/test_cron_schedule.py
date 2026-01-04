"""Sanity checks for the deployed cron schedule."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def crontab_content():
    path = Path(__file__).parent.parent.parent / "crontab"
    assert path.exists(), "crontab file is missing"
    return path.read_text()


def test_crontab_runs_bot_methods(crontab_content):
    for command in ("scan", "track_ranges", "trade", "manage"):
        assert f"-m skim.core.bot {command}" in crontab_content


def test_crontab_uses_venv_python(crontab_content):
    assert "/opt/skim/.venv/bin/python" in crontab_content
    assert ">> /opt/skim/logs/cron.log" in crontab_content


def test_crontab_includes_scan_gaps_and_scan_news(crontab_content):
    """crontab should include separate gap and news scans at 23:00 UTC."""
    assert (
        "1 23 * * * 0-4 skim cd /opt/skim && /opt/skim/.venv/bin/python -m skim.core.bot scan_gaps"
        in crontab_content
    )
    assert (
        "1 23 * * * 0-4 skim cd /opt/skim && /opt/skim/.venv/bin/python -m skim.core.bot scan_news"
        in crontab_content
    )
