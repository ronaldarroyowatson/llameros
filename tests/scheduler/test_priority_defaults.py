"""Tests for scheduler priority defaults by process class."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.scheduler import TurnTakingScheduler


class _FakeIterProc:
    def __init__(self, pid: int, name: str):
        self.info = {"pid": pid, "name": name}


def test_priority_defaults_from_classification(monkeypatch):
    rules = {
        "processes": ["python.exe", "Code.exe", "VirtualBoxVM.exe", "service.exe"],
    }
    scheduler = TurnTakingScheduler(rules)

    monkeypatch.setattr(
        "llameros.scheduler.psutil.process_iter",
        lambda attrs: [
            _FakeIterProc(1001, "python.exe"),
            _FakeIterProc(1002, "Code.exe"),
            _FakeIterProc(1003, "VirtualBoxVM.exe"),
            _FakeIterProc(1004, "service.exe"),
        ],
    )

    by_pid = {
        1001: "ai agent",
        1002: "editor",
        1003: "vm",
        1004: "background",
    }
    monkeypatch.setattr("llameros.scheduler.process_utils.classify_process", lambda pid: by_pid[pid])

    scheduler._sync_processes()

    assert scheduler._monitored[1001].priority == 10
    assert scheduler._monitored[1002].priority == 5
    assert scheduler._monitored[1003].priority == 8
    assert scheduler._monitored[1004].priority == 1
