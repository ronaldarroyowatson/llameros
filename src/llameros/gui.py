"""gui.py - Tkinter interface for Llameros process monitoring and controls."""
from __future__ import annotations

from collections import deque
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import psutil

from . import process_utils
from .gpu_monitor import get_gpu_memory
from .system_monitor import get_ram_usage
from .scheduler import TurnTakingScheduler


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
        self._selected_pid: int | None = None

        self._max_history = 90
        self._cpu_history: deque[float] = deque(maxlen=self._max_history)
        self._ram_history: deque[float] = deque(maxlen=self._max_history)
        self._gpu_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_cpu_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_ram_history: deque[float] = deque(maxlen=self._max_history)
        self._selected_gpu_history: deque[float] = deque(maxlen=self._max_history)

        self._build_layout()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        self._refresh()
        self._root.mainloop()

    def _build_layout(self) -> None:
        top_frame = ttk.Frame(self._root, padding=12)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, textvariable=self._top_cpu_var).pack(anchor=tk.W)
        ttk.Label(top_frame, textvariable=self._top_ram_var).pack(anchor=tk.W)
        ttk.Label(top_frame, textvariable=self._top_gpu_var).pack(anchor=tk.W)
        ttk.Label(top_frame, textvariable=self._triple_hog_var).pack(anchor=tk.W)

        toggle_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        toggle_frame.pack(fill=tk.X)
        ttk.Checkbutton(
            toggle_frame,
            text="Turn-taking mode",
            variable=self._turn_taking_var,
            command=self._toggle_turn_taking,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            toggle_frame,
            text="Show all processes",
            variable=self._show_all_processes_var,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            toggle_frame,
            text="Show only AI agents",
            variable=self._only_ai_var,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            toggle_frame,
            text="Show only heavy hitters",
            variable=self._only_heavy_var,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            toggle_frame,
            text="Show only monitored processes",
            variable=self._only_monitored_var,
        ).pack(side=tk.LEFT, padx=4)

        table_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        table_frame.pack(fill=tk.BOTH, expand=True)

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
        self._tree.heading("pid", text="PID", command=lambda: self._set_sort("pid"))
        self._tree.heading("name", text="Process", command=lambda: self._set_sort("name"))
        self._tree.heading("cpu", text="CPU%", command=lambda: self._set_sort("cpu_percent"))
        self._tree.heading("ram", text="RAM MB", command=lambda: self._set_sort("ram_mb"))
        self._tree.heading("gpu", text="GPU MB", command=lambda: self._set_sort("gpu_mb"))
        self._tree.heading("status", text="Status", command=lambda: self._set_sort("status"))
        self._tree.heading("priority", text="Priority", command=lambda: self._set_sort("priority"))
        self._tree.heading(
            "classification",
            text="Classification",
            command=lambda: self._set_sort("classification"),
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

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        charts_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        charts_frame.pack(fill=tk.BOTH, expand=False)

        self._system_canvas = tk.Canvas(charts_frame, height=300, bg="#101318", highlightthickness=0)
        self._system_canvas.pack(fill=tk.X, pady=(0, 8))
        self._process_canvas = tk.Canvas(charts_frame, height=180, bg="#101318", highlightthickness=0)
        self._process_canvas.pack(fill=tk.X)

        button_frame = ttk.Frame(self._root, padding=(12, 0, 12, 12))
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Pause", command=self._pause_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Resume", command=self._resume_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Kill", command=self._kill_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Set Priority", command=self._set_priority_selected).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(button_frame, text="Set Background", command=self._set_background_selected).pack(
            side=tk.LEFT, padx=4
        )

    def _toggle_turn_taking(self) -> None:
        self._scheduler.set_turn_taking_mode(self._turn_taking_var.get())

    def _on_row_selected(self, event: tk.Event) -> None:
        del event
        selected = self._tree.selection()
        if not selected:
            self._selected_pid = None
            return
        values = self._tree.item(selected[0], "values")
        if not values:
            self._selected_pid = None
            return
        self._selected_pid = int(values[0])

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

    def _set_sort(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = column in {"pid", "cpu_percent", "ram_mb", "gpu_mb", "priority"}

    def _sorted_rows(self, rows: list[dict]) -> list[dict]:
        def _key(item: dict) -> float | str:
            value = item.get(self._sort_column)
            if isinstance(value, (int, float)):
                return float(value)
            return str(value or "").lower()

        return sorted(rows, key=_key, reverse=self._sort_reverse)

    def _visible_rows(self, global_rows: list[dict], monitored_rows: list[dict]) -> list[dict]:
        rows = list(global_rows) if self._show_all_processes_var.get() else list(monitored_rows)

        if self._only_monitored_var.get():
            rows = [row for row in rows if bool(row.get("monitored"))]
        if self._only_ai_var.get():
            rows = [row for row in rows if row.get("classification") == "ai agent"]
        if self._only_heavy_var.get():
            rows = [row for row in rows if process_utils.is_heavy_hitter(row, self._rules)]
        return rows

    def _refresh_table(self, rows: list[dict]) -> None:
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        for row in self._sorted_rows(rows):
            self._tree.insert(
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

        if not self._cpu_history:
            return

        cpu_values = list(self._cpu_history)
        ram_values = list(self._ram_history)
        gpu_values = list(self._gpu_history)

        ram_max = max(1.0, max(ram_values))
        gpu_max = max(1.0, max(gpu_values))
        span = max(1, len(cpu_values) - 1)

        for index in range(len(cpu_values)):
            px = x + (index / span) * w
            cpu_norm = min(1.0, cpu_values[index] / 100.0)
            ram_norm = min(1.0, ram_values[index] / ram_max)
            gpu_norm = min(1.0, gpu_values[index] / gpu_max)

            total = cpu_norm + ram_norm + gpu_norm
            if total <= 0.0:
                continue

            cpu_h = h * (cpu_norm / total)
            ram_h = h * (ram_norm / total)
            gpu_h = h * (gpu_norm / total)

            y_base = y + h
            canvas.create_line(px, y_base, px, y_base - cpu_h, fill="#ff6b6b")
            canvas.create_line(px, y_base - cpu_h, px, y_base - cpu_h - ram_h, fill="#4dabf7")
            canvas.create_line(px, y_base - cpu_h - ram_h, px, y_base - cpu_h - ram_h - gpu_h, fill="#51cf66")

    def _draw_charts(self, visible_rows: list[dict]) -> None:
        self._system_canvas.delete("all")
        self._process_canvas.delete("all")

        cpu_now = float(psutil.cpu_percent(interval=0.0))
        ram_now = float(get_ram_usage())
        gpu_now = float(get_gpu_memory())

        self._cpu_history.append(cpu_now)
        self._ram_history.append(ram_now)
        self._gpu_history.append(gpu_now)

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

        selected = None
        if self._selected_pid is not None:
            selected = next((row for row in visible_rows if int(row["pid"]) == self._selected_pid), None)

        if selected:
            self._selected_cpu_history.append(float(selected["cpu_percent"]))
            self._selected_ram_history.append(float(selected["ram_mb"]))
            self._selected_gpu_history.append(float(selected["gpu_mb"]))
        else:
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

    def _refresh(self) -> None:
        monitored_rows = self._scheduler.get_process_rows()
        monitored_pids = self._scheduler.get_monitored_pids()
        monitored_names = self._scheduler.get_monitored_names()
        global_rows = process_utils.get_global_process_rows(
            monitored_pids=monitored_pids,
            monitored_names=monitored_names,
        )

        visible_rows = self._visible_rows(global_rows=global_rows, monitored_rows=monitored_rows)
        self._refresh_hogs(global_rows)
        self._refresh_table(visible_rows)
        self._draw_charts(visible_rows)
        self._root.after(1000, self._refresh)

    def _on_close(self) -> None:
        self._scheduler.stop()
        self._root.destroy()


def start_gui(scheduler: TurnTakingScheduler) -> None:
    """Run the GUI event loop."""
    app = LlamerosGUI(scheduler)
    app.run()