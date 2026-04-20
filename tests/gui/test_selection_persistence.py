"""Tests for selection persistence when clicking outside the table."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Tree:
    """Minimal Treeview mock with controllable selection."""

    def __init__(self):
        self._selection: list[str] = []
        self._items: dict[str, tuple] = {}
        self._inserted: list[tuple] = []

    def selection(self) -> list[str]:
        return list(self._selection)

    def item(self, row_id: str, option: str) -> tuple:
        assert option == "values"
        return self._items.get(row_id, ())

    def selection_remove(self, *items):
        for it in items:
            if it in self._selection:
                self._selection.remove(it)

    def selection_set(self, row_id: str):
        self._selection = [row_id]

    def get_children(self):
        return list(self._items.keys())

    def delete(self, row_id: str):
        self._items.pop(row_id, None)
        if row_id in self._selection:
            self._selection.remove(row_id)

    def insert(self, parent, position, values=()):
        row_id = f"row-{len(self._inserted)}"
        self._inserted.append((parent, position, values))
        self._items[row_id] = values
        return row_id


class _Canvas:
    def __init__(self):
        self.calls: list = []

    def delete(self, *a):
        pass

    def create_rectangle(self, *a, **kw):
        self.calls.append(("rect", a, kw))

    def create_text(self, *a, **kw):
        self.calls.append(("text", a, kw))

    def create_line(self, *a, **kw):
        self.calls.append(("line", a, kw))

    def winfo_width(self):
        return 1000


def _make_gui(selected_pid: int | None = None) -> LlamerosGUI:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._selected_pid = selected_pid
    gui._last_global_rows = []
    gui._last_visible_rows = []
    gui._max_history = 90
    gui._cpu_history = deque([10.0], maxlen=90)
    gui._ram_history = deque([1000.0], maxlen=90)
    gui._gpu_history = deque([500.0], maxlen=90)
    gui._selected_cpu_history = deque(maxlen=90)
    gui._selected_ram_history = deque(maxlen=90)
    gui._selected_gpu_history = deque(maxlen=90)
    gui._last_system_sample = None
    gui._last_selected_sample = None
    gui._render_interval_ms = 200
    gui._tree = _Tree()
    gui._system_canvas = _Canvas()
    gui._process_canvas = _Canvas()
    return gui


def test_empty_treeview_selection_event_does_not_clear_selected_pid():
    """_on_row_selected with empty selection must NOT clear _selected_pid."""
    gui = _make_gui(selected_pid=42)
    # Simulate Tkinter clicking empty space: selection() returns []
    gui._tree._selection = []
    event = type("Event", (), {})()
    gui._on_row_selected(event)
    assert gui._selected_pid == 42, (
        "Clicking empty table area must not clear _selected_pid"
    )


def test_refresh_table_restores_visual_selection_after_full_redraw():
    """_refresh_table must restore the selected row highlight after deleting/reinserting rows."""
    gui = _make_gui(selected_pid=55)
    gui._sort_column = "pid"
    gui._sort_reverse = False
    gui._sort_states = {}

    rows = [
        {
            "pid": 55,
            "name": "python.exe",
            "cpu_percent": 20.0,
            "ram_mb": 1024.0,
            "gpu_mb": 300.0,
            "status": "running",
            "priority": 5,
            "classification": "ai agent",
        },
        {
            "pid": 56,
            "name": "worker.exe",
            "cpu_percent": 5.0,
            "ram_mb": 256.0,
            "gpu_mb": 0.0,
            "status": "running",
            "priority": 3,
            "classification": "user",
        },
    ]
    gui._refresh_table(rows)

    # After redraw the tree must have a visual selection on PID 55
    assert len(gui._tree.selection()) == 1, (
        "_refresh_table must restore selection for _selected_pid=55"
    )
    selected_id = gui._tree.selection()[0]
    values = gui._tree.item(selected_id, "values")
    assert int(values[0]) == 55, (
        f"Selected row must be PID 55, got {values[0]}"
    )


def test_selection_clears_only_via_clear_selection_button():
    """_selected_pid must only be cleared when _clear_selection() is called explicitly."""
    gui = _make_gui(selected_pid=77)
    # Multiple empty-selection events must NOT clear the pid
    for _ in range(5):
        gui._tree._selection = []
        event = type("Event", (), {})()
        gui._on_row_selected(event)
    assert gui._selected_pid == 77

    # Explicit clear must clear it
    gui._clear_selection()
    assert gui._selected_pid is None
