"""process_rules.py – Load and expose watchdog rules from YAML config."""
from pathlib import Path
import yaml

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "rules.yaml"


def load_rules(config_path: Path = _DEFAULT_CONFIG) -> dict:
    """Load rules YAML and return as a dict."""
    with open(config_path, "r") as fh:
        return yaml.safe_load(fh)


def get_vram_limit(rules: dict) -> float:
    """Return VRAM threshold in MB."""
    return float(rules.get("vram_limit_mb", 14000))


def get_ram_limit(rules: dict) -> float:
    """Return RAM threshold in MB."""
    return float(rules.get("ram_limit_mb", 30000))


def get_process_list(rules: dict) -> list:
    """Return ordered list of process names to kill on threshold breach."""
    return rules.get("processes", [])
