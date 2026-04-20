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

## 8. Installer Lifecycle Architecture

### Install Flow

- Script: `installer/install.ps1`
- The installer first runs `installer/detect_previous_install.ps1` to classify existing state.
- If state is `none`, it performs a clean install into `Program Files\\Llameros` by default (or configured test override path).
- It copies application payload files, creates `bin\\llameros.cmd`, creates a Start Menu shortcut, registers PATH, and writes registry metadata.
- All actions are logged to `installer.log` with ISO 8601 UTC timestamps.

### Uninstall Flow

- Script: `installer/uninstall.ps1`
- Removes install directory contents, Start Menu entry, installer registry key, and PATH registration.
- Removes installer/runtime logs as part of directory cleanup and persistent state cleanup.
- If user data is present, removal is confirmed unless explicit removal flags are supplied.
- Uninstall is idempotent and safe to re-run without leaving orphan artifacts.

### Repair Flow

- Script: `installer/repair.ps1`
- Detects current install state and validates required artifacts (`src\\main.py`, `config\\rules.yaml`, `VERSION`, `bin\\llameros.cmd`).
- Restores missing artifacts from source payload, re-registers PATH, and re-registers registry metadata.
- Performs post-repair integrity validation by re-running previous-install detection.
- Logs each repair action and integrity result.

### Reinstall Flow

- Reinstall is performed by running `installer/install.ps1 -Reinstall`.
- Reinstall overwrites payload files, refreshes PATH registration without duplicates, and updates registry version metadata.
- Reinstall remains deterministic and idempotent for repeated runs.

### Previous-Install Detection

- Script: `installer/detect_previous_install.ps1`
- Detection checks:
  - Registry key presence and `InstallPath`
  - Install directory presence
  - Installed `VERSION` file presence
- Return values are strict and machine-parseable:
  - `none`
  - `installed`
  - `corrupted`

### Registry Schema

- Base key: `HKCU\\Software\\Llameros`
- Values:
  - `InstallPath` (string)
  - `Version` (string)
  - `InstallDate` (ISO 8601 UTC string)
- Registry writes are explicit and avoid overwrite unless reinstall/repair mode is active.

### PATH Rules

- PATH registration targets `Llameros\\bin`.
- Registration avoids duplicate entries and normalizes trailing separators.
- Session PATH and persistent PATH are both updated.
- PATH values are persisted without trailing semicolons.

### Logging Rules

- Installer lifecycle scripts write actions to `installer.log`.
- Log entries use ISO 8601 UTC timestamps, script module context, and level labels.
- Failures are surfaced explicitly with error-level log entries.

### Test Suite Structure

- Installer tests live under `tests/installer/` and cover:
  - Clean install
  - Clean uninstall
  - Repair
  - Reinstall
  - Previous-install detection
  - Version bump on reinstall
- Tests use a sandboxed install root, sandboxed Start Menu root, test-scoped registry keys, and a test-scoped persistent PATH store.

### 8.x Installer Bugfix Log Entries

Each installer bugfix will append a new entry here.

### [2026-04-19] — Added installer lifecycle architecture codex entries

Appended installer lifecycle architecture covering install, uninstall, repair, reinstall, previous-install detection, registry schema, PATH handling, logging requirements, and the dedicated installer test suite structure.

## 9. Global Process View Architecture

- The GUI now supports a full global process table sourced from `psutil.process_iter()` and enriched with GPU memory from `nvidia-smi`.
- Table columns include PID, process name, CPU%, RAM MB, GPU MB, status, priority, and classification.
- The view supports deterministic sorting by any column and filter toggles for AI agents, heavy hitters, and monitored-only rows.
- The GUI provides real-time chart panels for CPU, RAM, and GPU VRAM trends, plus a selected-process trend panel and stacked resource-pressure view.
- Heavy hitter detection uses reproducible thresholds derived from `config/rules.yaml` limits and explicit GPU AI-agent criteria.

## 10. AI Agent Awareness

- AI agents are detected using executable and runtime signals:
  - `ollama.exe`
  - `python.exe` with LLM/agent-oriented command-line hints
  - `node.exe` with Copilot/agent command-line hints
  - Any process consuming more than 500 MB GPU VRAM
- AI agents receive highest default scheduler priority (10) unless an operator override is applied.
- AI agents are considered turn-taking eligible unless manually paused or currently throttled by resource controls.

## 11. Scheduler Integration with Classification

- Scheduler metadata tracks classification for each monitored PID and updates it during process synchronization.
- Eligibility rules:
  - AI agents: eligible
  - Editors: not eligible
  - VMs: eligible
  - System processes: never eligible
  - Background services: not eligible
- Priority defaults:
  - AI agents: 10
  - Editors: 5
  - VMs: 8
  - Background services: 1
- Time-slice logic scales from the configured base quantum using priority so higher-priority eligible processes receive longer slices deterministically.

### [2026-04-19] — Added global process view, AI awareness, and classification scheduler codex entries

Appended sections documenting the global process table, real-time charting model, automatic process classification, AI-agent prioritization, and scheduler eligibility/time-slice behavior wired to process class metadata.

### [2026-04-19] — Classification-safe scheduling bugfix workflow execution

Bug: scheduler and watchdog operations could act on non-eligible process classes (especially system/editor/background contexts) without explicit class-aware guards, and global process visibility/classification behavior lacked regression protection. Failing tests: added deterministic tests `tests/scheduler/test_turn_taking_with_classification.py` and `tests/process_utils/test_classification_rules.py` to reproduce class eligibility and classification-rule failures against pre-fix behavior. Fix: added explicit classification APIs in `process_utils.py`, class-aware scheduling eligibility and system-process safeguards in `scheduler.py`/`watchdog.py`, and GUI/global-process logic that consumes these deterministic classifications. Expanded tests: added GUI coverage (`tests/gui/test_global_process_view.py`, `tests/gui/test_charts_render.py`, `tests/gui/test_classification_display.py`), scheduler defaults/priority coverage (`tests/scheduler/test_priority_defaults.py`, `tests/scheduler/test_ai_agent_priority.py`), and AI detection coverage (`tests/process_utils/test_ai_agent_detection.py`). Version bump: `1.0.1` -> `1.0.2`.

## 12. GUI Rendering and Interaction Rules

- Graphs must update continuously at a fixed interval.
- Graphs must never show gaps between data points.
- All GUI elements must resize responsively.
- All table columns must be sortable.
- Sorting must toggle ascending/descending.
- Layout must use weighted grid geometry.
- Canvas must redraw on resize events.

### [2026-04-19] — GUI continuous render, responsive layout, and sortable columns bugfix workflow execution

Bug: chart rendering cadence was coupled to slower data refresh timing, resulting in visual gaps/black segments; root layout sections were not fully responsive during window resize; and table header sorting behavior did not enforce deterministic per-column toggle state for all displayed columns. Failing tests: added `tests/gui/test_graph_continuous_render.py`, `tests/gui/test_responsive_layout.py`, and `tests/gui/test_sortable_columns.py` to reproduce fixed-interval redraw, resize-responsiveness, and column sort toggle/type behavior failures. Fix: implemented independent render ticks with rolling history extension from last-known samples, migrated major GUI sections to weighted `grid` with `sticky="nsew"`, bound resize events to chart redraw, and added generic per-column header click sorting for numeric and string fields. Expanded tests: retained existing GUI regression coverage and executed the complete GUI suite with the new targeted tests. Version bump: `1.0.2` -> `1.0.3`.

### GUI Rendering and Interaction Rules Addendum

- The stacked resource pressure graph uses the same fixed render cadence and history-extension behavior as the CPU, RAM, and GPU charts so no sample gaps appear between refreshes.
- Stacked pressure rendering includes horizontal gridlines at 25% intervals, vertical time ticks at 10-second equivalents derived from render cadence, and explicit axis labels for resource pressure and elapsed time.
- Per-process selection is sticky runtime state: clicking empty space does not clear it, selecting another process replaces it, and only an explicit clear action removes the selection and its per-process trend view.
- Filter controls must apply deterministic subsets without blanking the table as placeholder behavior.

## 13. Global Monitoring Rules

- Process CPU percentages shown in the GUI and process tables are normalized by logical CPU count so displayed values remain realistic on multi-core systems.
- `System Idle Process` is excluded from top-CPU-hog reporting so idle capacity is never surfaced as an actionable hog.
- Filter semantics are deterministic and composable for AI-agent, heavy-hitter, and monitored-only views.

### AI Agent Awareness Addendum

- AI-like Python workloads identified through agent/LLM command-line hints remain fully controllable through pause, resume, kill, priority, and background/foreground operations.
- AI-agent visibility and operator controls are available through both GUI actions and CLI commands backed by the same scheduler control surface.

### Scheduler Integration Addendum

- Turn-taking mode is a scheduler control only and must never act as a table filter or blank the visible process list.
- Scheduler metadata tracks explicit background/foreground state transitions and exposes them consistently to GUI and CLI control flows.
- Structured debug logging is emitted for scheduler decisions, process discovery, classification, filter application, graph rendering, and CLI command handling when debug mode is enabled.

### [2026-04-19] — GUI control parity, stacked pressure, logging, and CPU normalization bugfix workflow execution

Bug: the stacked pressure graph rendered staggered/gapped segments without axes, process-row selection was cleared by non-selection clicks, filter toggles lacked complete deterministic semantics, GUI-only controls had no CLI parity, debug logging coverage was sparse on known bug paths, and raw multi-core CPU percentages could surface `System Idle Process` as an impossible hog. Failing tests: added `tests/gui/test_stacked_pressure_continuous.py`, `tests/gui/test_stacked_pressure_grid_and_labels.py`, `tests/gui/test_process_selection_persistence.py`, `tests/gui/test_filters_ai_agents.py`, `tests/gui/test_filters_heavy_hitters.py`, `tests/gui/test_filters_monitored_processes.py`, `tests/cli/test_cli_process_control.py`, `tests/logging/test_debug_logging_paths.py`, `tests/system/test_cpu_usage_normalization.py`, and `tests/integration/test_ai_process_control.py` to reproduce the GUI, CLI, logging, classification, and control-path failures. Fix: unified stacked-pressure rendering with the continuous chart loop, made selection explicit-clear only, implemented shared deterministic process filtering, added scheduler-backed CLI process controls and debug logging configuration, normalized displayed CPU percentages, excluded idle capacity from hog reporting, and preserved raw CPU heuristics only where needed for classification. Expanded tests: executed the complete repository suite including GUI, integration, smoke, live, installer, and process/scheduler coverage after the targeted regressions. Version bump: `1.0.3` -> `1.0.4`.

## 13. Gridline and Axis Label Standards

- Every graph panel (`_draw_line`) must render horizontal gridlines at 0%, 25%, 50%, 75%, and 100% of panel height.
- Every graph panel must render vertical time ticks at 10-second equivalent intervals derived from `_render_interval_ms` (every `round(10000 / render_interval_ms)` samples).
- Every graph panel must display a Y-axis title label (e.g., "CPU Usage (%)", "RAM Usage (MB)", "VRAM Usage (MB)").
- Every graph panel must display an X-axis label "Time (seconds)" along the bottom edge.
- The stacked resource pressure graph also includes these gridlines and axis labels.
- All gridlines and labels must redraw correctly on canvas resize events.

## 14. Performance and Threading Rules

- Data collection (process scanning, GPU queries, classification) runs in the Tkinter `after()` loop and must NOT block the main thread beyond the scheduled tick interval.
- The render interval is 200 ms; the data refresh interval is 1000 ms. These are decoupled: rendering can happen without new data using last-known samples.
- Sorting is performed in-process on cached row data and must complete in under 200 ms for up to 1000 rows.
- Process stats are cached between data ticks; heavy re-scans are never triggered inline during sort or filter operations.
- Thread-safety: all Tkinter widget updates must occur on the main thread via `after()` callbacks.

## 15. CPU Normalization Rules

- `normalize_cpu_percent(raw, cpu_count)` divides psutil's per-process CPU reading (which is relative to one core) by the logical CPU count so values are bounded to [0%, 100%] system-relative.
- The `System Idle Process` (and any process whose name matches `_IDLE_PROCESS_NAMES`) must always display as 0% CPU and must never be reported as a top-CPU-hog.
- The normalization is applied before storage in process rows and before any display or threshold comparison.
- Raw (un-normalized) CPU is used only for internal classification heuristics where per-core granularity is meaningful.

## 16. AI Agent Classification Rules

- AI agents are detected using the following signals (any signal triggers "ai agent" classification):
  - Executable name matches `_AI_EXECUTABLES` (e.g., `ollama.exe`).
  - `python.exe` with command-line tokens matching any key in `_AI_CMDLINE_HINTS` (llm, llama, vllm, transformers, openai, copilot, agent, ollama).
  - `node.exe` with "copilot" or "agent" in command-line tokens.
  - GPU memory usage ≥ `AI_GPU_MB_THRESHOLD` (200 MB).
  - CPU usage > `AI_CPU_THRESHOLD` (25%) sustained continuously for ≥ `AI_CPU_SUSTAINED_SECONDS` (3 seconds), tracked in `_sustained_cpu_start` module-level dict.
- Sustained CPU tracking is maintained in the `_sustained_cpu_start` dict keyed by PID; stale entries are evicted when CPU drops below threshold.
- Classification is performed in `_classify_from_snapshot`; all callers (`get_global_process_rows`, `classify_process`, `get_process_stats`) feed through this function.

## 17. Filter Behavior Rules

- All filter controls (`only_ai`, `only_heavy`, `only_monitored`) apply deterministically and are composable.
- No filter combination may return an empty table as placeholder behavior when matching rows exist.
- Filter logic lives exclusively in `process_utils.filter_process_rows`; GUI merely passes the active flags.
- The AI filter returns all rows with `classification == "ai agent"` and must not return empty when AI-classified processes are present.

## 18. Selection Persistence Rules

- `_selected_pid` is sticky runtime state and may only be cleared by an explicit `_clear_selection()` call.
- Clicking empty table space (Treeview fires `<<TreeviewSelect>>` with empty selection) must NOT clear `_selected_pid`.
- `_refresh_table` must restore the visual Treeview highlight on the selected row after every full delete/re-insert cycle.
- The per-process trend chart remains visible as long as `_selected_pid` is set; it is cleared only after `_clear_selection()`.

### [2026-04-19] — Gridlines, AI thresholds, CPU normalization, selection persistence, and performance bugfix workflow execution

Bug: CPU/RAM/GPU graph panels lacked horizontal gridlines and X-axis labels; AI-agent detection threshold was 500 MB (too high, masking LLM workloads using 200–499 MB VRAM); sustained-CPU-based AI classification was unimplemented; System Idle Process displayed 100% normalized CPU instead of 0%; `_refresh_table` did not restore visual selection after full redraw; and sort/filter latency was unvalidated. Failing tests: `tests/gui/test_graph_gridlines_all.py`, `tests/gui/test_graph_axis_labels.py`, `tests/gui/test_stacked_pressure_continuous_render.py`, `tests/gui/test_filter_ai_agents.py`, `tests/system/test_cpu_normalization.py`, `tests/performance/test_sort_latency.py`, `tests/performance/test_ui_responsiveness.py`, `tests/gui/test_selection_persistence.py`. Fix: added gridlines (25%/50%/75%/100%) and "Time (seconds)" X-axis label to `_draw_line`; lowered `AI_GPU_MB_THRESHOLD` to 200 MB; added `_sustained_cpu_start` dict and sustained-CPU AI-agent detection logic in `_classify_from_snapshot`; zeroed idle-process CPU in `get_global_process_rows`; added `selection_set()` restore call in `_refresh_table`. Version bump: `1.0.4` -> `1.0.5`.
