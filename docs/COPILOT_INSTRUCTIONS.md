# Copilot Instructions for Llameros

## Purpose

This file tells GitHub Copilot how to behave inside the Llameros project. It defines architecture rules, coding style, reproducibility requirements, and constraints. Copilot must read and respect this file before generating, modifying, or suggesting any code within this repository.

---

## Core Principles

- **Deterministic, reproducible behavior** — Every run with the same config must produce the same outcome.
- **Modular architecture** — Each module has a single, clearly scoped responsibility.
- **No hidden state** — All state must be explicit and traceable.
- **No cross-project interference** — Llameros must not modify files, processes, or resources outside its defined scope.
- **No hard-coded ports** — All network or IPC configuration must come from external config.
- **Adaptive, self-healing logic** — The watchdog must recover gracefully from transient errors without crashing.
- **Artifact-driven development** — All decisions and changes must be traceable to config files, logs, or codex entries.
- **Stepwise, linear debugging** — Debugging follows a strict, reproducible sequence; no speculative jumps.
- **Clear diagnostics and logging** — Every significant action or decision must be logged with context.
- **No silent failures** — All exceptions and error conditions must be caught, logged, and surfaced explicitly.

---

## Coding Style Rules

- **Python 3.11+** — All code must target Python 3.11 or later.
- **Small, testable modules** — Each module must be independently testable in isolation.
- **Pure functions where possible** — Prefer stateless functions with explicit inputs and outputs.
- **No side effects in imports** — Importing any module must not trigger I/O, network calls, or process launches.
- **Config-driven thresholds** — All thresholds and process lists must be sourced from `config/rules.yaml`. No magic numbers in code.
- **Deterministic watchdog loop** — The watchdog loop timing and decision logic must be predictable and free of race conditions.
- **Explicit, timestamped logging** — Every log entry must include an ISO 8601 timestamp and the originating module.

---

## Architectural Rules

- `gpu_monitor.py` handles **only** GPU queries (VRAM usage, GPU load, etc.).
- `system_monitor.py` handles **only** RAM and system-level queries.
- `process_rules.py` loads configuration from `config/rules.yaml` and exposes thresholds and process lists to other modules.
- `watchdog.py` orchestrates monitoring, evaluates rules, and triggers actions (e.g., process termination).
- `main.py` is the sole entry point; it initializes and starts the watchdog.
- **No module may import from `main.py`.**
- **No circular imports** are permitted under any circumstances.

---

## Agent Behavior Rules

When generating or modifying code in this project, Copilot must:

- Always read `docs/CODEX.md` before generating code.
- Always respect `config/rules.yaml` as the single source of truth for thresholds and process configuration.
- Never invent new processes, thresholds, or behaviors not present in the config or explicitly requested.
- Never modify existing documented sections unless explicitly instructed to do so.
- Append new codex entries instead of rewriting or deleting old ones.

---

## Bugfix Workflow Requirements

- Always follow the test-first workflow defined in `BUGFIX_WORKFLOW.md`.
- Never fix a bug without first creating a failing test.
- Always expand tests with edge cases after the fix.
- Always update `CODEX.md` with a new entry documenting:
  - The bug
  - The failing test
  - The fix
  - The expanded tests
  - The version bump
- Always run the full test suite before declaring the fix complete.
- Always bump the bugfix version number.
- Always push and sync to Git after a successful fix.

---

## Installer Lifecycle Rules

- All installer scripts must be idempotent.
- No script may leave orphan files.
- All registry writes must be explicit.
- PATH updates must avoid duplicates.
- All installer actions must be logged.
- All installer bugs must follow the test-first bugfix workflow.
- All installer tests must pass before version bump.

## Global Monitoring Rules

- Always classify processes before scheduling.
- Never suspend system processes.
- Always prioritize AI agents unless overridden.
- Always update charts in real time.
- Always maintain deterministic behavior.

## GUI Behavior Requirements

- Always implement responsive layouts.
- Always implement sortable table columns.
- Always ensure continuous graph rendering.
- Always bind resize events to redraw logic.
- Always maintain deterministic update intervals.

## CLI Parity Requirements

- All core GUI process actions must have CLI equivalents in `main.py`.
- GUI and CLI process controls must reuse the same underlying scheduler/process-control logic.
- Turn-taking enable and disable operations must be available from both GUI and CLI surfaces.

## Expanded Monitoring Requirements

- All filters must be functional, deterministic, and must not blank the table as placeholder behavior.
- CPU metrics must be normalized to realistic total-system percentages for display and reporting.
- `System Idle Process` must never be treated as a top CPU hog.
- Debug logging must exist at critical paths and previously regressed locations, including process discovery, classification, scheduler decisions, filter application, graph updates, and CLI command handling.

## Graph Rendering Requirements

- All graph panels (CPU, RAM, GPU, stacked pressure) must include horizontal gridlines at 25%, 50%, 75%, and 100% of panel height.
- All graph panels must include vertical time-tick lines at 10-second equivalent intervals.
- All graph panels must display a Y-axis title label and an X-axis "Time (seconds)" label.
- Gridlines and labels must redraw correctly on canvas resize events.

## Performance and Thread-Safety Requirements

- UI updates must never block the main Tkinter thread.
- Data collection (process scanning, classification, GPU queries) must be scheduled via `after()`.
- Sorting must complete in under 200 ms for up to 1000 process rows.
- Process stats must be cached between ticks; re-scans must never be triggered inline during sort or filter.

## CPU Normalization Requirements

- CPU% displayed in all tables and charts must be normalized by logical CPU count (`raw / cpu_count`).
- Normalized CPU% must be capped at 100%.
- `System Idle Process` must always display as 0% CPU and must never be returned as top CPU hog.

## AI Agent Classification Requirements

- AI-GPU threshold for classification is 200 MB (not 500 MB).
- Processes sustaining >25% CPU for >3 continuous seconds must be classified as AI agents.
- `python.exe` with LLM/agent cmdline hints and `node.exe` with copilot/agent hints are always AI agents.
- `ollama.exe` is always an AI agent regardless of resource usage.

## Selection Persistence Requirements

- `_selected_pid` must persist until `_clear_selection()` is called explicitly.
- Clicking empty table space must NOT clear selection.
- `_refresh_table` must restore the visual Treeview highlight on `_selected_pid` after every full redraw.
- Selection must only be replaced by a new process click or cleared by the Clear Selection button.
