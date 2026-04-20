"""Tests turn-taking eligibility using process classification."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.scheduler import MonitoredProcess, TurnTakingScheduler


def test_turn_taking_skips_editor_system_and_background(monkeypatch):
    scheduler = TurnTakingScheduler({"processes": [], "turn_taking_mode": True, "turn_quantum_seconds": 2.0})

    scheduler._monitored = {
        1: MonitoredProcess(pid=1, name="python.exe", classification="ai agent", priority=10),
        2: MonitoredProcess(pid=2, name="Code.exe", classification="editor", priority=5),
        3: MonitoredProcess(pid=3, name="VirtualBoxVM.exe", classification="vm", priority=8),
        4: MonitoredProcess(pid=4, name="svchost.exe", classification="system", priority=1),
        5: MonitoredProcess(pid=5, name="service.exe", classification="background", priority=1),
    }

    resumed: list[int] = []
    suspended: list[int] = []
    monkeypatch.setattr("llameros.scheduler.process_utils.resume_process", lambda pid: resumed.append(pid) or True)
    monkeypatch.setattr("llameros.scheduler.process_utils.suspend_process", lambda pid: suspended.append(pid) or True)

    scheduler._apply_turn_taking()

    assert 2 not in resumed
    assert 4 not in resumed
    assert 5 not in resumed
    assert 2 not in suspended
    assert 4 not in suspended
    assert 5 not in suspended
    assert resumed == [3]
    assert suspended == [1]
