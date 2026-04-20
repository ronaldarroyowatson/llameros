"""Tests for continuous graph rendering behavior."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Root:
    def __init__(self):
        self.after_calls = []

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))


class _Canvas:
    def __init__(self):
        self.calls = []

    def delete(self, arg):
        self.calls.append(("delete", arg))

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rect", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))

    def winfo_width(self):
        return 1000


def _base_gui():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._root = _Root()
    gui._system_canvas = _Canvas()
    gui._process_canvas = _Canvas()
    gui._max_history = 10
    gui._cpu_history = deque([10.0], maxlen=10)
    gui._ram_history = deque([1000.0], maxlen=10)
    gui._gpu_history = deque([500.0], maxlen=10)
    gui._selected_cpu_history = deque(maxlen=10)
    gui._selected_ram_history = deque(maxlen=10)
    gui._selected_gpu_history = deque(maxlen=10)
    gui._selected_pid = None
    gui._last_visible_rows = []
    return gui


def test_graph_render_interval_is_fixed_200ms():
    gui = _base_gui()

    gui._schedule_render_tick()

    assert gui._root.after_calls
    assert gui._root.after_calls[-1][0] == 200


def test_render_tick_redraws_even_without_new_data():
    gui = _base_gui()

    before = len(gui._system_canvas.calls)
    gui._render_tick()
    first = len(gui._system_canvas.calls)
    gui._render_tick()
    second = len(gui._system_canvas.calls)

    assert first > before
    assert second > first


def test_render_tick_extends_last_known_values_to_avoid_gaps():
    gui = _base_gui()

    gui._render_tick()
    first_cpu = gui._cpu_history[-1]
    gui._render_tick()
    second_cpu = gui._cpu_history[-1]

    assert len(gui._cpu_history) >= 3
    assert first_cpu == second_cpu
