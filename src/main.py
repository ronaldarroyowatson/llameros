"""main.py - Entry point for the Llameros GPU/RAM watchdog."""
import argparse
import json
import logging
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
from llameros.logging_utils import configure_logging


_REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--list-processes", action="store_true", help="List process rows as JSON and exit")
    parser.add_argument("--pause", type=int, metavar="PID", help="Pause a process by PID and exit")
    parser.add_argument("--resume", type=int, metavar="PID", help="Resume a process by PID and exit")
    parser.add_argument("--kill", type=int, metavar="PID", help="Kill a process by PID and exit")
    parser.add_argument("--set-priority", nargs=2, metavar=("PID", "LEVEL"), help="Set monitored process priority and exit")
    parser.add_argument("--set-background", type=int, metavar="PID", help="Mark a process as background and exit")
    parser.add_argument("--bring-foreground", type=int, metavar="PID", help="Remove background flag from a process and exit")
    parser.add_argument("--enable-turn-taking", action="store_true", help="Enable turn-taking mode and exit")
    parser.add_argument("--disable-turn-taking", action="store_true", help="Disable turn-taking mode and exit")
    return parser


def _handle_cli_actions(args: argparse.Namespace, scheduler: TurnTakingScheduler) -> int | None:
    if hasattr(scheduler, "_sync_processes"):
        scheduler._sync_processes()

    if args.list_processes:
        rows = scheduler.get_process_rows()
        LOGGER.debug("action=cli command=list-processes row_count=%s", len(rows))
        print(json.dumps(rows, sort_keys=True))
        return 0

    actions = [
        (args.pause is not None, "pause", lambda: scheduler.pause(args.pause)),
        (args.resume is not None, "resume", lambda: scheduler.resume(args.resume)),
        (args.kill is not None, "kill", lambda: scheduler.kill(args.kill)),
        (
            args.set_priority is not None,
            "set-priority",
            lambda: scheduler.set_priority(int(args.set_priority[0]), int(args.set_priority[1])) or True,
        ),
        (args.set_background is not None, "set-background", lambda: scheduler.set_background(args.set_background, enabled=True) or True),
        (
            args.bring_foreground is not None,
            "bring-foreground",
            lambda: (
                scheduler.bring_foreground(args.bring_foreground)
                if hasattr(scheduler, "bring_foreground")
                else scheduler.set_background(args.bring_foreground, enabled=False)
            )
            or True,
        ),
        (args.enable_turn_taking, "enable-turn-taking", lambda: scheduler.set_turn_taking_mode(True) or True),
        (args.disable_turn_taking, "disable-turn-taking", lambda: scheduler.set_turn_taking_mode(False) or True),
    ]

    for enabled, command_name, action in actions:
        if not enabled:
            continue
        LOGGER.debug("action=cli command=%s", command_name)
        return 0 if action() is not False else 1

    return None


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    initial_rules = load_rules()
    configure_logging(initial_rules, debug=args.debug)

    if args.version:
        print(_read_version())
        return 0

    if args.diagnostics:
        _print_diagnostics()
        return 0

    if args.repair:
        raise SystemExit(_run_repair())

    rules = initial_rules

    scheduler = TurnTakingScheduler(rules)
    cli_result = _handle_cli_actions(args, scheduler)
    if cli_result is not None:
        return cli_result

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
