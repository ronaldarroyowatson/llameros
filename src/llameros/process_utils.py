"""process_utils.py - Process inspection and lifecycle helpers for Llameros."""
from __future__ import annotations

import subprocess
from typing import Any

import psutil


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


def get_top_cpu_process() -> dict[str, Any] | None:
    """Return the process consuming the most CPU."""
    top: dict[str, Any] | None = None
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            cpu_percent = float(proc.info.get("cpu_percent") or 0.0)
            if top is None or cpu_percent > top["cpu_percent"]:
                top = {
                    "pid": int(proc.info["pid"]),
                    "name": proc.info.get("name") or "unknown",
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
        psutil.Process(pid).suspend()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def resume_process(pid: int) -> bool:
    """Resume a process by PID; return True if action succeeded."""
    try:
        psutil.Process(pid).resume()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def kill_process(pid: int) -> bool:
    """Kill a process by PID; return True if action succeeded."""
    try:
        psutil.Process(pid).kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def get_process_stats(pid: int) -> dict[str, Any] | None:
    """Return process CPU/RAM/GPU stats and status for a PID."""
    gpu_map = _gpu_memory_by_pid()
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            cpu_percent = float(proc.cpu_percent(interval=0.0))
            ram_mb = float(proc.memory_info().rss) / (1024 * 1024)
            status = proc.status()
            name = proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None

    normalized_status = "paused" if status == psutil.STATUS_STOPPED else "running"
    return {
        "pid": pid,
        "name": name,
        "cpu_percent": cpu_percent,
        "ram_mb": ram_mb,
        "gpu_mb": float(gpu_map.get(pid, 0.0)),
        "status": normalized_status,
    }