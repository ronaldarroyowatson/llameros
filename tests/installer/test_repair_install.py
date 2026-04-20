"""Installer placeholder tests for repair install flow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_repair_install_placeholder():
    assert process_utils is not None
    assert True
