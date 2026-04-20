"""Tests for GUI global process filtering and sorting."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _Tree:
    def __init__(self):
        self._rows = []

    def get_children(self):
        return list(range(len(self._rows)))

    def delete(self, row_id):
        _ = row_id

    def insert(self, parent, index, values):
        _ = parent
        _ = index
        self._rows.append(values)


def test_visible_rows_filters_ai_and_monitored_only():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._rules = {"ram_limit_mb": 30000, "vram_limit_mb": 14000}
    gui._show_all_processes_var = _Var(True)
    gui._only_ai_var = _Var(True)
    gui._only_heavy_var = _Var(False)
    gui._only_monitored_var = _Var(True)

    rows = [
        {"pid": 1, "classification": "ai agent", "monitored": True},
        {"pid": 2, "classification": "ai agent", "monitored": False},
        {"pid": 3, "classification": "user", "monitored": True},
    ]

    visible = gui._visible_rows(global_rows=rows, monitored_rows=[])
    assert [row["pid"] for row in visible] == [1]


def test_refresh_table_includes_classification_column():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._tree = _Tree()
    gui._sort_column = "pid"
    gui._sort_reverse = False

    gui._refresh_table(
        [
            {
                "pid": 10,
                "name": "python.exe",
                "cpu_percent": 4.0,
                "ram_mb": 1200.0,
                "gpu_mb": 900.0,
                "status": "running",
                "priority": 10,
                "classification": "ai agent",
            }
        ]
    )

    assert gui._tree._rows[0][7] == "ai agent"
