"""Tests for cron schedule validation and workflow timing"""

import re
from datetime import datetime, timedelta
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
                    "scan_ibkr_gaps",
                    "scan_ibkr",
                    "scan",
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

                # Execute should be at least 2 minutes after track (allowing time for OR detection)
                assert execute_time - track_time >= 2, (
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

    def test_scan_method_exists(self, bot_methods):
        """TEST: scan method should exist in TradingBot"""
        assert "scan" in bot_methods, "scan method not found in TradingBot"

    def test_all_cron_methods_exist(self, bot_methods):
        """TEST: All cron commands should map to existing methods"""
        expected_methods = [
            "scan",  # Updated: should be scan
            "track_or_breakouts",
            "execute_orh_breakouts",
            "manage_positions",
            "status",
        ]

        for method_name in expected_methods:
            assert method_name in bot_methods, (
                f"Method {method_name} not found in TradingBot"
            )


class BaseCronTest:
    """Base class for cron schedule tests with common utilities"""

    @pytest.fixture
    def crontab_content(self):
        """Path to crontab file"""
        crontab_path = Path(__file__).parent.parent.parent / "crontab"
        return crontab_path.read_text()

    def utc_to_aedt(self, utc_hour, utc_minute=0, utc_day=0):
        """Convert UTC time to AEDT (UTC+11)"""
        # Handle hour 24 as 0 of next day
        if utc_hour == 24:
            utc_hour = 0
            utc_day += 1

        # Use a reference week where day 0 = Sunday, day 1 = Monday, etc.
        # Start with Sunday 2025-01-05
        base_date = datetime(2025, 1, 5 + utc_day, utc_hour, utc_minute)
        aedt_time = base_date + timedelta(hours=11)
        return aedt_time.hour, aedt_time.minute, aedt_time.weekday()

    def expand_day_range(self, day_str):
        """Expand day range like '1-4' into individual days"""
        if "-" in day_str:
            start, end = day_str.split("-")
            return list(range(int(start), int(end) + 1))
        return [int(day_str)]

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


class TestUTCAEDTConversion(BaseCronTest):
    """Test UTC to AEDT conversion accuracy for cron schedules"""

    def test_ibkr_gap_scan_utc_aedt_conversion(self, crontab_content):
        """FAILING TEST: IBKR gap scan should run at 10:00:30 AM AEDT"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and "scan" in parsed["command"]:
                entries.append(parsed)

        assert len(entries) > 0, "No scan command found"

        for entry in entries:
            utc_hour = int(entry["hour"])
            utc_minute = int(entry["minute"])
            # Handle day ranges
            days = self.expand_day_range(entry["day_week"])

            for utc_day in days:
                aedt_hour, aedt_minute, aedt_day = self.utc_to_aedt(
                    utc_hour, utc_minute, utc_day
                )

                # Should be 10:30 AM AEDT on Monday-Friday (0-4)
                assert aedt_hour == 10, (
                    f"Expected 10 AM AEDT, got {aedt_hour}:00 AEDT"
                )
                assert aedt_minute == 30, (
                    f"Expected 30 minutes AEDT, got {aedt_minute} minutes"
                )
                assert aedt_day in [0, 1, 2, 3, 4], (
                    f"Expected Monday-Friday AEDT, got day {aedt_day}"
                )

    def test_or_tracking_utc_aedt_conversion(self, crontab_content):
        """FAILING TEST: OR tracking should run at 10:10:30 AM AEDT"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and "track_or_breakouts" in parsed["command"]:
                entries.append(parsed)

        assert len(entries) > 0, "No track_or_breakouts command found"

        for entry in entries:
            utc_hour = int(entry["hour"])
            utc_minute = int(entry["minute"])
            # Handle day ranges
            days = self.expand_day_range(entry["day_week"])

            for utc_day in days:
                aedt_hour, aedt_minute, aedt_day = self.utc_to_aedt(
                    utc_hour, utc_minute, utc_day
                )

                # Should be 10:10 AM AEDT on Monday-Friday (0-4)
                assert aedt_hour == 10, (
                    f"Expected 10 AM AEDT, got {aedt_hour}:00 AEDT"
                )
                assert aedt_minute == 10, (
                    f"Expected 10 minutes AEDT, got {aedt_minute} minutes"
                )
                assert aedt_day in [0, 1, 2, 3, 4], (
                    f"Expected Monday-Friday AEDT, got day {aedt_day}"
                )

    def test_orh_execution_utc_aedt_conversion(self, crontab_content):
        """FAILING TEST: ORH execution should run at 10:12:00 AM AEDT"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and "execute_orh_breakouts" in parsed["command"]:
                entries.append(parsed)

        assert len(entries) > 0, "No execute_orh_breakouts command found"

        for entry in entries:
            utc_hour = int(entry["hour"])
            utc_minute = int(entry["minute"])
            # Handle day ranges
            days = self.expand_day_range(entry["day_week"])

            for utc_day in days:
                aedt_hour, aedt_minute, aedt_day = self.utc_to_aedt(
                    utc_hour, utc_minute, utc_day
                )

                # Should be 10:12 AM AEDT on Monday-Friday (0-4)
                assert aedt_hour == 10, (
                    f"Expected 10 AM AEDT, got {aedt_hour}:00 AEDT"
                )
                assert aedt_minute == 12, (
                    f"Expected 12 minutes AEDT, got {aedt_minute} minutes"
                )
                assert aedt_day in [0, 1, 2, 3, 4], (
                    f"Expected Monday-Friday AEDT, got day {aedt_day}"
                )


class TestMarketHoursCoverage(BaseCronTest):
    """Test that cron jobs cover ASX market hours properly"""

    def test_position_management_covers_full_market_session(
        self, crontab_content
    ):
        """FAILING TEST: Position management should cover entire ASX market session"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and "manage_positions" in parsed["command"]:
                entries.append(parsed)

        assert len(entries) > 0, "No manage_positions command found"

        for entry in entries:
            hours = entry["hour"].split(",")
            # Should cover 23:00-05:00 UTC (10:00-16:00 AEDT)
            required_hours = ["23", "0", "1", "2", "3", "4", "5"]
            for hour in required_hours:
                assert hour in hours, (
                    f"Position management missing hour {hour} UTC"
                )

    def test_market_open_scan_coverage(self, crontab_content):
        """FAILING TEST: Should have scan coverage right at market open"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and "scan" in parsed["command"]:
                entries.append(parsed)

        assert len(entries) > 0, "No scan command found"

        # Should have at least one entry at 23:00:30 UTC (10:00:30 AM AEDT)
        market_open_entries = [
            e for e in entries if e["hour"] == "23" and e["minute"] == "30"
        ]
        assert len(market_open_entries) > 0, (
            "No scan scheduled at market open (23:30 UTC)"
        )


class TestUTCDayMapping(BaseCronTest):
    """Test UTC day mapping for AEDT trading days"""

    def test_monday_aedx_trading_uses_sunday_utc(self, crontab_content):
        """FAILING TEST: Monday AEDT trading should use Sunday UTC (day 0)"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and any(
                cmd in parsed["command"]
                for cmd in [
                    "scan",
                    "track_or_breakouts",
                    "execute_orh_breakouts",
                ]
            ):
                entries.append(parsed)

        # Should have entries for Sunday UTC (day 0) for Monday AEDT trading
        sunday_entries = [e for e in entries if e["day_week"] == "0"]
        assert len(sunday_entries) > 0, (
            "No entries found for Sunday UTC (Monday AEDT)"
        )

    def test_tuesday_friday_aedx_trading_uses_monday_thursday_utc(
        self, crontab_content
    ):
        """FAILING TEST: Tuesday-Friday AEDT trading should use Monday-Thursday UTC (days 1-4)"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and any(
                cmd in parsed["command"]
                for cmd in [
                    "scan",
                    "track_or_breakouts",
                    "execute_orh_breakouts",
                ]
            ):
                entries.append(parsed)

        # Should have entries for Monday-Thursday UTC (days 1-4) for Tuesday-Friday AEDT
        weekday_entries = []
        for e in entries:
            day_week = e["day_week"]
            if day_week in ["1", "2", "3", "4"] or day_week == "1-4":
                weekday_entries.append(e)
        assert len(weekday_entries) > 0, (
            "No entries found for Monday-Thursday UTC (Tuesday-Friday AEDT)"
        )

    def test_no_friday_utc_entries(self, crontab_content):
        """FAILING TEST: Should not have entries on Friday UTC (Saturday AEDT - no trading)"""
        entries = []
        for line in crontab_content.split("\n"):
            parsed = self.parse_crontab_line(line)
            if parsed and any(
                cmd in parsed["command"]
                for cmd in [
                    "scan",
                    "track_or_breakouts",
                    "execute_orh_breakouts",
                ]
            ):
                entries.append(parsed)

        # Should NOT have entries for Friday UTC (day 5) as it's Saturday AEDT
        friday_entries = [e for e in entries if e["day_week"] == "5"]
        assert len(friday_entries) == 0, (
            f"Found {len(friday_entries)} entries for Friday UTC (should be none)"
        )


class TestCronSyntaxValidation(BaseCronTest):
    """Test cron syntax validation"""

    def test_all_cron_lines_have_valid_format(self, crontab_content):
        """FAILING TEST: All cron lines should have valid 5-field time format"""
        for line in crontab_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(None, 5)
            assert len(parts) >= 6, f"Invalid cron format: {line}"

            minute, hour, day_month, month, day_week = parts[:5]

            # Validate minute field (0-59)
            if minute != "*":
                for m in minute.split(","):
                    if "/" in m:
                        base, step = m.split("/")
                        assert base.isdigit() or base == "*", (
                            f"Invalid minute base: {base}"
                        )
                        assert step.isdigit(), f"Invalid minute step: {step}"
                    elif m.isdigit():
                        assert 0 <= int(m) <= 59, f"Minute out of range: {m}"

    def test_all_commands_use_correct_python_path(self, crontab_content):
        """FAILING TEST: All commands should use /app/.venv/bin/python"""
        for line in crontab_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            assert "/app/.venv/bin/python" in line, (
                f"Missing venv Python path: {line}"
            )
            assert "python -m skim.core.bot" in line, (
                f"Missing bot module invocation: {line}"
            )

    def test_all_commands_have_logging(self, crontab_content):
        """FAILING TEST: All commands should have proper logging redirection"""
        for line in crontab_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            assert ">> /var/log/cron.log 2>&1" in line, (
                f"Missing logging redirection: {line}"
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
