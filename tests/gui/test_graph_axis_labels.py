"""Tests verifying that all graph panels render correct axis labels."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Canvas:
    def __init__(self):
        self.calls: list = []

    def create_rectangle(self, *a, **kw):
        self.calls.append(("rect", a, kw))

    def create_text(self, *a, **kw):
        self.calls.append(("text", a, kw))

    def create_line(self, *a, **kw):
        self.calls.append(("line", a, kw))


def _text_labels(canvas: _Canvas) -> list[str]:
    return [kw.get("text", "") for kind, _, kw in canvas.calls if kind == "text"]


def _make_gui() -> LlamerosGUI:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._render_interval_ms = 200
    gui._max_history = 90
    gui._cpu_history = deque([float(i) for i in range(10)], maxlen=90)
    gui._ram_history = deque([1000.0 + 100.0 * i for i in range(10)], maxlen=90)
    gui._gpu_history = deque([500.0 + 50.0 * i for i in range(10)], maxlen=90)
    return gui


def test_cpu_graph_has_time_seconds_x_axis_label():
    """CPU graph must include an X-axis label reading 'Time (seconds)'."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._cpu_history), 0, 0, 300, 100, 100.0, "#ff6b6b", "CPU Usage (%)")
    labels = _text_labels(canvas)
    assert any("Time (seconds)" in lbl for lbl in labels), (
        f"X-axis label 'Time (seconds)' missing from CPU graph; labels found: {labels}"
    )


def test_ram_graph_has_time_seconds_x_axis_label():
    """RAM graph must include an X-axis label reading 'Time (seconds)'."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._ram_history), 0, 0, 300, 100, 16000.0, "#4dabf7", "RAM Usage (MB)")
    labels = _text_labels(canvas)
    assert any("Time (seconds)" in lbl for lbl in labels), (
        f"X-axis label 'Time (seconds)' missing from RAM graph; labels found: {labels}"
    )


def test_gpu_graph_has_time_seconds_x_axis_label():
    """GPU graph must include an X-axis label reading 'Time (seconds)'."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._gpu_history), 0, 0, 300, 100, 8000.0, "#51cf66", "VRAM Usage (MB)")
    labels = _text_labels(canvas)
    assert any("Time (seconds)" in lbl for lbl in labels), (
        f"X-axis label 'Time (seconds)' missing from GPU graph; labels found: {labels}"
    )


def test_cpu_graph_title_label_is_present():
    """CPU graph must include the y-axis title 'CPU Usage (%)'."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._cpu_history), 0, 0, 300, 100, 100.0, "#ff6b6b", "CPU Usage (%)")
    labels = _text_labels(canvas)
    assert any("CPU Usage (%)" in lbl for lbl in labels)


def test_ram_graph_title_label_is_present():
    """RAM graph must include the y-axis title 'RAM Usage (MB)'."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._ram_history), 0, 0, 300, 100, 16000.0, "#4dabf7", "RAM Usage (MB)")
    labels = _text_labels(canvas)
    assert any("RAM Usage (MB)" in lbl for lbl in labels)


def test_gpu_graph_title_label_is_present():
    """GPU graph must include a VRAM/GPU title label."""
    gui = _make_gui()
    canvas = _Canvas()
    gui._draw_line(canvas, list(gui._gpu_history), 0, 0, 300, 100, 8000.0, "#51cf66", "VRAM Usage (MB)")
    labels = _text_labels(canvas)
    assert any("VRAM Usage (MB)" in lbl or "GPU" in lbl for lbl in labels)
