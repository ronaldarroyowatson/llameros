"""watchdog.py – Poll GPU/RAM and kill processes when thresholds are exceeded."""
import logging
import time

import psutil

from .gpu_monitor import get_gpu_memory
from .system_monitor import get_ram_usage
from .process_rules import get_vram_limit, get_ram_limit, get_process_list

logging.basicConfig(
    filename="llameros.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_POLL_INTERVAL = 1  # seconds


def _kill_first_match(process_names: list) -> bool:
    """Kill the first running process whose name matches the ordered list.

    Returns True if a process was killed, False otherwise.
    """
    running = {p.info["name"]: p for p in psutil.process_iter(["name", "pid"])}
    for name in process_names:
        if name in running:
            proc = running[name]
            try:
                proc.kill()
                logging.warning("Killed process '%s' (PID %s)", name, proc.pid)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                logging.error("Failed to kill '%s': %s", name, exc)
    return False


def run_once(rules: dict) -> None:
    """Execute a single watchdog iteration (useful for testing)."""
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
