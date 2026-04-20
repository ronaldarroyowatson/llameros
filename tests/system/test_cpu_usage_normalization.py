"""Tests for CPU percentage normalization and idle-process handling."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


class _ProcRow:
    def __init__(self, pid, name, cpu_percent, rss=1024 * 1024, status="running", username="user", cmdline=None):
        self.info = {
            "pid": pid,
            "name": name,
            "cpu_percent": cpu_percent,
            "memory_info": SimpleNamespace(rss=rss),
            "status": status,
            "username": username,
            "cmdline": cmdline or [name],
        }


def test_global_rows_normalize_cpu_percent_by_cpu_count(monkeypatch):
    monkeypatch.setattr(process_utils, "_gpu_memory_by_pid", lambda: {})
    monkeypatch.setattr(process_utils, "_visible_window_pids", lambda: set())
    monkeypatch.setattr(process_utils.psutil, "cpu_count", lambda logical=True: 4)
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs: [
            _ProcRow(10, "python.exe", 260.0),
            _ProcRow(11, "worker.exe", 80.0),
        ],
    )

    rows = process_utils.get_global_process_rows()

    assert max(row["cpu_percent"] for row in rows) <= 100.0


def test_top_cpu_process_excludes_system_idle_process(monkeypatch):
    monkeypatch.setattr(
        process_utils.psutil,
        "process_iter",
        lambda attrs: [
            _ProcRow(1, "System Idle Process", 2600.0),
            _ProcRow(2, "python.exe", 55.0),
        ],
    )
    monkeypatch.setattr(process_utils.psutil, "cpu_count", lambda logical=True: 8)

    top = process_utils.get_top_cpu_process()

    assert top is not None
    assert top["name"] == "python.exe"
