"""watchdog.py – Poll GPU/RAM and kill processes when thresholds are exceeded."""
import logging
import time

import psutil

from .gpu_monitor import get_gpu_memory
from .system_monitor import get_ram_usage
from .process_rules import get_vram_limit, get_ram_limit, get_process_list
from . import process_utils

logging.basicConfig(
    filename="llameros.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_POLL_INTERVAL = 1  # seconds


def _heavy_hitter_names(rules: dict) -> list[str]:
    rows = process_utils.get_global_process_rows(
        monitored_names=set(get_process_list(rules)),
    )
    scored: list[tuple[float, str, dict]] = []
    for row in rows:
        if not process_utils.is_heavy_hitter(row, rules):
            continue
        score = float(row["cpu_percent"]) + (float(row["ram_mb"]) / 1024.0) + (float(row["gpu_mb"]) / 512.0)
        scored.append((score, str(row["name"]), row))

    scored.sort(key=lambda item: (-item[0], item[1].lower()))

    for _, _, row in scored:
        logging.warning(
            "Resource spike: PID=%s NAME=%s CLASS=%s CPU=%.1f RAM=%.1fMB GPU=%.1fMB",
            row["pid"],
            row["name"],
            row["classification"],
            row["cpu_percent"],
            row["ram_mb"],
            row["gpu_mb"],
        )

    names: list[str] = []
    seen: set[str] = set()
    for _, name, _ in scored:
        lower = name.lower()
        if lower in seen:
            continue
        seen.add(lower)
        names.append(name)
    return names


def _auto_add_heavy_hitters(rules: dict) -> None:
    process_names = get_process_list(rules)
    existing = {name.lower() for name in process_names}
    new_names = []
    for name in _heavy_hitter_names(rules):
        if name.lower() in existing:
            continue
        new_names.append(name)
        existing.add(name.lower())

    if not new_names:
        return

    process_names.extend(new_names)
    rules["processes"] = process_names
    logging.info("Auto-added heavy hitters to monitored list: %s", ", ".join(new_names))


def _kill_first_match(process_names: list) -> bool:
    """Kill the first running process whose name matches the ordered list.

    Returns True if a process was killed, False otherwise.
    """
    running = {p.info["name"]: p for p in psutil.process_iter(["name", "pid"])}
    for name in process_names:
        if name in running:
            proc = running[name]
            try:
                if process_utils.is_system(proc.pid):
                    logging.warning("Skipped killing system process '%s' (PID %s)", name, proc.pid)
                    continue
                proc.kill()
                logging.warning("Killed process '%s' (PID %s)", name, proc.pid)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                logging.error("Failed to kill '%s': %s", name, exc)
    return False


def run_once(rules: dict) -> None:
    """Execute a single watchdog iteration (useful for testing)."""
    _auto_add_heavy_hitters(rules)

    vram_used = get_gpu_memory()
    ram_used = get_ram_usage()

    vram_limit = get_vram_limit(rules)
    ram_limit = get_ram_limit(rules)
    process_names = get_process_list(rules)

    if vram_used > vram_limit:
        logging.warning(
            "VRAM threshold exceeded: %.0f MB used / %.0f MB limit", vram_used, vram_limit
        )
        _kill_first_match(process_names)

    if ram_used > ram_limit:
        logging.warning(
            "RAM threshold exceeded: %.0f MB used / %.0f MB limit", ram_used, ram_limit
        )
        _kill_first_match(process_names)


def start(rules: dict) -> None:
    """Enter the main watchdog loop (runs until KeyboardInterrupt)."""
    logging.info("Llameros watchdog started.")
    try:
        while True:
            run_once(rules)
            time.sleep(_POLL_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Llameros watchdog stopped.")
