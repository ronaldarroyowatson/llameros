"""Unit placeholder tests for GPU monitor module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import gpu_monitor


def test_gpu_monitor_import_placeholder():
    assert gpu_monitor is not None
    assert True
