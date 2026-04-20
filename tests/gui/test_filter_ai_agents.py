"""Tests for AI-agent process classification and filtering with updated thresholds."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from llameros import process_utils


def test_process_with_200mb_vram_is_classified_as_ai_agent():
    """Any process using ≥200 MB GPU VRAM must be classified as an AI agent."""
    result = process_utils._classify_from_snapshot(
        pid=1000,
        name="python.exe",
        username="user",
        cmdline_blob="python server.py",
        cpu_percent=5.0,
        gpu_mb=200.0,
        has_window=False,
    )
    assert result == "ai agent", (
        f"Expected 'ai agent' for 200 MB VRAM process, got '{result}'"
    )


def test_process_below_200mb_vram_not_classified_as_ai_from_vram_alone():
    """A process using exactly 199 MB VRAM must NOT be AI-classified based on VRAM alone."""
    result = process_utils._classify_from_snapshot(
        pid=1000,
        name="python.exe",
        username="user",
        cmdline_blob="python server.py",
        cpu_percent=5.0,
        gpu_mb=199.0,
        has_window=True,
    )
    # Without cmdline hints or high VRAM, this should be "user"
    assert result != "ai agent", (
        f"Expected non-AI classification for 199 MB VRAM, got '{result}'"
    )


def test_python_with_llm_cmdline_is_classified_as_ai_agent():
    """python.exe running LLM workloads (cmdline hint) must be classified as AI agent."""
    result = process_utils._classify_from_snapshot(
        pid=2000,
        name="python.exe",
        username="user",
        cmdline_blob="python -m vllm serve llama3",
        cpu_percent=10.0,
        gpu_mb=0.0,
        has_window=False,
    )
    assert result == "ai agent"


def test_node_with_copilot_agent_cmdline_is_classified_as_ai_agent():
    """node.exe running Copilot agents must be classified as AI agent."""
    result = process_utils._classify_from_snapshot(
        pid=3000,
        name="node.exe",
        username="user",
        cmdline_blob="node dist/agent/copilot-language-server.js",
        cpu_percent=5.0,
        gpu_mb=0.0,
        has_window=False,
    )
    assert result == "ai agent"


def test_ollama_is_classified_as_ai_agent():
    """ollama.exe must always be classified as AI agent."""
    result = process_utils._classify_from_snapshot(
        pid=4000,
        name="ollama.exe",
        username="user",
        cmdline_blob="ollama serve",
        cpu_percent=2.0,
        gpu_mb=0.0,
        has_window=False,
    )
    assert result == "ai agent"


def test_sustained_high_cpu_process_classified_as_ai_agent(monkeypatch):
    """A process sustaining >25% CPU for >3 seconds must be classified as AI agent."""
    import time
    # Seed the sustained-CPU tracker as if the process started 4 seconds ago
    pid = 5555
    monkeypatch.setitem(
        process_utils._sustained_cpu_start,
        pid,
        time.monotonic() - 4.0,  # 4 seconds ago
    )
    result = process_utils._classify_from_snapshot(
        pid=pid,
        name="worker.exe",
        username="user",
        cmdline_blob="worker.exe",
        cpu_percent=30.0,  # above 25% threshold
        gpu_mb=0.0,
        has_window=True,
    )
    assert result == "ai agent", (
        f"Expected 'ai agent' for sustained-CPU process, got '{result}'"
    )


def test_short_cpu_spike_not_classified_as_ai_agent(monkeypatch):
    """A process with >25% CPU for only 1 second must NOT be AI-classified."""
    import time
    pid = 6666
    monkeypatch.setitem(
        process_utils._sustained_cpu_start,
        pid,
        time.monotonic() - 1.0,  # only 1 second ago
    )
    result = process_utils._classify_from_snapshot(
        pid=pid,
        name="worker.exe",
        username="user",
        cmdline_blob="worker.exe",
        cpu_percent=30.0,
        gpu_mb=0.0,
        has_window=True,
    )
    assert result != "ai agent", (
        f"Short CPU spike should not trigger AI classification; got '{result}'"
    )


def test_ai_filter_returns_non_empty_when_ai_rows_exist():
    """filter_process_rows with only_ai=True must not blank the table when AI rows exist."""
    rows = [
        {
            "pid": 10,
            "name": "ollama.exe",
            "classification": "ai agent",
            "monitored": False,
            "cpu_percent": 8.0,
            "ram_mb": 2048.0,
            "gpu_mb": 250.0,
        },
        {
            "pid": 11,
            "name": "chrome.exe",
            "classification": "user",
            "monitored": False,
            "cpu_percent": 2.0,
            "ram_mb": 512.0,
            "gpu_mb": 0.0,
        },
    ]
    filtered = process_utils.filter_process_rows(rows, rules={}, only_ai=True)
    assert len(filtered) == 1
    assert filtered[0]["pid"] == 10
