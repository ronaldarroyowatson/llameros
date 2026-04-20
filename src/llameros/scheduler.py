"""scheduler.py - Process scheduler with turn-taking and resource-aware controls."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import psutil

from .gpu_monitor import get_gpu_memory
from .process_rules import get_ram_limit, get_vram_limit
from .system_monitor import get_ram_usage
from . import process_utils

LOGGER = logging.getLogger(__name__)


@dataclass
class MonitoredProcess:
    pid: int
    name: str
    priority: int = 5
    background: bool = False


class TurnTakingScheduler:
    """Coordinate monitored processes with optional turn-taking behavior."""

    def __init__(self, rules: dict):
        self._rules = rules
        self._process_names = list(rules.get("processes", []))
        self._poll_interval = float(rules.get("scheduler_poll_interval_seconds", 1.0))
        self._quantum_seconds = float(rules.get("turn_quantum_seconds", 5.0))
        self._cpu_limit_percent = float(rules.get("cpu_limit_percent", 100.0))
        self._vram_limit = get_vram_limit(rules)
        self._ram_limit = get_ram_limit(rules)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._turn_taking_enabled = bool(rules.get("turn_taking_mode", False))

        self._monitored: dict[int, MonitoredProcess] = {}
        self._manual_paused: set[int] = set()
        self._throttled: set[int] = set()

        self._rr_index = 0
        self._active_pid: int | None = None
        self._slot_deadline = 0.0

    def start(self) -> None:
        """Run scheduler loop until stopped."""
        while not self._stop_event.is_set():
            self._sync_processes()
            self._apply_resource_awareness()
            self._apply_turn_taking()
            time.sleep(self._poll_interval)

    def stop(self) -> None:
        """Signal loop shutdown."""
        self._stop_event.set()

    def set_turn_taking_mode(self, enabled: bool) -> None:
        with self._lock:
            self._turn_taking_enabled = enabled
            self._active_pid = None
            self._slot_deadline = 0.0

    def get_turn_taking_mode(self) -> bool:
        with self._lock:
            return self._turn_taking_enabled

    def pause(self, pid: int) -> bool:
        ok = process_utils.suspend_process(pid)
        if ok:
            with self._lock:
                self._manual_paused.add(pid)
                if self._active_pid == pid:
                    self._active_pid = None
        return ok

    def resume(self, pid: int) -> bool:
        ok = process_utils.resume_process(pid)
        if ok:
            with self._lock:
                self._manual_paused.discard(pid)
                self._throttled.discard(pid)
        return ok

    def kill(self, pid: int) -> bool:
        ok = process_utils.kill_process(pid)
        if ok:
            with self._lock:
                self._manual_paused.discard(pid)
                self._throttled.discard(pid)
                self._monitored.pop(pid, None)
                if self._active_pid == pid:
                    self._active_pid = None
        return ok

    def set_priority(self, pid: int, level: int) -> None:
        with self._lock:
            proc = self._monitored.get(pid)
            if proc:
                proc.priority = max(1, min(10, int(level)))

    def set_background(self, pid: int, enabled: bool = True) -> None:
        with self._lock:
            proc = self._monitored.get(pid)
            if proc:
                proc.background = enabled

    def get_process_rows(self) -> list[dict]:
        rows: list[dict] = []
        with self._lock:
            snapshot = list(self._monitored.values())

        for proc in snapshot:
            stats = process_utils.get_process_stats(proc.pid)
            if not stats:
                continue
            rows.append(
                {
                    "pid": proc.pid,
                    "name": proc.name,
                    "cpu_percent": stats["cpu_percent"],
                    "ram_mb": stats["ram_mb"],
                    "gpu_mb": stats["gpu_mb"],
                    "status": stats["status"],
                    "priority": proc.priority,
                }
            )
        return rows

    def _sync_processes(self) -> None:
        running: dict[int, str] = {}
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info.get("name") or ""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if name in self._process_names:
                running[int(proc.info["pid"])] = name

        with self._lock:
            for pid in list(self._monitored):
                if pid not in running:
                    self._monitored.pop(pid, None)
                    self._manual_paused.discard(pid)
                    self._throttled.discard(pid)

            for pid, name in running.items():
                if pid not in self._monitored:
                    self._monitored[pid] = MonitoredProcess(pid=pid, name=name)

    def _apply_resource_awareness(self) -> None:
        rows = self.get_process_rows()
        if not rows:
            return

        vram_used = get_gpu_memory()
        ram_used = get_ram_usage()
        cpu_used = psutil.cpu_percent(interval=0.0)

        hot: set[int] = set()

        if vram_used > self._vram_limit:
            gpu_heavy = max(rows, key=lambda row: row["gpu_mb"])
            if gpu_heavy["gpu_mb"] > 0:
                hot.add(int(gpu_heavy["pid"]))

        if ram_used > self._ram_limit:
            ram_heavy = max(rows, key=lambda row: row["ram_mb"])
            hot.add(int(ram_heavy["pid"]))

        if cpu_used > self._cpu_limit_percent:
            cpu_heavy = max(rows, key=lambda row: row["cpu_percent"])
            hot.add(int(cpu_heavy["pid"]))

        with self._lock:
            manual = set(self._manual_paused)
            throttled = set(self._throttled)

        for pid in hot:
            if pid in manual:
                continue
            if process_utils.suspend_process(pid):
                with self._lock:
                    self._throttled.add(pid)
                LOGGER.warning("Scheduler suspended PID %s due to high resource pressure", pid)

        if not hot and throttled:
            for pid in throttled:
                if pid in manual:
                    continue
                process_utils.resume_process(pid)
            with self._lock:
                self._throttled.clear()

    def _apply_turn_taking(self) -> None:
        with self._lock:
            if not self._turn_taking_enabled:
                return

            candidates = [
                proc
                for proc in self._monitored.values()
                if proc.pid not in self._manual_paused and proc.pid not in self._throttled
            ]

            if not candidates:
                self._active_pid = None
                return

            candidates.sort(key=lambda proc: (-proc.priority, proc.pid))
            now = time.monotonic()
            should_advance = (
                self._active_pid is None
                or self._active_pid not in {proc.pid for proc in candidates}
                or now >= self._slot_deadline
            )

            if should_advance:
                self._rr_index = (self._rr_index + 1) % len(candidates)
                self._active_pid = candidates[self._rr_index].pid
                self._slot_deadline = now + self._quantum_seconds

            active_pid = self._active_pid
            candidate_pids = [proc.pid for proc in candidates]

        for pid in candidate_pids:
            if pid == active_pid:
                process_utils.resume_process(pid)
            else:
                process_utils.suspend_process(pid)