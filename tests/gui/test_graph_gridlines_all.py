"""Tests verifying that all graph panels draw horizontal and vertical gridlines."""
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


def _make_gui() -> LlamerosGUI:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._render_interval_ms = 200
    gui._max_history = 90
    gui._cpu_history = deque([10.0 * i for i in range(10)], maxlen=90)
    gui._ram_history = deque([1000.0 + 100.0 * i for i in range(10)], maxlen=90)
    gui._gpu_history = deque([500.0 + 50.0 * i for i in range(10)], maxlen=90)
    return gui


def _horizontal_lines(canvas: _Canvas, x: float, w: float, y: float, h: float) -> list:
    """Return horizontal line calls within the given panel bounds."""
    results = []
    for kind, args, kwargs in canvas.calls:
        if kind != "line":
            continue
        # A horizontal line has y1 == y2 and spans the panel width
        if len(args) >= 4 and abs(args[1] - args[3]) < 1.0:
            py = args[1]
            if y <= py <= y + h:
                results.append(py)
    return results


def test_draw_line_has_horizontal_gridlines_at_25_50_75():
    """_draw_line must emit horizontal gridlines at 25 / 50 / 75 % height marks."""
    gui = _make_gui()
    canvas = _Canvas()
    x, y, w, h = 8.0, 8.0, 300.0, 120.0
    gui._draw_line(canvas, list(gui._cpu_history), x, y, w, h, 100.0, "#ff6b6b", "CPU Usage (%)")

    h_lines = _horizontal_lines(canvas, x, w, y, h)
    # Must have at least 3 horizontal gridlines (25%, 50%, 75%)
    assert len(h_lines) >= 3, f"Expected ≥3 horizontal gridlines, got {len(h_lines)}"


def test_draw_line_gridlines_correspond_to_25_pct_intervals():
    """Horizontal gridlines must be spaced at every 25 % of panel height."""
    gui = _make_gui()
    canvas = _Canvas()
    x, y, w, h = 0.0, 0.0, 300.0, 100.0
    gui._draw_line(canvas, list(gui._cpu_history), x, y, w, h, 100.0, "#ff6b6b", "CPU Usage (%)")

    h_lines = sorted(_horizontal_lines(canvas, x, w, y, h))
    # Expected positions (top-of-panel = y, bottom = y+h = 100)
    # 25% from bottom → y + h*(1 - 0.25) = 75
    # 50% from bottom → 50
    # 75% from bottom → 25
    expected = [25.0, 50.0, 75.0]
    found = [round(v) for v in h_lines]
    for exp in expected:
        assert exp in found, f"Gridline at {exp} not found; gridlines at: {found}"


def test_draw_line_has_vertical_time_ticks():
    """_draw_line must emit at least one vertical time-tick line for long history."""
    gui = _make_gui()
    # Load 60 samples so there's enough history for a tick every 50 samples
    gui._cpu_history = deque([float(i) for i in range(60)], maxlen=90)
    canvas = _Canvas()
    x, y, w, h = 0.0, 0.0, 300.0, 100.0
    gui._draw_line(canvas, list(gui._cpu_history), x, y, w, h, 100.0, "#ff6b6b", "CPU Usage (%)")

    # A vertical tick line has x1 == x2 (or close) and spans panel height
    vertical_ticks = [
        args for kind, args, _ in canvas.calls
        if kind == "line" and len(args) >= 4 and abs(args[0] - args[2]) < 1.0
        and abs(args[3] - args[1] - h) < 5.0
    ]
    assert len(vertical_ticks) >= 1, "Expected ≥1 vertical time-tick line for 60-sample history"


def test_ram_graph_also_has_horizontal_gridlines():
    """RAM graph (via _draw_line) must also have horizontal gridlines."""
    gui = _make_gui()
    canvas = _Canvas()
    x, y, w, h = 8.0, 8.0, 300.0, 120.0
    gui._draw_line(canvas, list(gui._ram_history), x, y, w, h, 16000.0, "#4dabf7", "RAM Usage (MB)")

    h_lines = _horizontal_lines(canvas, x, w, y, h)
    assert len(h_lines) >= 3, f"RAM graph: expected ≥3 horizontal gridlines, got {len(h_lines)}"


def test_gpu_graph_also_has_horizontal_gridlines():
    """GPU graph (via _draw_line) must also have horizontal gridlines."""
    gui = _make_gui()
    canvas = _Canvas()
    x, y, w, h = 8.0, 8.0, 300.0, 120.0
    gui._draw_line(canvas, list(gui._gpu_history), x, y, w, h, 8000.0, "#51cf66", "VRAM Usage (MB)")

    h_lines = _horizontal_lines(canvas, x, w, y, h)
    assert len(h_lines) >= 3, f"GPU graph: expected ≥3 horizontal gridlines, got {len(h_lines)}"
