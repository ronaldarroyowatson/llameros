"""Unit placeholder tests for process utils module."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_process_utils_import_placeholder():
    assert process_utils is not None
    assert True
