"""process_utils.py - Process inspection and lifecycle helpers for Llameros."""
from __future__ import annotations

import ctypes
import logging
import subprocess
import time
from collections.abc import Iterable
from typing import Any

import psutil

LOGGER = logging.getLogger(__name__)

AI_GPU_MB_THRESHOLD = 200.0
AI_CPU_THRESHOLD = 25.0
AI_CPU_SUSTAINED_SECONDS = 3.0
LOW_CPU_BACKGROUND_THRESHOLD = 1.0

# Tracks monotonic timestamp when a PID first exceeded AI_CPU_THRESHOLD
_sustained_cpu_start: dict[int, float] = {}

_AI_EXECUTABLES = {"ollama.exe"}
_EDITOR_EXECUTABLES = {"code.exe", "code-insiders.exe"}
_VM_EXECUTABLES = {"virtualboxvm.exe"}
_SYSTEM_USERS = {
    "nt authority\\system",
    "nt authority\\local service",
    "nt authority\\network service",
    "system",
}
_AI_CMDLINE_HINTS = {
    "llm",
    "llama",
    "vllm",
    "transformers",
    "openai",
    "copilot",
    "agent",
    "ollama",
}
_IDLE_PROCESS_NAMES = {"system idle process", "idle"}


def _gpu_memory_by_pid() -> dict[int, float]:
    """Return GPU memory (MB) by PID from nvidia-smi, or empty if unavailable."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    if result.returncode != 0:
        return {}

    usage: dict[int, float] = {}
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
            gpu_mb = float(parts[1])
        except ValueError:
            continue
        usage[pid] = usage.get(pid, 0.0) + gpu_mb
    return usage


def _visible_window_pids() -> set[int]:
    """Return PIDs that currently own a visible top-level window on Windows."""
    if not hasattr(ctypes, "windll"):
        return set()

    user32 = ctypes.windll.user32
    found: set[int] = set()

    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _callback(hwnd: int, lparam: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                found.add(int(pid.value))
        return True

    user32.EnumWindows(enum_windows_proc(_callback), 0)
    return found


def _name_lower(name: str | None) -> str:
    return (name or "").strip().lower()


def _cmdline_tokens(cmdline: Iterable[str]) -> str:
    return " ".join(cmdline).lower()


def normalize_cpu_percent(raw_cpu_percent: float, cpu_count: int | None = None) -> float:
    """Normalize process CPU usage to total-system percentage."""
    resolved_cpu_count = max(1, int(cpu_count or (psutil.cpu_count(logical=True) or 1)))
    normalized = max(0.0, float(raw_cpu_percent) / resolved_cpu_count)
    return min(100.0, normalized)


def is_idle_process_name(name: str | None) -> bool:
    return _name_lower(name) in _IDLE_PROCESS_NAMES


def _classify_from_snapshot(
    *,
    pid: int,
    name: str,
    username: str,
    cmdline_blob: str,
    cpu_percent: float,
    gpu_mb: float,
    has_window: bool,
) -> str:
    lower_name = _name_lower(name)
    lower_user = (username or "").lower()

    if lower_name in _EDITOR_EXECUTABLES:
        return "editor"

    if lower_name in _VM_EXECUTABLES:
        return "vm"

    if pid < 200 or lower_user in _SYSTEM_USERS:
        return "system"

    # Track sustained high-CPU processes
    if cpu_percent > AI_CPU_THRESHOLD:
        if pid not in _sustained_cpu_start:
            _sustained_cpu_start[pid] = time.monotonic()
    else:
        _sustained_cpu_start.pop(pid, None)

    sustained_ai = (
        pid in _sustained_cpu_start
        and (time.monotonic() - _sustained_cpu_start[pid]) >= AI_CPU_SUSTAINED_SECONDS
    )

    is_python_llm = lower_name == "python.exe" and any(
        hint in cmdline_blob for hint in _AI_CMDLINE_HINTS
    )
    is_node_agent = lower_name == "node.exe" and (
        "copilot" in cmdline_blob or "agent" in cmdline_blob
    )

    if (
        lower_name in _AI_EXECUTABLES
        or is_python_llm
        or is_node_agent
        or gpu_mb >= AI_GPU_MB_THRESHOLD
        or sustained_ai
    ):
        return "ai agent"

    if not has_window and cpu_percent <= LOW_CPU_BACKGROUND_THRESHOLD:
        return "background"

    return "user"


def classify_process(pid: int) -> str:
    """Classify a process as system/user/AI/editor/VM/background."""
    gpu_map = _gpu_memory_by_pid()
    window_pids = _visible_window_pids()
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            name = proc.name()
            username = proc.username() or ""
            cmdline_blob = _cmdline_tokens(proc.cmdline())
            raw_cpu_percent = float(proc.cpu_percent(interval=0.0))
            cpu_percent = normalize_cpu_percent(raw_cpu_percent)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return "background"

    classification = _classify_from_snapshot(
        pid=pid,
        name=name,
        username=username,
        cmdline_blob=cmdline_blob,
        cpu_percent=raw_cpu_percent,
        gpu_mb=float(gpu_map.get(pid, 0.0)),
        has_window=pid in window_pids,
    )
    LOGGER.debug(
        "action=classification pid=%s name=%s classification=%s cpu_percent=%.1f gpu_mb=%.1f",
        pid,
        name,
        classification,
        cpu_percent,
        float(gpu_map.get(pid, 0.0)),
    )
    return classification


def is_ai_agent(pid: int) -> bool:
    return classify_process(pid) == "ai agent"


def is_editor(pid: int) -> bool:
    return classify_process(pid) == "editor"


def is_vm(pid: int) -> bool:
    return classify_process(pid) == "vm"


def is_system(pid: int) -> bool:
    return classify_process(pid) == "system"


def get_global_process_rows(
    monitored_pids: set[int] | None = None,
    monitored_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return process rows for the global process table with classifications."""
    monitored_pids = monitored_pids or set()
    monitored_names = {_name_lower(name) for name in (monitored_names or set())}

    gpu_map = _gpu_memory_by_pid()
    window_pids = _visible_window_pids()
    cpu_count = max(1, int(psutil.cpu_count(logical=True) or 1))
    rows: list[dict[str, Any]] = []

    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "username", "cmdline"]):
        try:
            pid = int(proc.info["pid"])
            name = proc.info.get("name") or "unknown"
            raw_cpu_percent = float(proc.info.get("cpu_percent") or 0.0)
            cpu_percent = normalize_cpu_percent(raw_cpu_percent, cpu_count=cpu_count)
            if is_idle_process_name(proc.info.get("name")):
                cpu_percent = 0.0
            ram_mb = float(proc.info["memory_info"].rss) / (1024 * 1024)
            status = proc.info.get("status") or "unknown"
            username = proc.info.get("username") or ""
            cmdline_blob = _cmdline_tokens(proc.info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
            continue

        normalized_status = "paused" if status == psutil.STATUS_STOPPED else "running"
        gpu_mb = float(gpu_map.get(pid, 0.0))
        classification = _classify_from_snapshot(
            pid=pid,
            name=name,
            username=username,
            cmdline_blob=cmdline_blob,
            cpu_percent=raw_cpu_percent,
            gpu_mb=gpu_mb,
            has_window=pid in window_pids,
        )

        rows.append(
            {
                "pid": pid,
                "name": name,
                "cpu_percent": cpu_percent,
                "ram_mb": ram_mb,
                "gpu_mb": gpu_mb,
                "status": normalized_status,
                "classification": classification,
                "monitored": pid in monitored_pids or _name_lower(name) in monitored_names,
            }
        )
        LOGGER.debug(
            "action=process-discovery pid=%s name=%s classification=%s monitored=%s cpu_percent=%.1f ram_mb=%.1f gpu_mb=%.1f",
            pid,
            name,
            classification,
            pid in monitored_pids or _name_lower(name) in monitored_names,
            cpu_percent,
            ram_mb,
            gpu_mb,
        )

    return rows


def filter_process_rows(
    rows: list[dict[str, Any]],
    rules: dict | None = None,
    *,
    only_ai: bool = False,
    only_heavy: bool = False,
    only_monitored: bool = False,
) -> list[dict[str, Any]]:
    """Apply deterministic GUI process filters without mutating input rows."""
    filtered = list(rows)

    if only_monitored:
        filtered = [row for row in filtered if bool(row.get("monitored"))]
    if only_ai:
        filtered = [row for row in filtered if row.get("classification") == "ai agent"]
    if only_heavy:
        filtered = [row for row in filtered if is_heavy_hitter(row, rules)]

    LOGGER.debug(
        "action=filter only_ai=%s only_heavy=%s only_monitored=%s before=%s after=%s",
        only_ai,
        only_heavy,
        only_monitored,
        len(rows),
        len(filtered),
    )
    return filtered


def is_heavy_hitter(row: dict[str, Any], rules: dict | None = None) -> bool:
    """Return True when a process row is a significant resource consumer."""
    rules = rules or {}
    ram_limit = float(rules.get("ram_limit_mb", 30000.0))
    vram_limit = float(rules.get("vram_limit_mb", 14000.0))
    cpu_limit = float(rules.get("cpu_limit_percent", 100.0))

    cpu_percent = float(row.get("cpu_percent", 0.0))
    ram_mb = float(row.get("ram_mb", 0.0))
    gpu_mb = float(row.get("gpu_mb", 0.0))

    return (
        gpu_mb > AI_GPU_MB_THRESHOLD
        or gpu_mb >= vram_limit * 0.20
        or ram_mb >= ram_limit * 0.20
        or cpu_percent >= max(50.0, cpu_limit * 0.80)
    )


def get_top_cpu_process() -> dict[str, Any] | None:
    """Return the process consuming the most CPU."""
    top: dict[str, Any] | None = None
    cpu_count = max(1, int(psutil.cpu_count(logical=True) or 1))
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            name = proc.info.get("name") or "unknown"
            if is_idle_process_name(name):
                continue
            cpu_percent = normalize_cpu_percent(float(proc.info.get("cpu_percent") or 0.0), cpu_count=cpu_count)
            if top is None or cpu_percent > top["cpu_percent"]:
                top = {
                    "pid": int(proc.info["pid"]),
                    "name": name,
                    "cpu_percent": cpu_percent,
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return top


def get_top_ram_process() -> dict[str, Any] | None:
    """Return the process consuming the most resident memory."""
    top: dict[str, Any] | None = None
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            ram_mb = float(proc.info["memory_info"].rss) / (1024 * 1024)
            if top is None or ram_mb > top["ram_mb"]:
                top = {
                    "pid": int(proc.info["pid"]),
                    "name": proc.info.get("name") or "unknown",
                    "ram_mb": ram_mb,
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            continue
    return top


def get_top_gpu_process() -> dict[str, Any] | None:
    """Return the process consuming the most GPU memory."""
    gpu_map = _gpu_memory_by_pid()
    if not gpu_map:
        return None

    top_pid = max(gpu_map, key=gpu_map.get)
    gpu_mb = float(gpu_map[top_pid])
    try:
        proc = psutil.Process(top_pid)
        name = proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        name = "unknown"
    return {"pid": top_pid, "name": name, "gpu_mb": gpu_mb}


def suspend_process(pid: int) -> bool:
    """Suspend a process by PID; return True if action succeeded."""
    try:
        proc = psutil.Process(pid)
        proc.suspend()
        LOGGER.debug("action=pause pid=%s name=%s success=true", pid, proc.name())
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        LOGGER.debug("action=pause pid=%s success=false", pid)
        return False


def resume_process(pid: int) -> bool:
    """Resume a process by PID; return True if action succeeded."""
    try:
        proc = psutil.Process(pid)
        proc.resume()
        LOGGER.debug("action=resume pid=%s name=%s success=true", pid, proc.name())
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        LOGGER.debug("action=resume pid=%s success=false", pid)
        return False


def kill_process(pid: int) -> bool:
    """Kill a process by PID; return True if action succeeded."""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        LOGGER.debug("action=kill pid=%s name=%s success=true", pid, proc.name())
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        LOGGER.debug("action=kill pid=%s success=false", pid)
        return False


def get_process_stats(pid: int) -> dict[str, Any] | None:
    """Return process CPU/RAM/GPU stats and status for a PID."""
    gpu_map = _gpu_memory_by_pid()
    window_pids = _visible_window_pids()
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            raw_cpu_percent = float(proc.cpu_percent(interval=0.0))
            cpu_percent = normalize_cpu_percent(raw_cpu_percent)
            ram_mb = float(proc.memory_info().rss) / (1024 * 1024)
            status = proc.status()
            name = proc.name()
            username = proc.username() or ""
            cmdline_blob = _cmdline_tokens(proc.cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None

    normalized_status = "paused" if status == psutil.STATUS_STOPPED else "running"
    classification = _classify_from_snapshot(
        pid=pid,
        name=name,
        username=username,
        cmdline_blob=cmdline_blob,
        cpu_percent=raw_cpu_percent,
        gpu_mb=float(gpu_map.get(pid, 0.0)),
        has_window=pid in window_pids,
    )
    return {
        "pid": pid,
        "name": name,
        "cpu_percent": cpu_percent,
        "ram_mb": ram_mb,
        "gpu_mb": float(gpu_map.get(pid, 0.0)),
        "status": normalized_status,
        "classification": classification,
    }