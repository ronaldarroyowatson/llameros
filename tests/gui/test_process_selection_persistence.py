"""Tests for persistent process selection behavior."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Tree:
    def __init__(self, selection_values=None, item_values=None):
        self._selection_values = selection_values or []
        self._item_values = item_values or {}

    def selection(self):
        return list(self._selection_values)

    def item(self, row_id, option):
        assert option == "values"
        return self._item_values[row_id]

    def selection_remove(self, *items):
        _ = items
        self._selection_values = []


class _Canvas:
    def __init__(self):
        self.calls = []

    def delete(self, arg):
        self.calls.append(("delete", (arg,), {}))

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rect", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))

    def winfo_width(self):
        return 1000


def test_selection_persists_when_clicking_outside_table():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._selected_pid = 77
    gui._tree = _Tree(selection_values=[])

    gui._on_row_selected(event=None)

    assert gui._selected_pid == 77


def test_clear_selection_resets_selected_graph_state():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._tree = _Tree(selection_values=["row-1"], item_values={"row-1": (55, "python.exe")})
    gui._system_canvas = _Canvas()
    gui._process_canvas = _Canvas()
    gui._max_history = 10
    gui._cpu_history = deque([10.0], maxlen=10)
    gui._ram_history = deque([1000.0], maxlen=10)
    gui._gpu_history = deque([500.0], maxlen=10)
    gui._selected_cpu_history = deque([25.0], maxlen=10)
    gui._selected_ram_history = deque([2000.0], maxlen=10)
    gui._selected_gpu_history = deque([1200.0], maxlen=10)
    gui._selected_pid = 55
    gui._last_visible_rows = []

    gui._clear_selection()
    gui._draw_charts(
        [
            {
                "pid": 55,
                "name": "python.exe",
                "classification": "ai agent",
                "cpu_percent": 25.0,
                "ram_mb": 2000.0,
                "gpu_mb": 1200.0,
            }
        ]
    )

    texts = [kwargs.get("text") for kind, _, kwargs in gui._process_canvas.calls if kind == "text"]

    assert gui._selected_pid is None
    assert len(gui._selected_cpu_history) == 0
    assert any("select a process row" in text for text in texts if text)
