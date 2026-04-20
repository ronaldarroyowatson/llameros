"""Unit placeholder tests for system monitor module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import system_monitor


def test_system_monitor_import_placeholder():
    assert system_monitor is not None
    assert True
