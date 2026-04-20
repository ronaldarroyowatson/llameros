"""Tests specific to AI-agent scheduling defaults."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.scheduler import MonitoredProcess, TurnTakingScheduler


def test_ai_agent_default_priority_is_highest():
    scheduler = TurnTakingScheduler({"processes": ["python.exe"]})
    proc = MonitoredProcess(pid=42, name="python.exe", classification="ai agent", priority=10)

    assert scheduler._priority_defaults["ai agent"] == 10
    assert proc.priority == 10
