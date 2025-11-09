#!/usr/bin/env python3
"""Test script to verify IBKR gap scanner fix"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skim.scanners.ibkr_gap_scanner import IBKRGapScanner


def test_scanner_params():
    """Test that scanner parameters include required type field"""
    print("Testing scanner parameters...")

    # Create scanner without initializing the client to avoid OAuth requirements
    scanner = IBKRGapScanner.__new__(IBKRGapScanner)
    params = scanner._create_gap_scan_params(min_gap=3.0)

    print(f"Scanner parameters: {params}")

    # Verify required parameters are present
    assert "instrument" in params, "Missing 'instrument' parameter"
    assert "type" in params, "Missing 'type' parameter"
    assert "location" in params, "Missing 'location' parameter"
    assert "filter" in params, "Missing 'filter' parameter"

    # Verify parameter values
    assert params["instrument"] == "STK", (
        f"Expected instrument='STK', got {params['instrument']}"
    )
    assert params["type"] == "TOP_GAINERS", (
        f"Expected type='TOP_GAINERS', got {params['type']}"
    )
    assert params["location"] == "ASX", (
        f"Expected location='ASX', got {params['location']}"
    )

    print("✅ All scanner parameter tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_scanner_params()
        print("\n🎉 Scanner fix verified successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
