"""main.py – Entry point for the Llameros GPU/RAM watchdog."""
import sys
import threading
from pathlib import Path

# Allow `python src/main.py` without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from llameros.process_rules import load_rules
from llameros import watchdog
from llameros.scheduler import TurnTakingScheduler
from llameros.gui import start_gui


def main():
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
