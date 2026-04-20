"""Tests for CPU percentage normalization including System Idle Process handling."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


class _ProcRow:
    def __init__(self, pid, name, cpu_percent, rss=1024 * 1024,
                 status="running", username="user", cmdline=None):
        self.info = {
            "pid": pid,
            "name": name,
            "cpu_percent": cpu_percent,
            "memory_info": SimpleNamespace(rss=rss),
            "status": status,
            "username": username,
            "cmdline": cmdline or [name],
        }


def test_normalize_cpu_divides_by_logical_cores():
    """normalize_cpu_percent must divide raw value by logical core count."""
    result = process_utils.normalize_cpu_percent(400.0, cpu_count=4)
    assert result == 100.0


def test_normalize_cpu_caps_at_100_percent():
    """normalize_cpu_percent must never return a value > 100%."""
    result = process_utils.normalize_cpu_percent(9999.0, cpu_count=4)
    assert result == 100.0


def test_normalize_cpu_handles_zero():
    """normalize_cpu_percent must return 0 for zero input."""
    assert process_utils.normalize_cpu_percent(0.0, cpu_count=4) == 0.0


def test_system_idle_process_excluded_from_global_rows(monkeypatch):
    """System Idle Process must not appear as a high-CPU row; it must be capped or skipped."""
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: set())
    monkeypatch.setattr(process_utils.psutil, "cpu_count", lambda logical=True: 4)
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs: [
            _ProcRow(0, "System Idle Process", 2600.0),
            _ProcRow(100, "worker.exe", 200.0),
        ],
    )
    rows = process_utils.get_global_process_rows()
    # System Idle Process must be skipped or have cpu_percent == 0
    for row in rows:
        if "idle" in row["name"].lower():
            assert row["cpu_percent"] == 0.0, (
                f"System Idle Process cpu_percent must be 0, got {row['cpu_percent']}"
            )


def test_global_rows_all_cpu_within_100_percent(monkeypatch):
    """All cpu_percent values in global rows must be at most 100%."""
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: set())
    monkeypatch.setattr(process_utils.psutil, "cpu_count", lambda logical=True: 8)
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs: [
            _ProcRow(10, "python.exe", 800.0),
            _ProcRow(11, "worker.exe", 400.0),
            _ProcRow(12, "idle.exe", 0.0),
        ],
    )
    rows = process_utils.get_global_process_rows()
    for row in rows:
        assert row["cpu_percent"] <= 100.0, (
            f"cpu_percent {row['cpu_percent']} exceeds 100% for {row['name']}"
        )


def test_top_cpu_never_returns_idle_process(monkeypatch):
    """get_top_cpu_process must never return System Idle Process."""
    monkeypatch.setattr(process_utils.psutil, "cpu_count", lambda logical=True: 4)
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs: [
            _ProcRow(0, "System Idle Process", 2400.0),
            _ProcRow(1, "Idle", 2400.0),
            _ProcRow(100, "python.exe", 100.0),
        ],
    )
    top = process_utils.get_top_cpu_process()
    assert top is not None
    assert not process_utils.is_idle_process_name(top["name"]), (
        f"get_top_cpu_process returned idle process: {top}"
    )
