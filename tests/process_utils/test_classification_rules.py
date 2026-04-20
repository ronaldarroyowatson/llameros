"""Tests for process classification rules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


class _FakeProc:
    def __init__(self, pid: int, name: str, cmdline: list[str], cpu: float, username: str = "user"):
        self._pid = pid
        self._name = name
        self._cmdline = cmdline
        self._cpu = cpu
        self._username = username

    def oneshot(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def name(self):
        return self._name

    def username(self):
        return self._username

    def cmdline(self):
        return self._cmdline

    def cpu_percent(self, interval=0.0):
        _ = interval
        return self._cpu


def test_classify_editor_vm_system_user_background(monkeypatch):
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: set())

    cases = {
        101: _FakeProc(101, "svchost.exe", [], 0.1, "NT AUTHORITY\\SYSTEM"),
        501: _FakeProc(501, "Code.exe", [], 2.0),
        601: _FakeProc(601, "VirtualBoxVM.exe", [], 5.0),
        701: _FakeProc(701, "calc.exe", [], 0.1),
        801: _FakeProc(801, "notepad.exe", [], 3.0),
    }

    monkeypatch.setattr(process_utils.psutil, "Process", lambda pid: cases[pid])

    assert process_utils.classify_process(101) == "system"
    assert process_utils.classify_process(501) == "editor"
    assert process_utils.classify_process(601) == "vm"
    assert process_utils.classify_process(701) == "background"
    assert process_utils.classify_process(801) == "user"


def test_classify_ai_agent_by_python_llm_hint(monkeypatch):
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: {900})
    monkeypatch.setattr(
        process_utils.psutil,
        "Process",
        lambda pid: _FakeProc(pid, "python.exe", ["python", "serve.py", "--model", "llama3"], 12.0),
    )

    assert process_utils.classify_process(900) == "ai agent"
