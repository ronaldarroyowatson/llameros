"""Tests for responsive GUI layout behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _Root:
    def __init__(self):
        self.rows = {}
        self.cols = {}

    def rowconfigure(self, idx, weight):
        self.rows[idx] = weight

    def columnconfigure(self, idx, weight):
        self.cols[idx] = weight


class _Widget:
    def __init__(self):
        self.grid_kwargs = None

    def grid(self, **kwargs):
        self.grid_kwargs = kwargs


def test_weighted_grid_is_configured_for_root_layout():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._root = _Root()

    gui._configure_root_grid_weights()

    assert gui._root.rows[2] > 0
    assert gui._root.rows[3] > 0
    assert gui._root.cols[0] > 0


def test_major_sections_use_sticky_nsew_grid():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    table = _Widget()
    charts = _Widget()
    buttons = _Widget()

    gui._grid_major_sections(table_frame=table, charts_frame=charts, button_frame=buttons)

    assert table.grid_kwargs["sticky"] == "nsew"
    assert charts.grid_kwargs["sticky"] == "nsew"
    assert buttons.grid_kwargs["sticky"] == "nsew"


def test_resize_event_triggers_chart_redraw(monkeypatch):
    gui = LlamerosGUI.__new__(LlamerosGUI)
    called = {"count": 0}

    def _mark_redraw(*_args, **_kwargs):
        called["count"] += 1

    monkeypatch.setattr(gui, "_draw_charts", _mark_redraw)
    gui._last_visible_rows = []

    gui._on_resize(event=None)

    assert called["count"] == 1
