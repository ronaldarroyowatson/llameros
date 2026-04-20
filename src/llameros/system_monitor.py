"""system_monitor.py – Query system RAM usage via psutil."""
import psutil


def get_ram_usage() -> float:
    """Return used RAM in MB."""
    return psutil.virtual_memory().used / (1024 * 1024)
