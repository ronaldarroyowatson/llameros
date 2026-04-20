"""Live placeholder tests for RAM pressure scenarios."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import system_monitor


def test_live_ram_pressure_placeholder():
    assert system_monitor is not None
    assert True
