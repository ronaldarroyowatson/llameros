"""Tests for AI-agent process filtering."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_ai_agent_filter_returns_only_ai_rows():
    rows = [
        {"pid": 1, "classification": "ai agent", "monitored": True, "cpu_percent": 10.0, "ram_mb": 1024.0, "gpu_mb": 600.0},
        {"pid": 2, "classification": "user", "monitored": True, "cpu_percent": 10.0, "ram_mb": 1024.0, "gpu_mb": 0.0},
    ]

    filtered = process_utils.filter_process_rows(rows, rules={}, only_ai=True)

    assert [row["pid"] for row in filtered] == [1]
