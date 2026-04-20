"""test_watchdog.py – Smoke tests for the Llameros watchdog."""
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the src directory is on the path when running tests directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llameros.process_rules import load_rules, get_vram_limit, get_ram_limit, get_process_list
from llameros import watchdog


def test_load_rules():
    rules = load_rules()
    assert "vram_limit_mb" in rules
    assert "ram_limit_mb" in rules
    assert isinstance(get_process_list(rules), list)


def test_run_once_no_crash():
    """Watchdog run_once should complete without raising exceptions."""
    rules = load_rules()
    # Patch monitors to return values safely below thresholds
    with patch("llameros.watchdog.get_gpu_memory", return_value=0.0), \
         patch("llameros.watchdog.get_ram_usage", return_value=0.0):
        watchdog.run_once(rules)


def test_thresholds_from_rules():
    rules = {"vram_limit_mb": 8000, "ram_limit_mb": 16000, "processes": ["test.exe"]}
    assert get_vram_limit(rules) == 8000.0
    assert get_ram_limit(rules) == 16000.0
    assert get_process_list(rules) == ["test.exe"]
