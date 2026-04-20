"""main.py - Entry point for the Llameros GPU/RAM watchdog."""
import argparse
import json
import subprocess
import sys
import threading
from pathlib import Path

# Allow `python src/main.py` without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from llameros.process_rules import load_rules
from llameros import watchdog
from llameros.scheduler import TurnTakingScheduler
from llameros.gui import start_gui
from llameros import gpu_monitor
from llameros import system_monitor


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_version() -> str:
    version_file = _REPO_ROOT / "VERSION"
    if not version_file.exists():
        return "0.0.0"
    return version_file.read_text(encoding="utf-8").strip()


def _run_repair() -> int:
    repair_script = _REPO_ROOT / "installer" / "repair.ps1"
    if not repair_script.exists():
        print("Repair script not found.", file=sys.stderr)
        return 1

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repair_script),
    ]
    result = subprocess.run(command, capture_output=True, text=True, cwd=str(_REPO_ROOT), check=False)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def _print_diagnostics() -> None:
    rules = load_rules()
    diagnostics = {
        "version": _read_version(),
        "vram_limit_mb": rules.get("vram_limit_mb"),
        "ram_limit_mb": rules.get("ram_limit_mb"),
        "process_count": len(rules.get("processes", [])),
        "gpu_memory_used_mb": gpu_monitor.get_gpu_memory(),
        "ram_used_mb": system_monitor.get_ram_usage(),
    }
    print(json.dumps(diagnostics, sort_keys=True))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Llameros watchdog entry point")
    parser.add_argument("--version", action="store_true", help="Print the Llameros version and exit")
    parser.add_argument("--diagnostics", action="store_true", help="Print diagnostics as JSON and exit")
    parser.add_argument("--repair", action="store_true", help="Run installer/repair.ps1 and exit")
    return parser


def main():
    args = _build_parser().parse_args()

    if args.version:
        print(_read_version())
        return

    if args.diagnostics:
        _print_diagnostics()
        return

    if args.repair:
        raise SystemExit(_run_repair())

    rules = load_rules()

    scheduler = TurnTakingScheduler(rules)

    # Deterministic startup order: scheduler thread, watchdog thread, then GUI loop.
    scheduler_thread = threading.Thread(target=scheduler.start, name="llameros-scheduler", daemon=True)
    scheduler_thread.start()

    watchdog_thread = threading.Thread(
        target=watchdog.start,
        args=(rules,),
        name="llameros-watchdog",
        daemon=True,
    )
    watchdog_thread.start()

    start_gui(scheduler)


if __name__ == "__main__":
    main()
