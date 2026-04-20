"""Tests verifying that data collection is scheduled via after() and non-blocking."""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


class _AfterScheduler:
    """Records after() calls without actually scheduling them."""

    def __init__(self):
        self.scheduled: list[tuple[int, object]] = []

    def __call__(self, delay_ms: int, callback):
        self.scheduled.append((delay_ms, callback))


class _MockRoot:
    def __init__(self):
        self._after = _AfterScheduler()

    def after(self, delay_ms: int, callback=None):
        if callback is None:
            return
        self._after(delay_ms, callback)


def _make_gui() -> LlamerosGUI:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._data_refresh_ms = 1000
    gui._render_interval_ms = 200
    gui._max_history = 90
    gui._sort_column = "priority"
    gui._sort_reverse = True
    gui._sort_states = {}
    gui._selected_pid = None
    gui._cpu_history = deque(maxlen=90)
    gui._ram_history = deque(maxlen=90)
    gui._gpu_history = deque(maxlen=90)
    gui._selected_cpu_history = deque(maxlen=90)
    gui._selected_ram_history = deque(maxlen=90)
    gui._selected_gpu_history = deque(maxlen=90)
    gui._last_visible_rows = []
    gui._last_global_rows = []
    gui._last_monitored_rows = []
    gui._last_system_sample = None
    gui._last_selected_sample = None
    root = _MockRoot()
    gui._root = root
    return gui


def test_render_tick_schedules_next_tick_via_after():
    """_schedule_render_tick must use root.after() to avoid blocking the main thread."""
    gui = _make_gui()
    scheduler = gui._root._after

    gui._schedule_render_tick()

    assert len(scheduler.scheduled) >= 1, "render tick must schedule via after()"
    delay_ms, _ = scheduler.scheduled[0]
    assert delay_ms == gui._render_interval_ms, (
        f"Expected render tick delay {gui._render_interval_ms} ms, got {delay_ms} ms"
    )


def test_data_tick_schedules_next_tick_via_after(monkeypatch):
    """_data_tick must re-schedule itself via root.after() for non-blocking refresh."""
    import llameros.process_utils as pu
    import llameros.gui as gui_module
    import psutil

    gui = _make_gui()

    class _MockScheduler:
        def get_process_rows(self):
            return []
        def get_monitored_pids(self):
            return set()
        def get_monitored_names(self):
            return set()
        def get_rules(self):
            return {}

    gui._scheduler = _MockScheduler()
    gui._rules = {}

    monkeypatch.setattr(pu, "get_global_process_rows", lambda **kw: [])
    monkeypatch.setattr(pu, "get_top_cpu_process", lambda: None)
    monkeypatch.setattr(pu, "get_top_ram_process", lambda: None)
    monkeypatch.setattr(pu, "get_top_gpu_process", lambda: None)
    monkeypatch.setattr(pu, "filter_process_rows", lambda rows, **kw: rows)
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 10.0)

    import llameros.system_monitor as sm
    import llameros.gpu_monitor as gm
    monkeypatch.setattr(sm, "get_ram_usage", lambda: 4096.0)
    monkeypatch.setattr(gm, "get_gpu_memory", lambda: 1024.0)

    # Stub out the tree and canvas so _data_tick doesn't crash without a real Tk window
    class _Stub:
        def get_children(self):
            return []
        def delete(self, *a):
            pass
        def insert(self, *a, **kw):
            pass

    gui._tree = _Stub()
    gui._top_cpu_var = type("V", (), {"set": lambda s, v: None})()
    gui._top_ram_var = type("V", (), {"set": lambda s, v: None})()
    gui._top_gpu_var = type("V", (), {"set": lambda s, v: None})()
    gui._triple_hog_var = type("V", (), {"set": lambda s, v: None})()
    gui._show_all_processes_var = type("V", (), {"get": lambda s: True})()
    gui._only_ai_var = type("V", (), {"get": lambda s: False})()
    gui._only_heavy_var = type("V", (), {"get": lambda s: False})()
    gui._only_monitored_var = type("V", (), {"get": lambda s: False})()

    gui._data_tick()

    after_scheduler = gui._root._after
    assert len(after_scheduler.scheduled) >= 1, "_data_tick must reschedule itself via after()"
    delays = [d for d, _ in after_scheduler.scheduled]
    assert gui._data_refresh_ms in delays, (
        f"Expected data_refresh_ms={gui._data_refresh_ms} in after() delays; got {delays}"
    )
