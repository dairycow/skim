"""Tests for cron schedule validation and workflow timing"""

import re
from pathlib import Path

import pytest

from skim.core.bot import TradingBot


class TestCronScheduleValidation:
    """Test cron schedule timing and conflicts"""

    @pytest.fixture
    def crontab_path(self):
        """Path to the crontab file"""
        return Path(__file__).parent.parent.parent / "crontab"

    @pytest.fixture
    def crontab_content(self, crontab_path):
        """Read crontab content"""
        return crontab_path.read_text()

    def parse_crontab_line(self, line):
        """Parse a single crontab line into components"""
        # Remove comments and empty lines
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # Split into time part and command part
        parts = line.split(None, 5)
        if len(parts) < 6:
            return None

        return {
            "minute": parts[0],
            "hour": parts[1],
            "day_month": parts[2],
            "month": parts[3],
            "day_week": parts[4],
            "command": parts[5],
            "full_line": line,
        }

    def extract_command_name(self, command):
        """Extract the bot method name from cron command"""
        # Look for pattern like "-m skim.core.bot method_name"
        match = re.search(r"skim\.core\.bot\s+(\w+)", command)
        return match.group(1) if match else None

    def test_crontab_file_exists(self, crontab_path):
        """Test that crontab file exists"""
        assert crontab_path.exists(), (
            f"Crontab file not found at {crontab_path}"
        )

    def test_scan_and_track_not_scheduled_same_time(self, crontab_content):
        """FAILING TEST: scan and track should not be scheduled at same time"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed:
                command_name = self.extract_command_name(parsed["command"])
                if command_name in [
                    "scan_ibkr",
                    "scan_ibkr_gaps",
                    "track_or_breakouts",
                ]:
                    entries.append(
                        {
                            "command": command_name,
                            "minute": parsed["minute"],
                            "hour": parsed["hour"],
                        }
                    )

        # Find scan and track entries
        scan_entries = [e for e in entries if "scan" in e["command"]]
        track_entries = [e for e in entries if "track" in e["command"]]

        assert len(scan_entries) > 0, "No scan command found in crontab"
        assert len(track_entries) > 0, "No track command found in crontab"

        # This should FAIL initially because both are at 30 0
        for scan in scan_entries:
            for track in track_entries:
                assert not (
                    scan["minute"] == track["minute"]
                    and scan["hour"] == track["hour"]
                ), (
                    f"Scan and track scheduled at same time: {scan['minute']} {scan['hour']}"
                )

    def test_execute_runs_after_track(self, crontab_content):
        """FAILING TEST: execute should run 30 minutes after track"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed:
                command_name = self.extract_command_name(parsed["command"])
                if command_name in [
                    "track_or_breakouts",
                    "execute_orh_breakouts",
                ]:
                    entries.append(
                        {
                            "command": command_name,
                            "minute": parsed["minute"],
                            "hour": parsed["hour"],
                        }
                    )

        track_entries = [e for e in entries if "track" in e["command"]]
        execute_entries = [e for e in entries if "execute" in e["command"]]

        assert len(track_entries) > 0, "No track command found"
        assert len(execute_entries) > 0, "No execute command found"

        # This should FAIL initially - execute should be 30 min after track
        for track in track_entries:
            for execute in execute_entries:
                track_time = int(track["hour"]) * 60 + int(track["minute"])
                execute_time = int(execute["hour"]) * 60 + int(
                    execute["minute"]
                )

                # Execute should be at least 25 minutes after track (allowing 5 min buffer)
                assert execute_time - track_time >= 25, (
                    f"Execute should run at least 25 min after track. "
                    f"Track: {track['hour']}:{track['minute']}, "
                    f"Execute: {execute['hour']}:{execute['minute']}"
                )

    def test_status_command_scheduled(self, crontab_content):
        """FAILING TEST: status command should be scheduled daily"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed:
                command_name = self.extract_command_name(parsed["command"])
                if command_name == "status":
                    entries.append(parsed)

        # This should FAIL initially - no status command in crontab
        assert len(entries) > 0, "No status command found in crontab"

        # Check it's scheduled for 05:30 UTC
        status_entry = entries[0]
        assert status_entry["hour"] == "5", (
            f"Status should run at hour 5, got {status_entry['hour']}"
        )
        assert status_entry["minute"] == "30", (
            f"Status should run at minute 30, got {status_entry['minute']}"
        )

    def test_position_management_covers_market_open(self, crontab_content):
        """FAILING TEST: position management should cover 23:00-00:00"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed:
                command_name = self.extract_command_name(parsed["command"])
                if command_name == "manage_positions":
                    entries.append(parsed)

        assert len(entries) > 0, "No manage_positions command found"

        pos_entry = entries[0]
        hours = pos_entry["hour"].split(",")

        # This should FAIL initially - missing hour 23
        assert "23" in hours, (
            "Position management should run at 23:00 for market open coverage"
        )
        assert "0" in hours, (
            "Position management should run at 0:00 for market open coverage"
        )


class TestBotMethodAvailability:
    """Test that all cron commands map to existing bot methods"""

    @pytest.fixture
    def bot_methods(self):
        """Get all callable methods from TradingBot"""
        bot_methods = {}
        for attr_name in dir(TradingBot):
            attr = getattr(TradingBot, attr_name)
            if callable(attr) and not attr_name.startswith("_"):
                bot_methods[attr_name] = attr
        return bot_methods

    def test_scan_ibkr_gaps_method_exists(self, bot_methods):
        """Test that scan_ibkr_gaps method exists"""
        assert "scan_ibkr_gaps" in bot_methods, (
            "scan_ibkr_gaps method not found in TradingBot"
        )

    def test_all_cron_methods_exist(self, bot_methods):
        """TEST: All cron commands should map to existing methods"""
        expected_methods = [
            "scan_ibkr_gaps",  # Fixed: should be scan_ibkr_gaps
            "track_or_breakouts",
            "execute_orh_breakouts",
            "manage_positions",
            "status",
        ]

        for method_name in expected_methods:
            assert method_name in bot_methods, (
                f"Method {method_name} not found in TradingBot"
            )


class TestPythonPathConsistency:
    """Test Python path consistency between cron and Docker setup"""

    @pytest.fixture
    def crontab_content(self):
        """Path to crontab file"""
        crontab_path = Path(__file__).parent.parent.parent / "crontab"
        return crontab_path.read_text()

    def test_crontab_uses_venv_python(self, crontab_content):
        """TEST: Crontab should use virtual environment Python"""
        # This should now PASS - crontab uses /app/.venv/bin/python
        assert "/app/.venv/bin/python" in crontab_content, (
            "Crontab should use /app/.venv/bin/python for virtual environment"
        )
        assert "/usr/local/bin/python" not in crontab_content, (
            "Crontab should not use system Python at /usr/local/bin/python"
        )

    def test_dockerfile_sets_venv_path(self):
        """Test that Dockerfile sets up virtual environment path"""
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"
        dockerfile_content = dockerfile_path.read_text()

        assert "/app/.venv/bin" in dockerfile_content, (
            "Dockerfile should include /app/.venv/bin in PATH"
        )
        assert "uv sync" in dockerfile_content, (
            "Dockerfile should run uv sync to create virtual environment"
        )
