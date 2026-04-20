"""Tests for GUI chart rendering paths."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


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


def test_charts_render_for_selected_process(monkeypatch):
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._system_canvas = _Canvas()
    gui._process_canvas = _Canvas()
    gui._max_history = 10
    gui._cpu_history = deque(maxlen=10)
    gui._ram_history = deque(maxlen=10)
    gui._gpu_history = deque(maxlen=10)
    gui._selected_cpu_history = deque(maxlen=10)
    gui._selected_ram_history = deque(maxlen=10)
    gui._selected_gpu_history = deque(maxlen=10)
    gui._selected_pid = 55

    monkeypatch.setattr("llameros.gui.psutil.cpu_percent", lambda interval=0.0: 20.0)
    monkeypatch.setattr("llameros.gui.get_ram_usage", lambda: 8192.0)
    monkeypatch.setattr("llameros.gui.get_gpu_memory", lambda: 2048.0)

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

    assert len(gui._system_canvas.calls) > 0
    assert len(gui._process_canvas.calls) > 0
    assert len(gui._selected_cpu_history) == 1
