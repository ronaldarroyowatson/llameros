"""Installer placeholder tests for clean install flow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_rules


def test_clean_install_placeholder():
    assert process_rules is not None
    assert True
