"""Tests for AI-agent helper predicates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


class _FakeProc:
    def __init__(self, pid: int):
        self._pid = pid

    def oneshot(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def name(self):
        return "worker.exe"

    def username(self):
        return "user"

    def cmdline(self):
        return ["worker.exe"]

    def cpu_percent(self, interval=0.0):
        _ = interval
        return 2.0


def test_is_ai_agent_true_when_gpu_memory_high(monkeypatch):
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {321: 700.0})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: {321})
    monkeypatch.setattr(process_utils.psutil, "Process", lambda pid: _FakeProc(pid))

    assert process_utils.is_ai_agent(321) is True
    assert process_utils.is_editor(321) is False
    assert process_utils.is_vm(321) is False
    assert process_utils.is_system(321) is False
