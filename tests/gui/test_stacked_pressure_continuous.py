"""Tests for stacked resource pressure continuity rendering."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Canvas:
    def __init__(self):
        self.calls = []

    def create_rectangle(self, *args, **kwargs):
        self.calls.append(("rect", args, kwargs))

    def create_text(self, *args, **kwargs):
        self.calls.append(("text", args, kwargs))

    def create_line(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))


def test_stacked_pressure_uses_continuous_lines_without_gaps():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._render_interval_ms = 200
    gui._cpu_history = deque([10.0, 20.0, 30.0, 40.0], maxlen=10)
    gui._ram_history = deque([1000.0, 1000.0, 1200.0, 1400.0], maxlen=10)
    gui._gpu_history = deque([500.0, 700.0, 700.0, 900.0], maxlen=10)

    canvas = _Canvas()
    gui._draw_stacked_pressure(canvas, 10, 10, 320, 120)

    line_calls = [call for call in canvas.calls if call[0] == "line"]

    assert line_calls
    assert any(len(args) > 4 for _, args, _ in line_calls)
