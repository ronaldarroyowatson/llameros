"""Tests that GUI passes classification through display rows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


def test_visible_rows_monitored_mode_uses_monitored_rows():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._rules = {"ram_limit_mb": 30000, "vram_limit_mb": 14000}
    gui._show_all_processes_var = _Var(False)
    gui._only_ai_var = _Var(False)
    gui._only_heavy_var = _Var(False)
    gui._only_monitored_var = _Var(False)

    visible = gui._visible_rows(
        global_rows=[{"pid": 1, "classification": "user", "monitored": False}],
        monitored_rows=[{"pid": 9, "classification": "ai agent", "monitored": True}],
    )

    assert len(visible) == 1
    assert visible[0]["pid"] == 9
    assert visible[0]["classification"] == "ai agent"
