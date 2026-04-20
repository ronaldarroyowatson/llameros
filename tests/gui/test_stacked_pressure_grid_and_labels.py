"""Tests for stacked resource pressure chart labels and gridlines."""
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


def test_stacked_pressure_renders_gridlines_axis_labels_and_time_ticks():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._render_interval_ms = 200
    gui._cpu_history = deque([10.0] * 60, maxlen=90)
    gui._ram_history = deque([1024.0] * 60, maxlen=90)
    gui._gpu_history = deque([512.0] * 60, maxlen=90)

    canvas = _Canvas()
    gui._draw_stacked_pressure(canvas, 10, 10, 360, 140)

    texts = [kwargs.get("text") for kind, _, kwargs in canvas.calls if kind == "text"]
    grid_calls = [call for call in canvas.calls if call[0] == "line" and call[2].get("dash")]

    assert "Resource Pressure (%)" in texts
    assert "Time (seconds)" in texts
    assert any(text == "10" for text in texts)
    assert len(grid_calls) >= 4
