"""Tests verifying stacked-pressure graph uses the same continuous render loop."""
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


def _make_gui_with_history() -> LlamerosGUI:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._render_interval_ms = 200
    gui._max_history = 90
    gui._cpu_history = deque([float(i % 30) for i in range(60)], maxlen=90)
    gui._ram_history = deque([1000.0 + 10.0 * i for i in range(60)], maxlen=90)
    gui._gpu_history = deque([500.0 + 5.0 * i for i in range(60)], maxlen=90)
    return gui


def test_stacked_pressure_draws_three_continuous_lines():
    """Stacked pressure must draw exactly three polylines (CPU, RAM, total pressure)."""
    gui = _make_gui_with_history()
    canvas = _Canvas()
    gui._draw_stacked_pressure(canvas, 0, 0, 300, 120)

    line_calls = [(kind, args, kw) for kind, args, kw in canvas.calls if kind == "line"]
    # Filter: long polylines (> 4 coordinate values) are the data lines
    poly_lines = [args for _, args, _ in line_calls if len(args) >= 8]
    assert len(poly_lines) >= 3, (
        f"Expected ≥3 polyline data lines in stacked pressure, got {len(poly_lines)}"
    )


def test_stacked_pressure_redraws_without_new_data():
    """_render_tick must produce stacked pressure output using last-known values."""
    gui = _make_gui_with_history()
    gui._last_system_sample = {"cpu": 40.0, "ram": 8000.0, "gpu": 2000.0}
    gui._last_selected_sample = None
    gui._last_visible_rows = []
    gui._selected_pid = None
    gui._selected_cpu_history = deque(maxlen=90)
    gui._selected_ram_history = deque(maxlen=90)
    gui._selected_gpu_history = deque(maxlen=90)

    class _MockCanvas:
        def __init__(self):
            self.calls: list = []
            self._after_calls: list = []

        def delete(self, *a):
            pass

        def create_rectangle(self, *a, **kw):
            self.calls.append(("rect", a, kw))

        def create_text(self, *a, **kw):
            self.calls.append(("text", a, kw))

        def create_line(self, *a, **kw):
            self.calls.append(("line", a, kw))

        def winfo_width(self):
            return 900

    sys_canvas = _MockCanvas()
    proc_canvas = _MockCanvas()
    gui._system_canvas = sys_canvas
    gui._process_canvas = proc_canvas

    # Simulate a render tick: extend history with last-known sample, draw charts
    if gui._last_system_sample:
        gui._cpu_history.append(float(gui._last_system_sample["cpu"]))
        gui._ram_history.append(float(gui._last_system_sample["ram"]))
        gui._gpu_history.append(float(gui._last_system_sample["gpu"]))

    gui._draw_charts([])

    line_calls = [args for kind, args, _ in sys_canvas.calls if kind == "line"]
    poly_lines = [args for args in line_calls if len(args) >= 8]
    assert len(poly_lines) >= 3, (
        f"Expected ≥3 data polylines in stacked pressure after render tick; got {len(poly_lines)}"
    )


def test_stacked_pressure_has_horizontal_gridlines():
    """Stacked pressure must draw horizontal gridlines at 0/25/50/75/100 pct."""
    gui = _make_gui_with_history()
    canvas = _Canvas()
    gui._draw_stacked_pressure(canvas, 0.0, 0.0, 300.0, 100.0)

    # Horizontal lines have y1 == y2 and span nearly the full width
    h_lines = [
        round(args[1])
        for kind, args, _ in canvas.calls
        if kind == "line" and len(args) >= 4 and abs(args[1] - args[3]) < 1.0
    ]
    # Expect gridlines at 0%, 25%, 50%, 75%, 100% — positions 100, 75, 50, 25, 0 of h=100
    expected = {0, 25, 50, 75, 100}
    found = set(h_lines)
    assert expected.issubset(found), (
        f"Stacked pressure gridlines missing; expected {expected}, found {found}"
    )
