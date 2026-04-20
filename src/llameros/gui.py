"""gui.py - Tkinter interface for Llameros process monitoring and controls."""
from __future__ import annotations

from collections import deque
import logging
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import psutil

from . import process_utils
from .gpu_monitor import get_gpu_memory
from .system_monitor import get_ram_usage
from .scheduler import TurnTakingScheduler

LOGGER = logging.getLogger(__name__)


class LlamerosGUI:
    """Desktop control panel for scheduler state and process actions."""

    def __init__(self, scheduler: TurnTakingScheduler):
        self._scheduler = scheduler
        self._rules = self._scheduler.get_rules()
        self._root = tk.Tk()
        self._root.title("Llameros Control Panel")
        self._root.geometry("1280x900")

        self._turn_taking_var = tk.BooleanVar(value=self._scheduler.get_turn_taking_mode())
        self._show_all_processes_var = tk.BooleanVar(value=True)
        self._only_ai_var = tk.BooleanVar(value=False)
        self._only_heavy_var = tk.BooleanVar(value=False)
        self._only_monitored_var = tk.BooleanVar(value=False)

        self._top_cpu_var = tk.StringVar(value="Top CPU hog: n/a")
        self._top_ram_var = tk.StringVar(value="Top RAM hog: n/a")
        self._top_gpu_var = tk.StringVar(value="Top GPU hog: n/a")
        self._triple_hog_var = tk.StringVar(value="Hogging all three: n/a")

        self._sort_column = "priority"
        self._sort_reverse = True
        self._sort_states: dict[str, bool] = {}
        self._column_sort_key = {
            "pid": "pid",
            "name": "name",
            "cpu": "cpu_percent",
            "ram": "ram_mb",
            "gpu": "gpu_mb",
            "status": "status",
            "priority": "priority",
            "classification": "classification",
        }
        self._selected_pid: int | None = None

        self._max_history = 90
        self._cpu_history: deque[float] = deque(maxlen=self._max_history)
        self._ram_history: deque[float] = deque(maxlen=self._max_history)
        self._gpu_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_cpu_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_ram_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_gpu_history: deque[float] = deque(maxlen=self._max_history)
        self._last_visible_rows: list[dict] = []
        self._last_global_rows: list[dict] = []
        self._last_monitored_rows: list[dict] = []
        self._last_system_sample: dict[str, float] | None = None
        self._last_selected_sample: dict[str, float] | None = None

        self._data_refresh_ms = 1000
        self._render_interval_ms = 200

        self._build_layout()
        self._configure_root_grid_weights()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.bind("<Configure>", self._on_resize)

    def run(self) -> None:
        self._data_tick()
        self._schedule_render_tick()
        self._root.mainloop()

    def _build_layout(self) -> None:
        top_frame = ttk.Frame(self._root, padding=12)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(0, weight=1)

        ttk.Label(top_frame, textvariable=self._top_cpu_var).grid(row=0, column=0, sticky="w")
        ttk.Label(top_frame, textvariable=self._top_ram_var).grid(row=1, column=0, sticky="w")
        ttk.Label(top_frame, textvariable=self._top_gpu_var).grid(row=2, column=0, sticky="w")
        ttk.Label(top_frame, textvariable=self._triple_hog_var).grid(row=3, column=0, sticky="w")

        toggle_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        toggle_frame.grid(row=1, column=0, sticky="ew")
        ttk.Checkbutton(
            toggle_frame,
            text="Turn-taking mode",
            variable=self._turn_taking_var,
            command=self._toggle_turn_taking,
        ).grid(row=0, column=0, padx=4, sticky="w")
        ttk.Checkbutton(
            toggle_frame,
            text="Show all processes",
            variable=self._show_all_processes_var,
            command=self._refresh_visible_view,
        ).grid(row=0, column=1, padx=4, sticky="w")
        ttk.Checkbutton(
            toggle_frame,
            text="Show only AI agents",
            variable=self._only_ai_var,
            command=self._refresh_visible_view,
        ).grid(row=0, column=2, padx=4, sticky="w")
        ttk.Checkbutton(
            toggle_frame,
            text="Show only heavy hitters",
            variable=self._only_heavy_var,
            command=self._refresh_visible_view,
        ).grid(row=0, column=3, padx=4, sticky="w")
        ttk.Checkbutton(
            toggle_frame,
            text="Show only monitored processes",
            variable=self._only_monitored_var,
            command=self._refresh_visible_view,
        ).grid(row=0, column=4, padx=4, sticky="w")
        toggle_frame.columnconfigure(5, weight=1)

        table_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = (
            "pid",
            "name",
            "cpu",
            "ram",
            "gpu",
            "status",
            "priority",
            "classification",
        )
        self._tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        self._tree.heading("pid", text="PID", command=lambda: self._on_heading_click("pid"))
        self._tree.heading("name", text="Process", command=lambda: self._on_heading_click("name"))
        self._tree.heading("cpu", text="CPU%", command=lambda: self._on_heading_click("cpu_percent"))
        self._tree.heading("ram", text="RAM MB", command=lambda: self._on_heading_click("ram_mb"))
        self._tree.heading("gpu", text="GPU MB", command=lambda: self._on_heading_click("gpu_mb"))
        self._tree.heading("status", text="Status", command=lambda: self._on_heading_click("status"))
        self._tree.heading("priority", text="Priority", command=lambda: self._on_heading_click("priority"))
        self._tree.heading(
            "classification",
            text="Classification",
            command=lambda: self._on_heading_click("classification"),
        )

        self._tree.column("pid", width=80, anchor=tk.CENTER)
        self._tree.column("name", width=200)
        self._tree.column("cpu", width=100, anchor=tk.E)
        self._tree.column("ram", width=120, anchor=tk.E)
        self._tree.column("gpu", width=120, anchor=tk.E)
        self._tree.column("status", width=120, anchor=tk.CENTER)
        self._tree.column("priority", width=100, anchor=tk.CENTER)
        self._tree.column("classification", width=180, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)
        self._tree.bind("<<TreeviewSelect>>", self._on_row_selected)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")

        charts_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        charts_frame.grid(row=3, column=0, sticky="nsew")
        charts_frame.rowconfigure(0, weight=3)
        charts_frame.rowconfigure(1, weight=2)
        charts_frame.columnconfigure(0, weight=1)

        self._system_canvas = tk.Canvas(charts_frame, height=300, bg="#101318", highlightthickness=0)
        self._system_canvas.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self._process_canvas = tk.Canvas(charts_frame, height=180, bg="#101318", highlightthickness=0)
        self._process_canvas.grid(row=1, column=0, sticky="nsew")
        self._system_canvas.bind("<Configure>", self._on_resize)
        self._process_canvas.bind("<Configure>", self._on_resize)

        button_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        button_frame.grid(row=4, column=0, sticky="nsew")

        ttk.Button(button_frame, text="Pause", command=self._pause_selected).grid(row=0, column=0, padx=4, sticky="ew")
        ttk.Button(button_frame, text="Resume", command=self._resume_selected).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(button_frame, text="Kill", command=self._kill_selected).grid(row=0, column=2, padx=4, sticky="ew")
        ttk.Button(button_frame, text="Set Priority", command=self._set_priority_selected).grid(
            row=0, column=3, padx=4, sticky="ew"
        )
        ttk.Button(button_frame, text="Set Background", command=self._set_background_selected).grid(
            row=0, column=4, padx=4, sticky="ew"
        )
        ttk.Button(button_frame, text="Clear Selection", command=self._clear_selection).grid(
            row=0, column=5, padx=4, sticky="ew"
        )
        for idx in range(6):
            button_frame.columnconfigure(idx, weight=1)

        self._grid_major_sections(table_frame, charts_frame, button_frame)

    def _configure_root_grid_weights(self) -> None:
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=0)
        self._root.rowconfigure(1, weight=0)
        self._root.rowconfigure(2, weight=3)
        self._root.rowconfigure(3, weight=2)
        self._root.rowconfigure(4, weight=0)

    @staticmethod
    def _grid_major_sections(table_frame: ttk.Frame, charts_frame: ttk.Frame, button_frame: ttk.Frame) -> None:
        table_frame.grid(sticky="nsew")
        charts_frame.grid(sticky="nsew")
        button_frame.grid(sticky="nsew")

    def _on_resize(self, event: tk.Event | None = None) -> None:
        del event
        self._draw_charts(getattr(self, "_last_visible_rows", []))

    def _toggle_turn_taking(self) -> None:
        self._scheduler.set_turn_taking_mode(self._turn_taking_var.get())
        LOGGER.debug("action=filter turn_taking_enabled=%s", self._turn_taking_var.get())

    def _on_row_selected(self, event: tk.Event | None) -> None:
        del event
        selected = self._tree.selection()
        if not selected:
            return
        values = self._tree.item(selected[0], "values")
        if not values:
            return
        self._selected_pid = int(values[0])
        LOGGER.debug("action=selection pid=%s", self._selected_pid)

    def _clear_selection(self) -> None:
        self._selected_pid = None
        self._last_selected_sample = None
        self._selected_cpu_history.clear()
        self._selected_ram_history.clear()
        self._selected_gpu_history.clear()
        if hasattr(self, "_tree") and hasattr(self._tree, "selection_remove"):
            self._tree.selection_remove(*self._tree.selection())
        LOGGER.debug("action=selection cleared=true")

    def _selected_pid_value(self) -> int | None:
        return self._selected_pid

    def _pause_selected(self) -> None:
        pid = self._selected_pid_value()
        if pid is None:
            return
        self._scheduler.pause(pid)

    def _resume_selected(self) -> None:
        pid = self._selected_pid_value()
        if pid is None:
            return
        self._scheduler.resume(pid)

    def _kill_selected(self) -> None:
        pid = self._selected_pid_value()
        if pid is None:
            return
        if messagebox.askyesno("Confirm Kill", f"Kill PID {pid}?"):
            self._scheduler.kill(pid)

    def _set_priority_selected(self) -> None:
        pid = self._selected_pid_value()
        if pid is None:
            return
        level = simpledialog.askinteger(
            "Set Priority",
            "Enter priority level (1-10):",
            minvalue=1,
            maxvalue=10,
            parent=self._root,
        )
        if level is None:
            return
        self._scheduler.set_priority(pid, level)

    def _set_background_selected(self) -> None:
        pid = self._selected_pid_value()
        if pid is None:
            return
        self._scheduler.set_background(pid, enabled=True)

    def _find_selected_row(self, visible_rows: list[dict]) -> dict | None:
        if self._selected_pid is None:
            return None

        for row in visible_rows:
            if int(row["pid"]) == self._selected_pid:
                return row

        for row in getattr(self, "_last_global_rows", []):
            if int(row["pid"]) == self._selected_pid:
                return row

        return process_utils.get_process_stats(self._selected_pid)

    def _refresh_hogs(self, rows: list[dict]) -> None:
        top_cpu = process_utils.get_top_cpu_process()
        top_ram = process_utils.get_top_ram_process()
        top_gpu = process_utils.get_top_gpu_process()

        self._top_cpu_var.set(
            f"Top CPU hog: {self._format_top(top_cpu, 'cpu_percent', '%')}"
        )
        self._top_ram_var.set(
            f"Top RAM hog: {self._format_top(top_ram, 'ram_mb', ' MB')}"
        )
        self._top_gpu_var.set(
            f"Top GPU hog: {self._format_top(top_gpu, 'gpu_mb', ' MB')}"
        )

        if not rows:
            self._triple_hog_var.set("Hogging all three: n/a")
            return

        by_cpu = max(rows, key=lambda row: row["cpu_percent"])
        by_ram = max(rows, key=lambda row: row["ram_mb"])
        by_gpu = max(rows, key=lambda row: row["gpu_mb"])
        if by_cpu["pid"] == by_ram["pid"] == by_gpu["pid"]:
            self._triple_hog_var.set(
                f"Hogging all three: {by_cpu['name']} (PID {by_cpu['pid']})"
            )
        else:
            self._triple_hog_var.set("Hogging all three: none")

    @staticmethod
    def _format_top(item: dict | None, metric_key: str, suffix: str) -> str:
        if not item:
            return "n/a"
        value = float(item.get(metric_key, 0.0))
        return f"{item.get('name', 'unknown')} (PID {item.get('pid')}) - {value:.1f}{suffix}"

    def _on_heading_click(self, column: str) -> None:
        if not hasattr(self, "_sort_states"):
            self._sort_states = {}
        if column not in self._sort_states:
            self._sort_states[column] = False
        else:
            self._sort_states[column] = not self._sort_states[column]
        self._sort_column = column
        self._sort_reverse = self._sort_states[column]

    def _sorted_rows(self, rows: list[dict]) -> list[dict]:
        values = [row.get(self._sort_column) for row in rows if row.get(self._sort_column) is not None]
        is_numeric = bool(values) and all(isinstance(value, (int, float)) for value in values)

        def _key(item: dict) -> float | str:
            value = item.get(self._sort_column)
            if is_numeric:
                return float(value)
            return str(value or "").lower()

        return sorted(rows, key=_key, reverse=self._sort_reverse)

    def _visible_rows(self, global_rows: list[dict], monitored_rows: list[dict]) -> list[dict]:
        rows = list(global_rows) if self._show_all_processes_var.get() else list(monitored_rows)
        return process_utils.filter_process_rows(
            rows,
            rules=self._rules,
            only_ai=self._only_ai_var.get(),
            only_heavy=self._only_heavy_var.get(),
            only_monitored=self._only_monitored_var.get(),
        )

    def _refresh_table(self, rows: list[dict]) -> None:
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        for row in self._sorted_rows(rows):
            row_id = self._tree.insert(
                "",
                tk.END,
                values=(
                    row["pid"],
                    row["name"],
                    f"{row['cpu_percent']:.1f}",
                    f"{row['ram_mb']:.1f}",
                    f"{row['gpu_mb']:.1f}",
                    row["status"],
                    row.get("priority", 0),
                    row.get("classification", "user"),
                ),
            )
            if getattr(self, "_selected_pid", None) is not None and int(row["pid"]) == self._selected_pid:
                self._tree.selection_set(row_id)

    def _draw_line(
        self,
        canvas: tk.Canvas,
        values: list[float],
        x: float,
        y: float,
        w: float,
        h: float,
        max_value: float,
        color: str,
        label: str,
    ) -> None:
        canvas.create_rectangle(x, y, x + w, y + h, outline="#2d3440")
        canvas.create_text(x + 8, y + 10, text=label, anchor=tk.W, fill="#d6deeb", font=("Segoe UI", 9))
        canvas.create_text(
            x + w / 2,
            y + h - 4,
            text="Time (seconds)",
            anchor=tk.CENTER,
            fill="#9fb0c0",
            font=("Segoe UI", 8),
        )

        for pct in (25, 50, 75, 100):
            py = y + h - (pct / 100.0) * h
            canvas.create_line(x, py, x + w, py, fill="#24303b", dash=(2, 4))
            canvas.create_text(x + w - 4, py - 2, text=str(pct), anchor=tk.E, fill="#738496")

        if values:
            span = max(1, len(values) - 1)
            samples_per_tick = max(
                1, int(round(10000 / max(1, getattr(self, "_render_interval_ms", 200))))
            )
            for index in range(samples_per_tick, len(values), samples_per_tick):
                px = x + (index / span) * w
                canvas.create_line(px, y, px, y + h, fill="#24303b", dash=(2, 4))
                seconds = int(
                    round((index * getattr(self, "_render_interval_ms", 200)) / 1000.0)
                )
                canvas.create_text(
                    px, y + h - 14, text=str(seconds), anchor=tk.CENTER, fill="#738496"
                )

        if not values:
            return

        clamped_max = max(1.0, max_value)
        points: list[float] = []
        span = max(1, len(values) - 1)
        for index, value in enumerate(values):
            px = x + (index / span) * w
            ratio = min(1.0, max(0.0, value / clamped_max))
            py = y + h - (ratio * h)
            points.extend((px, py))
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=2, smooth=True)

    def _draw_stacked_pressure(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        w: float,
        h: float,
    ) -> None:
        canvas.create_rectangle(x, y, x + w, y + h, outline="#2d3440")
        canvas.create_text(
            x + 8,
            y + 10,
            text="Stacked Resource Pressure",
            anchor=tk.W,
            fill="#d6deeb",
            font=("Segoe UI", 9),
        )
        canvas.create_text(x + 12, y + (h / 2), text="Resource Pressure (%)", anchor=tk.W, fill="#9fb0c0")
        canvas.create_text(x + (w / 2), y + h - 8, text="Time (seconds)", anchor=tk.CENTER, fill="#9fb0c0")

        for percent in (0, 25, 50, 75, 100):
            py = y + h - ((percent / 100.0) * h)
            canvas.create_line(x, py, x + w, py, fill="#24303b", dash=(2, 4))
            canvas.create_text(x + w - 4, py - 2, text=str(percent), anchor=tk.E, fill="#738496")

        if not self._cpu_history:
            return

        cpu_values = list(self._cpu_history)
        ram_values = list(self._ram_history)
        gpu_values = list(self._gpu_history)

        ram_max = max(1.0, max(ram_values))
        gpu_max = max(1.0, max(gpu_values))
        span = max(1, len(cpu_values) - 1)

        cpu_points: list[float] = []
        ram_points: list[float] = []
        total_points: list[float] = []
        samples_per_tick = max(1, int(round(10000 / max(1, getattr(self, "_render_interval_ms", 200)))))

        for index in range(len(cpu_values)):
            px = x + (index / span) * w
            cpu_pct = min(100.0, max(0.0, cpu_values[index]))
            ram_pct = min(100.0, max(0.0, (ram_values[index] / ram_max) * 100.0))
            gpu_pct = min(100.0, max(0.0, (gpu_values[index] / gpu_max) * 100.0))

            cpu_top = y + h - ((cpu_pct / 100.0) * h)
            ram_top = y + h - ((min(100.0, cpu_pct + ram_pct) / 100.0) * h)
            total_top = y + h - ((min(100.0, cpu_pct + ram_pct + gpu_pct) / 100.0) * h)

            cpu_points.extend((px, cpu_top))
            ram_points.extend((px, ram_top))
            total_points.extend((px, total_top))

            if index and index % samples_per_tick == 0:
                seconds = int(round((index * getattr(self, "_render_interval_ms", 200)) / 1000.0))
                canvas.create_line(px, y, px, y + h, fill="#24303b", dash=(2, 4))
                canvas.create_text(px, y + h - 20, text=str(seconds), anchor=tk.CENTER, fill="#738496")

        if len(cpu_points) >= 4:
            canvas.create_line(*cpu_points, fill="#ff6b6b", width=2, smooth=True)
        if len(ram_points) >= 4:
            canvas.create_line(*ram_points, fill="#4dabf7", width=2, smooth=True)
        if len(total_points) >= 4:
            canvas.create_line(*total_points, fill="#51cf66", width=2, smooth=True)

    def _draw_charts(self, visible_rows: list[dict]) -> None:
        if not hasattr(self, "_last_system_sample"):
            self._last_system_sample = None
        if not hasattr(self, "_last_selected_sample"):
            self._last_selected_sample = None
        if not hasattr(self, "_last_visible_rows"):
            self._last_visible_rows = []
        self._system_canvas.delete("all")
        self._process_canvas.delete("all")

        self._last_visible_rows = list(visible_rows)

        if self._last_system_sample is None:
            self._last_system_sample = {
                "cpu": float(psutil.cpu_percent(interval=0.0)),
                "ram": float(get_ram_usage()),
                "gpu": float(get_gpu_memory()),
            }
        if not self._cpu_history:
            self._cpu_history.append(self._last_system_sample["cpu"])
        if not self._ram_history:
            self._ram_history.append(self._last_system_sample["ram"])
        if not self._gpu_history:
            self._gpu_history.append(self._last_system_sample["gpu"])

        width = max(900, self._system_canvas.winfo_width())
        panel_w = (width - 24) / 2
        panel_h = 130

        self._draw_line(
            self._system_canvas,
            list(self._cpu_history),
            8,
            8,
            panel_w,
            panel_h,
            100.0,
            "#ff6b6b",
            "CPU Usage (%)",
        )
        self._draw_line(
            self._system_canvas,
            list(self._ram_history),
            16 + panel_w,
            8,
            panel_w,
            panel_h,
            max(1.0, max(self._ram_history) if self._ram_history else 1.0),
            "#4dabf7",
            "RAM Usage (MB)",
        )
        self._draw_line(
            self._system_canvas,
            list(self._gpu_history),
            8,
            156,
            panel_w,
            panel_h,
            max(1.0, max(self._gpu_history) if self._gpu_history else 1.0),
            "#51cf66",
            "GPU VRAM Usage (MB)",
        )
        self._draw_stacked_pressure(self._system_canvas, 16 + panel_w, 156, panel_w, panel_h)

        selected = self._find_selected_row(visible_rows)

        if selected:
            self._last_selected_sample = {
                "cpu": float(selected["cpu_percent"]),
                "ram": float(selected["ram_mb"]),
                "gpu": float(selected["gpu_mb"]),
            }
            if not self._selected_cpu_history:
                self._selected_cpu_history.append(self._last_selected_sample["cpu"])
            if not self._selected_ram_history:
                self._selected_ram_history.append(self._last_selected_sample["ram"])
            if not self._selected_gpu_history:
                self._selected_gpu_history.append(self._last_selected_sample["gpu"])
        elif self._selected_pid is None:
            self._last_selected_sample = None
            self._selected_cpu_history.clear()
            self._selected_ram_history.clear()
            self._selected_gpu_history.clear()

        proc_width = max(900, self._process_canvas.winfo_width())
        self._process_canvas.create_rectangle(8, 8, proc_width - 8, 172, outline="#2d3440")
        if not selected:
            self._process_canvas.create_text(
                16,
                18,
                text="Per-process Usage (select a process row)",
                anchor=tk.W,
                fill="#d6deeb",
                font=("Segoe UI", 9),
            )
            return

        LOGGER.debug("action=graph-render selected_pid=%s visible_rows=%s", selected["pid"], len(visible_rows))

        label = (
            f"Per-process Usage: {selected['name']} (PID {selected['pid']}) "
            f"[{selected.get('classification', 'user')}]"
        )
        self._process_canvas.create_text(
            16,
            18,
            text=label,
            anchor=tk.W,
            fill="#d6deeb",
            font=("Segoe UI", 9),
        )

        self._draw_line(
            self._process_canvas,
            list(self._selected_cpu_history),
            16,
            30,
            proc_width - 32,
            40,
            100.0,
            "#ff6b6b",
            "CPU%",
        )
        self._draw_line(
            self._process_canvas,
            list(self._selected_ram_history),
            16,
            78,
            proc_width - 32,
            40,
            max(1.0, max(self._selected_ram_history) if self._selected_ram_history else 1.0),
            "#4dabf7",
            "RAM MB",
        )
        self._draw_line(
            self._process_canvas,
            list(self._selected_gpu_history),
            16,
            126,
            proc_width - 32,
            40,
            max(1.0, max(self._selected_gpu_history) if self._selected_gpu_history else 1.0),
            "#51cf66",
            "GPU MB",
        )

    def _data_tick(self) -> None:
        monitored_rows = self._scheduler.get_process_rows()
        monitored_pids = self._scheduler.get_monitored_pids()
        monitored_names = self._scheduler.get_monitored_names()
        global_rows = process_utils.get_global_process_rows(
            monitored_pids=monitored_pids,
            monitored_names=monitored_names,
        )

        self._last_monitored_rows = list(monitored_rows)
        self._last_global_rows = list(global_rows)

        visible_rows = self._visible_rows(global_rows=global_rows, monitored_rows=monitored_rows)
        self._last_visible_rows = list(visible_rows)

        self._last_system_sample = {
            "cpu": float(psutil.cpu_percent(interval=0.0)),
            "ram": float(get_ram_usage()),
            "gpu": float(get_gpu_memory()),
        }

        selected = self._find_selected_row(visible_rows)
        if selected:
            self._last_selected_sample = {
                "cpu": float(selected["cpu_percent"]),
                "ram": float(selected["ram_mb"]),
                "gpu": float(selected["gpu_mb"]),
            }
        elif self._selected_pid is None:
            self._last_selected_sample = None

        self._refresh_hogs(global_rows)
        self._refresh_table(visible_rows)
        self._root.after(self._data_refresh_ms, self._data_tick)

    def _schedule_render_tick(self) -> None:
        self._root.after(getattr(self, "_render_interval_ms", 200), self._render_tick)

    def _render_tick(self) -> None:
        if not hasattr(self, "_last_system_sample"):
            self._last_system_sample = None
        if not hasattr(self, "_last_selected_sample"):
            self._last_selected_sample = None
        if not hasattr(self, "_last_visible_rows"):
            self._last_visible_rows = []

        if self._last_system_sample is None and self._cpu_history and self._ram_history and self._gpu_history:
            self._last_system_sample = {
                "cpu": float(self._cpu_history[-1]),
                "ram": float(self._ram_history[-1]),
                "gpu": float(self._gpu_history[-1]),
            }

        if self._last_system_sample:
            self._cpu_history.append(float(self._last_system_sample["cpu"]))
            self._ram_history.append(float(self._last_system_sample["ram"]))
            self._gpu_history.append(float(self._last_system_sample["gpu"]))

        if self._last_selected_sample:
            self._selected_cpu_history.append(float(self._last_selected_sample["cpu"]))
            self._selected_ram_history.append(float(self._last_selected_sample["ram"]))
            self._selected_gpu_history.append(float(self._last_selected_sample["gpu"]))

        LOGGER.debug(
            "action=graph-render system_samples=%s selected_samples=%s",
            len(self._cpu_history),
            len(self._selected_cpu_history),
        )
        self._draw_charts(self._last_visible_rows)
        self._schedule_render_tick()

    def _refresh(self) -> None:
        self._data_tick()

    def _refresh_visible_view(self) -> None:
        visible_rows = self._visible_rows(
            global_rows=getattr(self, "_last_global_rows", []),
            monitored_rows=getattr(self, "_last_monitored_rows", []),
        )
        self._last_visible_rows = list(visible_rows)
        if hasattr(self, "_tree"):
            self._refresh_table(visible_rows)
        if hasattr(self, "_system_canvas") and hasattr(self, "_process_canvas"):
            self._draw_charts(visible_rows)

    def _on_close(self) -> None:
        self._scheduler.stop()
        self._root.destroy()


def start_gui(scheduler: TurnTakingScheduler) -> None:
    """Run the GUI event loop."""
    app = LlamerosGUI(scheduler)
    app.run()