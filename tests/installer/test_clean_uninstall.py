"""Installer placeholder tests for clean uninstall flow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import watchdog


def test_clean_uninstall_placeholder():
    assert watchdog is not None
    assert True
