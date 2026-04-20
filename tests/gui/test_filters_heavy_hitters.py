"""Tests for heavy-hitter process filtering."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_heavy_hitter_filter_returns_only_heavy_rows():
    rows = [
        {"pid": 1, "classification": "ai agent", "monitored": True, "cpu_percent": 60.0, "ram_mb": 7000.0, "gpu_mb": 600.0},
        {"pid": 2, "classification": "user", "monitored": True, "cpu_percent": 5.0, "ram_mb": 500.0, "gpu_mb": 0.0},
    ]

    filtered = process_utils.filter_process_rows(
        rows,
        rules={"ram_limit_mb": 30000.0, "vram_limit_mb": 14000.0, "cpu_limit_percent": 100.0},
        only_heavy=True,
    )

    assert [row["pid"] for row in filtered] == [1]
