"""Smoke placeholder tests for startup path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import main


def test_startup_placeholder():
    assert main is not None
    assert True
