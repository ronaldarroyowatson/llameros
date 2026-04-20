"""Tests for sort performance: sorting must complete within 200 ms for 1000 rows."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


def _make_gui_with_rows(n: int = 1000) -> tuple[LlamerosGUI, list[dict]]:
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._sort_column = "cpu_percent"
    gui._sort_reverse = True
    gui._sort_states = {}

    rows = [
        {
            "pid": i,
            "name": f"proc_{i}.exe",
            "cpu_percent": float(i % 100),
            "ram_mb": float(i * 10 % 32768),
            "gpu_mb": float(i * 5 % 8192),
            "status": "running",
            "priority": i % 10 + 1,
            "classification": "user",
        }
        for i in range(n)
    ]
    return gui, rows


def test_sort_1000_rows_completes_within_200ms():
    """_sorted_rows must complete within 200 ms for 1000 process rows."""
    gui, rows = _make_gui_with_rows(1000)
    start = time.perf_counter()
    sorted_rows = gui._sorted_rows(rows)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert len(sorted_rows) == 1000
    assert elapsed_ms < 200.0, f"Sort took {elapsed_ms:.1f} ms, expected < 200 ms"


def test_sort_by_name_1000_rows_within_200ms():
    """Sorting by name (string key) must also complete within 200 ms."""
    gui, rows = _make_gui_with_rows(1000)
    gui._sort_column = "name"
    gui._sort_reverse = False
    start = time.perf_counter()
    sorted_rows = gui._sorted_rows(rows)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert len(sorted_rows) == 1000
    assert elapsed_ms < 200.0, f"Name sort took {elapsed_ms:.1f} ms, expected < 200 ms"


def test_sort_order_is_descending_for_numeric_column():
    """Sorting cpu_percent descending must place highest value first."""
    gui, rows = _make_gui_with_rows(100)
    gui._sort_column = "cpu_percent"
    gui._sort_reverse = True
    sorted_rows = gui._sorted_rows(rows)
    values = [r["cpu_percent"] for r in sorted_rows]
    assert values == sorted(values, reverse=True)
