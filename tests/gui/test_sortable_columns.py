"""Tests for sortable GUI table columns."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros.gui import LlamerosGUI


def _rows():
    return [
        {
            "pid": 200,
            "name": "zeta.exe",
            "cpu_percent": 40.0,
            "ram_mb": 1800.0,
            "gpu_mb": 400.0,
            "status": "running",
            "priority": 4,
            "classification": "user",
        },
        {
            "pid": 100,
            "name": "alpha.exe",
            "cpu_percent": 5.0,
            "ram_mb": 900.0,
            "gpu_mb": 1200.0,
            "status": "sleeping",
            "priority": 10,
            "classification": "ai agent",
        },
        {
            "pid": 150,
            "name": "beta.exe",
            "cpu_percent": 22.0,
            "ram_mb": 1100.0,
            "gpu_mb": 50.0,
            "status": "stopped",
            "priority": 2,
            "classification": "background service",
        },
    ]


def test_clicking_numeric_column_toggles_ascending_descending():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._sort_states = {}

    gui._on_heading_click("pid")
    asc = [row["pid"] for row in gui._sorted_rows(_rows())]
    gui._on_heading_click("pid")
    desc = [row["pid"] for row in gui._sorted_rows(_rows())]

    assert asc == [100, 150, 200]
    assert desc == [200, 150, 100]


def test_clicking_string_column_toggles_ascending_descending():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._sort_states = {}

    gui._on_heading_click("name")
    asc = [row["name"] for row in gui._sorted_rows(_rows())]
    gui._on_heading_click("name")
    desc = [row["name"] for row in gui._sorted_rows(_rows())]

    assert asc == ["alpha.exe", "beta.exe", "zeta.exe"]
    assert desc == ["zeta.exe", "beta.exe", "alpha.exe"]


def test_each_heading_is_sortable():
    gui = LlamerosGUI.__new__(LlamerosGUI)
    gui._sort_states = {}

    columns = ["pid", "name", "cpu_percent", "ram_mb", "gpu_mb", "status", "priority", "classification"]
    for column in columns:
        gui._on_heading_click(column)
        _ = gui._sorted_rows(_rows())

    assert set(gui._sort_states.keys()) == set(columns)
