"""Integration tests for AI-like process detection and control."""
import subprocess
import sys
import time
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils
from llameros.scheduler import MonitoredProcess, TurnTakingScheduler


_SCRIPT = Path(__file__).resolve().parents[1] / "resources" / "dummy_ai_workload.py"


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def test_ai_process_control_round_trip():
    proc = subprocess.Popen([sys.executable, str(_SCRIPT), "--model", "llama-test-agent"])
    try:
        assert _wait_for(lambda: psutil.pid_exists(proc.pid))
        assert process_utils.classify_process(proc.pid) == "ai agent"

        scheduler = TurnTakingScheduler({"processes": [Path(sys.executable).name], "turn_quantum_seconds": 1.0})
        scheduler._monitored[proc.pid] = MonitoredProcess(
            pid=proc.pid,
            name=Path(sys.executable).name,
            classification="ai agent",
            priority=10,
        )

        assert scheduler.pause(proc.pid) is True
        assert _wait_for(lambda: psutil.Process(proc.pid).status() == psutil.STATUS_STOPPED)
        assert scheduler.resume(proc.pid) is True
        assert _wait_for(lambda: psutil.Process(proc.pid).status() != psutil.STATUS_STOPPED)

        scheduler.set_priority(proc.pid, 3)
        assert scheduler._monitored[proc.pid].priority == 3

        scheduler.set_background(proc.pid, enabled=True)
        assert scheduler._monitored[proc.pid].background is True
        scheduler.set_background(proc.pid, enabled=False)
        assert scheduler._monitored[proc.pid].background is False

        assert scheduler.kill(proc.pid) is True
        assert _wait_for(lambda: proc.poll() is not None)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
