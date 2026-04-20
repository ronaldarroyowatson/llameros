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
