"""Tests for debug logging across key bugfix paths."""
import logging
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import main
from llameros.gui import LlamerosGUI
from llameros.scheduler import MonitoredProcess, TurnTakingScheduler


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _Root:
    def after(self, delay, callback):
        _ = (delay, callback)


class _Canvas:
    def delete(self, arg):
        _ = arg

    def create_rectangle(self, *args, **kwargs):
        _ = (args, kwargs)

    def create_text(self, *args, **kwargs):
        _ = (args, kwargs)

    def create_line(self, *args, **kwargs):
        _ = (args, kwargs)

    def winfo_width(self):
        return 1000


def test_debug_logging_emits_for_cli_filter_and_scheduler(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    monkeypatch.setattr(main, "load_rules", lambda: {"processes": [], "LOG_LEVEL": "DEBUG"})
    fake_scheduler = type("Scheduler", (), {"get_process_rows": lambda self: [], "set_turn_taking_mode": lambda self, enabled: None})()
    monkeypatch.setattr(main, "TurnTakingScheduler", lambda rules: fake_scheduler)

    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._rules = {"LOG_LEVEL": "DEBUG", "ram_limit_mb": 30000.0, "vram_limit_mb": 14000.0}
    gui._show_all_processes_var = _Var(True)
    gui._only_ai_var = _Var(True)
    gui._only_heavy_var = _Var(False)
    gui._only_monitored_var = _Var(False)
    gui._root = _Root()
    gui._system_canvas = _Canvas()
    gui._process_canvas = _Canvas()
    gui._cpu_history = deque([10.0], maxlen=10)
    gui._ram_history = deque([1000.0], maxlen=10)
    gui._gpu_history = deque([500.0], maxlen=10)
    gui._selected_cpu_history = deque(maxlen=10)
    gui._selected_ram_history = deque(maxlen=10)
    gui._selected_gpu_history = deque(maxlen=10)
    gui._selected_pid = None
    gui._last_visible_rows = []
    gui._render_interval_ms = 200

    gui._visible_rows(
        global_rows=[{"pid": 1, "classification": "ai agent", "monitored": True, "cpu_percent": 10.0, "ram_mb": 1000.0, "gpu_mb": 600.0}],
        monitored_rows=[],
    )
    gui._render_tick()

    scheduler = TurnTakingScheduler({"processes": [], "turn_taking_mode": True})
    scheduler._monitored = {1: MonitoredProcess(pid=1, name="python.exe", classification="ai agent", priority=10)}
    monkeypatch.setattr("llameros.scheduler.process_utils.resume_process", lambda pid: True)
    monkeypatch.setattr("llameros.scheduler.process_utils.suspend_process", lambda pid: True)
    scheduler._apply_turn_taking()

    assert main.main(["--debug", "--list-processes"]) == 0

    messages = [record.getMessage() for record in caplog.records]
    assert any("action=filter" in message for message in messages)
    assert any("action=graph-render" in message for message in messages)
    assert any("action=schedule" in message for message in messages)
    assert any("action=cli" in message for message in messages)
