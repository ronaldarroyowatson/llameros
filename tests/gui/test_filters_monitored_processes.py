"""Tests for monitored-process filtering."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_monitored_filter_returns_only_monitored_rows():
    rows = [
        {"pid": 1, "classification": "ai agent", "monitored": True, "cpu_percent": 10.0, "ram_mb": 1024.0, "gpu_mb": 600.0},
        {"pid": 2, "classification": "user", "monitored": False, "cpu_percent": 10.0, "ram_mb": 1024.0, "gpu_mb": 0.0},
    ]

    filtered = process_utils.filter_process_rows(rows, rules={}, only_monitored=True)

    assert [row["pid"] for row in filtered] == [1]
