"""Unit placeholder tests for watchdog core module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import watchdog


def test_watchdog_core_import_placeholder():
    assert watchdog is not None
    assert True
