"""gui.py - Tkinter interface for Llameros process monitoring and controls."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from . import process_utils
from .scheduler import TurnTakingScheduler


class LlamerosGUI:
    """Desktop control panel for scheduler state and process actions."""

    def __init__(self, scheduler: TurnTakingScheduler):
        self._scheduler = scheduler
        self._root = tk.Tk()
        self._root.title("Llameros Control Panel")
        self._root.geometry("1000x620")

        self._turn_taking_var = tk.BooleanVar(value=self._scheduler.get_turn_taking_mode())

        self._top_cpu_var = tk.StringVar(value="Top CPU hog: n/a")
        self._top_ram_var = tk.StringVar(value="Top RAM hog: n/a")
        self._top_gpu_var = tk.StringVar(value="Top GPU hog: n/a")
        self._triple_hog_var = tk.StringVar(value="Hogging all three: n/a")

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
        ).pack(anchor=tk.W)

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
        )
        self._tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        self._tree.heading("pid", text="PID")
        self._tree.heading("name", text="Process")
        self._tree.heading("cpu", text="CPU%")
        self._tree.heading("ram", text="RAM MB")
        self._tree.heading("gpu", text="GPU MB")
        self._tree.heading("status", text="Status")
        self._tree.heading("priority", text="Priority")

        self._tree.column("pid", width=80, anchor=tk.CENTER)
        self._tree.column("name", width=200)
        self._tree.column("cpu", width=100, anchor=tk.E)
        self._tree.column("ram", width=120, anchor=tk.E)
        self._tree.column("gpu", width=120, anchor=tk.E)
        self._tree.column("status", width=120, anchor=tk.CENTER)
        self._tree.column("priority", width=100, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll_y.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

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

    def _selected_pid(self) -> int | None:
        selected = self._tree.selection()
        if not selected:
            return None
        values = self._tree.item(selected[0], "values")
        if not values:
            return None
        return int(values[0])

    def _pause_selected(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        self._scheduler.pause(pid)

    def _resume_selected(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        self._scheduler.resume(pid)

    def _kill_selected(self) -> None:
        pid = self._selected_pid()
        if pid is None:
            return
        if messagebox.askyesno("Confirm Kill", f"Kill PID {pid}?"):
            self._scheduler.kill(pid)

    def _set_priority_selected(self) -> None:
        pid = self._selected_pid()
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
        pid = self._selected_pid()
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

    def _refresh_table(self, rows: list[dict]) -> None:
        for row_id in self._tree.get_children():
            self._tree.delete(row_id)

        for row in sorted(rows, key=lambda item: (-item["priority"], item["pid"])):
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
                    row["priority"],
                ),
            )

    def _refresh(self) -> None:
        rows = self._scheduler.get_process_rows()
        self._refresh_hogs(rows)
        self._refresh_table(rows)
        self._root.after(1000, self._refresh)

    def _on_close(self) -> None:
        self._scheduler.stop()
        self._root.destroy()


def start_gui(scheduler: TurnTakingScheduler) -> None:
    """Run the GUI event loop."""
    app = LlamerosGUI(scheduler)
    app.run()