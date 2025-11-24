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


def test_crontab_includes_range_tracking_at_utc_1010(crontab_content):
    """track_ranges must run 10 minutes after the UTC market open (23:10 UTC)."""
    assert (
        "10 23 * * 0 skim cd /opt/skim && /opt/skim/.venv/bin/python -m skim.core.bot track_ranges"
        in crontab_content
    )
    assert (
        "10 23 * * 1-4 skim cd /opt/skim && /opt/skim/.venv/bin/python -m skim.core.bot track_ranges"
        in crontab_content
    )


def test_trade_follows_range_tracking(crontab_content):
    """Ensure execution jobs are scheduled after range tracking to respect ORH sampling."""
    range_index = crontab_content.index("-m skim.core.bot track_ranges")
    trade_index = crontab_content.index("-m skim.core.bot trade")
    assert range_index < trade_index
