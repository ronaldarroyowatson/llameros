# Llameros Codex

This codex is the authoritative reference for the architecture, design intent, rules, and evolving knowledge of the Llameros project. Copilot must read this file before generating code.

---

## 1. Project Overview

Llameros is a lightweight GPU/RAM watchdog designed to prevent out-of-memory (OOM) crashes on workstations running large language models or other memory-intensive workloads. It continuously monitors VRAM usage, system RAM, and a configurable list of key processes. When thresholds are exceeded, it takes targeted corrective action — such as killing lower-priority processes — to keep the system stable and responsive.

Key goals:

- Prevent OOM crashes before they occur
- Operate silently in the background with minimal overhead
- Remain fully configurable via `config/rules.yaml`
- Produce clear, timestamped logs for post-hoc diagnosis

---

## 2. Architecture Summary

| Module | Responsibility |
| --- | --- |
| `gpu_monitor.py` | Queries GPU VRAM usage and GPU load metrics |
| `system_monitor.py` | Queries system RAM usage and related OS-level metrics |
| `process_rules.py` | Loads `config/rules.yaml` and exposes thresholds, process kill lists, and rule logic |
| `watchdog.py` | Orchestrates the monitoring loop; evaluates rules and dispatches actions |
| `main.py` | Entry point; initializes all modules and starts the watchdog loop |

**Dependency direction:** `main.py` → `watchdog.py` → `gpu_monitor.py`, `system_monitor.py`, `process_rules.py`

No module imports from `main.py`. No circular imports.

---

## 3. Monitoring Rules

### VRAM Threshold Behavior

- When VRAM usage exceeds the configured `vram_threshold_percent`, the watchdog enters alert mode.
- In alert mode, it evaluates the `kill_order` list from `rules.yaml` and terminates processes in priority order until VRAM drops below the threshold.
- A cooldown period (configurable) must elapse before the next kill action.

### RAM Threshold Behavior

- When system RAM usage exceeds `ram_threshold_percent`, the same kill-order logic applies.
- VRAM and RAM alerts are evaluated independently but logged together.

### Process Kill Order

- The kill order is defined in `config/rules.yaml` under the `kill_order` key.
- Processes are terminated in list order (index 0 = first to kill).
- The watchdog must verify the process is running before attempting termination.
- A failed kill attempt must be logged and must not halt the watchdog loop.

### Logging Requirements

- All threshold breaches must be logged at `WARNING` level.
- All kill actions must be logged at `WARNING` level with the process name, PID, and reason.
- All errors must be logged at `ERROR` level with full exception context.
- Log entries must include ISO 8601 timestamps and the originating module name.

---

## 4. Reproducibility Rules

- **No randomness** — The watchdog must behave identically given identical system state and config.
- **No external dependencies beyond `requirements.txt`** — All runtime dependencies must be pinned and declared.
- **Config is the single source of truth** — All thresholds, process names, intervals, and cooldowns must come from `config/rules.yaml`. No hardcoded values in source code.
- **Deterministic, timestamped logs** — Log output must be machine-parseable and reproducible for the same sequence of events.

---

## 5. Expansion Hooks

The following capabilities are planned but not yet implemented. New codex entries should be appended here as each is designed or built.

- **Auto-restart logic** — Automatically restart a terminated process after a configurable recovery window.
- **Windows service integration** — Run Llameros as a persistent Windows service with proper start/stop/restart lifecycle management.
- **Tray icon integration** — Provide a system tray icon showing current VRAM/RAM status and allowing manual pause/resume.
- **Spike detection** — Detect rapid, short-duration memory spikes and trigger preemptive action before thresholds are crossed.
- **Per-process thresholds** — Allow individual VRAM/RAM limits to be set per process in `rules.yaml`.
- **Multi-GPU support** — Monitor and act on multiple GPUs independently, with per-GPU threshold configuration.

---

## 6. Codex Update Protocol

This codex is an append-only living document. The following rules govern all updates:

- **New sections must be appended** at the end of the relevant section or as a new top-level section. Existing content must not be rewritten or removed.
- **Each update must include a timestamp and a short description** of what was added or changed (see format below).
- **Copilot must never delete or modify previous codex entries** unless the user explicitly provides that instruction with clear justification.
- Breaking these rules degrades the traceability and trustworthiness of the project record.

### Update Log Format

```text
### [YYYY-MM-DD] — <Short description of change>
<One to three sentences describing what was added, why, and any relevant constraints.>
```

---

### [2026-04-19] — Initial codex creation

Established the foundational codex for the Llameros project, covering project overview, architecture, monitoring rules, reproducibility requirements, expansion hooks, and the codex update protocol.

## 7. GUI and Scheduler Extension

### GUI Architecture

- Module: `src/llameros/gui.py`
- UI stack: Tkinter + ttk
- The GUI reads live process state from the scheduler and process utilities and presents:
  - Top CPU hog process
  - Top RAM hog process
  - Top GPU hog process
  - Any process that is simultaneously the top CPU, RAM, and GPU hog among monitored processes
- A monitored-process table includes CPU%, RAM MB, GPU MB, status, and priority, with process identity (PID and name) for deterministic operator actions.
- Operator controls: Pause, Resume, Kill, Set Priority, Set Background, and Turn-taking mode toggle.

### Scheduler Rules

- Module: `src/llameros/scheduler.py`
- The scheduler maintains a live monitored-process registry from configured process names in `config/rules.yaml`.
- Priority levels are integer values from 1 to 10 and influence turn-taking candidate ordering.
- Resource-aware behavior:
  - If VRAM usage is above `vram_limit_mb`, the scheduler suspends the highest GPU-memory monitored process.
  - If RAM usage is above `ram_limit_mb`, the scheduler suspends the highest RAM monitored process.
  - If CPU usage is above `cpu_limit_percent` (when configured), the scheduler suspends the highest CPU monitored process.
- When pressure subsides, scheduler-throttled processes are resumed unless they were manually paused.

### Turn-taking Algorithm

- Turn-taking mode is an explicit boolean runtime control exposed in the GUI.
- When enabled, eligible monitored processes are sorted by priority (descending) and PID (ascending) for deterministic order.
- Each selected process receives a fixed execution quantum (`turn_quantum_seconds`) and is then suspended.
- The scheduler resumes the next process in round-robin order and repeats continuously.
- Manual pauses and resource-throttled processes are excluded from active turn-taking slots.

### Process Priority System

- Priority is scheduler-local metadata persisted in memory for active monitored PIDs.
- Default priority for newly discovered monitored processes is level 5.
- Higher priority increases scheduling preference but does not bypass safety controls (manual pause, resource throttling).
- Background flag is tracked as explicit process metadata for future policy extensions.

### [2026-04-19] — Added GUI and turn-taking scheduler codex entries

Appended architecture and behavior documentation for the Tkinter GUI, round-robin turn-taking scheduler, resource-aware suspension policy, and the in-memory process priority model used by monitored processes.

## 7. Bugfix Workflow (Permanent Rules)

This project uses a strict test-first bugfix methodology:

- A failing test must be created before any fix.
- The test must fail for the correct reason.
- The fix must be minimal and targeted.
- The test must pass after the fix.
- Additional edge-case tests must be added.
- All tests must be added to the permanent suite.
- The full suite must pass before version bump.
- Version bump increments the bugfix number.
- All changes must be committed and synced.

### 7.x Bugfix Log Entries

Each bugfix will append a new entry here.

### [2026-04-19] — Cleared problems pane and fixed GUI tree scrolling keyword

Bug: `Treeview.configure` used `yscroll` instead of `yscrollcommand`, and docs formatting issues generated deterministic Problems pane noise. Failing test: `tests/unit/test_bugfix_regressions.py` initially failed on GUI keyword and markdown hygiene checks. Fix: replaced `yscroll` with `yscrollcommand`, reformatted codex/workflow markdown to resolve lint violations, and expanded regression assertions for docs and codex code-fence language. Version bump: `1.0.0` -> `1.0.1`.
