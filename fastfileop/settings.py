"""FastFileOp - Settings Window Module

Provides tkinter-based settings interface.
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

logger = logging.getLogger(__name__)


class SettingsWindow:
    """Settings window

    Provides controls for:
    - Buffer size (slider)
    - Worker threads (spinbox)
    - Hook switches (checkboxes)
    - Auto-start (checkbox)
    - Debug mode (checkbox)
    """

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._window: Optional[tk.Tk] = None

    def show(self):
        """Show settings window"""
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except tk.TclError:
                self._window = None

        self._create_window()

    def _create_window(self):
        config = self.config_manager.config

        self._window = tk.Tk()
        self._window.title("FastFileOp Settings")
        self._window.geometry("480x420")
        self._window.resizable(False, False)

        # Center window
        self._window.update_idletasks()
        x = (self._window.winfo_screenwidth() - 480) // 2
        y = (self._window.winfo_screenheight() - 420) // 2
        self._window.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(self._window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Engine Settings ===
        engine_frame = ttk.LabelFrame(main_frame, text="Engine Settings", padding=10)
        engine_frame.pack(fill=tk.X, pady=(0, 10))

        # Buffer size
        buf_frame = ttk.Frame(engine_frame)
        buf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(buf_frame, text="Buffer Size:").pack(side=tk.LEFT)
        self._buffer_var = tk.IntVar(value=config.buffer_size_mb)
        self._buffer_label = ttk.Label(buf_frame, text=f"{config.buffer_size_mb} MB")
        self._buffer_label.pack(side=tk.RIGHT)
        buf_scale = ttk.Scale(
            buf_frame,
            from_=32,
            to=512,
            variable=self._buffer_var,
            orient=tk.HORIZONTAL,
            command=self._update_buffer_label,
        )
        buf_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Worker threads
        worker_frame = ttk.Frame(engine_frame)
        worker_frame.pack(fill=tk.X, pady=5)
        ttk.Label(worker_frame, text="Worker Threads:").pack(side=tk.LEFT)
        self._workers_var = tk.IntVar(value=config.worker_threads)
        worker_spin = ttk.Spinbox(
            worker_frame,
            from_=1,
            to=8,
            textvariable=self._workers_var,
            width=8,
        )
        worker_spin.pack(side=tk.RIGHT)

        # === Interception Settings ===
        intercept_frame = ttk.LabelFrame(main_frame, text="Interception Settings", padding=10)
        intercept_frame.pack(fill=tk.X, pady=(0, 10))

        self._hook_copy_var = tk.BooleanVar(value=config.hook_copy)
        ttk.Checkbutton(
            intercept_frame,
            text="Intercept Copy/Move (Ctrl+C/X, Ctrl+V)",
            variable=self._hook_copy_var,
        ).pack(anchor=tk.W, pady=2)

        self._hook_delete_var = tk.BooleanVar(value=config.hook_delete)
        ttk.Checkbutton(
            intercept_frame,
            text="Intercept Delete (Delete, Shift+Delete)",
            variable=self._hook_delete_var,
        ).pack(anchor=tk.W, pady=2)

        self._hook_drag_var = tk.BooleanVar(value=config.hook_drag)
        drag_check = ttk.Checkbutton(
            intercept_frame,
            text="Intercept Drag & Drop (requires FastFileOpShim.dll)",
            variable=self._hook_drag_var,
        )
        drag_check.pack(anchor=tk.W, pady=2)

        # === System Settings ===
        system_frame = ttk.LabelFrame(main_frame, text="System Settings", padding=10)
        system_frame.pack(fill=tk.X, pady=(0, 10))

        # Read actual registry state for auto-start
        auto_start_registered = self.config_manager.is_auto_start_registered()
        self._auto_start_var = tk.BooleanVar(value=auto_start_registered)
        ttk.Checkbutton(
            system_frame,
            text="Start with Windows",
            variable=self._auto_start_var,
        ).pack(anchor=tk.W, pady=2)

        self._debug_var = tk.BooleanVar(value=config.debug_mode)
        ttk.Checkbutton(
            system_frame,
            text="Debug Mode (verbose logging)",
            variable=self._debug_var,
        ).pack(anchor=tk.W, pady=2)

        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._close).pack(side=tk.RIGHT)

        self._window.protocol("WM_DELETE_WINDOW", self._close)
        self._window.mainloop()

    def _update_buffer_label(self, value):
        """Update buffer size label"""
        self._buffer_label.config(text=f"{int(float(value))} MB")

    def _save(self):
        """Save settings"""
        try:
            buffer_size_mb = self._buffer_var.get()
            worker_threads = self._workers_var.get()
            hook_copy = self._hook_copy_var.get()
            hook_delete = self._hook_delete_var.get()
            hook_drag = self._hook_drag_var.get()
            auto_start = self._auto_start_var.get()
            debug_mode = self._debug_var.get()

            # Update config
            self.config_manager.update(
                buffer_size_mb=buffer_size_mb,
                worker_threads=worker_threads,
                hook_copy=hook_copy,
                hook_delete=hook_delete,
                hook_drag=hook_drag,
                debug_mode=debug_mode,
            )

            # Handle auto-start separately (registry)
            self.config_manager.set_auto_start(auto_start)

            # Update debug mode
            from .logger import set_debug_mode
            set_debug_mode(debug_mode)

            messagebox.showinfo("Success", "Settings saved.", parent=self._window)
            self._close()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}", parent=self._window)

    def _close(self):
        """Close window"""
        if self._window:
            self._window.destroy()
            self._window = None
