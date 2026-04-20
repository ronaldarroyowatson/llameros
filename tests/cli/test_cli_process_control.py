"""Tests for CLI process-control parity with GUI actions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import main


class _FakeScheduler:
    def __init__(self):
        self.calls = []

    def get_process_rows(self):
        return [{"pid": 42, "name": "python.exe", "classification": "ai agent"}]

    def pause(self, pid):
        self.calls.append(("pause", pid))
        return True

    def resume(self, pid):
        self.calls.append(("resume", pid))
        return True

    def kill(self, pid):
        self.calls.append(("kill", pid))
        return True

    def set_priority(self, pid, level):
        self.calls.append(("set_priority", pid, level))

    def set_background(self, pid, enabled=True):
        self.calls.append(("set_background", pid, enabled))

    def set_turn_taking_mode(self, enabled):
        self.calls.append(("turn_taking", enabled))


def test_cli_routes_process_commands_to_shared_scheduler(monkeypatch, capsys):
    fake_scheduler = _FakeScheduler()
    monkeypatch.setattr(main, "load_rules", lambda: {"processes": []})
    monkeypatch.setattr(main, "TurnTakingScheduler", lambda rules: fake_scheduler)

    assert main.main(["--list-processes"]) == 0
    output = capsys.readouterr().out
    assert '"pid": 42' in output

    assert main.main(["--pause", "99"]) == 0
    assert main.main(["--resume", "99"]) == 0
    assert main.main(["--kill", "99"]) == 0
    assert main.main(["--set-priority", "99", "7"]) == 0
    assert main.main(["--set-background", "99"]) == 0
    assert main.main(["--bring-foreground", "99"]) == 0
    assert main.main(["--enable-turn-taking"]) == 0
    assert main.main(["--disable-turn-taking"]) == 0

    assert fake_scheduler.calls == [
        ("pause", 99),
        ("resume", 99),
        ("kill", 99),
        ("set_priority", 99, 7),
        ("set_background", 99, True),
        ("set_background", 99, False),
        ("turn_taking", True),
        ("turn_taking", False),
    ]
