"""FastFileOp - Progress Window Module

Shows a progress dialog during file operations with:
- Current file name
- Overall progress (files and bytes)
- Transfer speed
- Estimated time remaining
- Pause/Resume/Cancel buttons

Uses a dedicated tkinter thread for UI, safe to call from any thread.
"""

import logging
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from .l10n import get_text, LANG_EN, LANG_ZH

logger = logging.getLogger(__name__)


class ProgressWindow:
    """Progress dialog for file operations - thread-safe"""

    def __init__(
        self,
        title: str = "FastFileOp",
        operation: str = "Copying",
        total_files: int = 0,
        total_bytes: int = 0,
        on_pause: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        lang: str = LANG_EN,
    ):
        self.title = title
        self.operation = operation
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.on_pause = on_pause
        self.on_cancel = on_cancel
        self._lang = lang

        self._paused = False
        self._cancelled = False
        self._closed = False

        # Progress tracking
        self._current_file = ""
        self._files_done = 0
        self._bytes_done = 0
        self._start_time = 0
        self._last_update = 0

        # Thread-safe command queue (UI thread reads from this)
        self._queue: queue.Queue = queue.Queue()

        # UI thread
        self._ui_thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None

    def show(self):
        """Show the progress window (starts UI thread)"""
        if self._closed:
            return
        self._start_time = time.time()
        self._ui_thread = threading.Thread(target=self._run_ui_loop, daemon=True)
        self._ui_thread.start()
        # Wait for UI to be ready
        time.sleep(0.2)

    def _run_ui_loop(self):
        """Run tkinter mainloop in dedicated thread"""
        self._root = tk.Tk()
        self._root.withdraw()  # Hide root window

        # Create the actual progress window as Toplevel
        self._build_window()

        # Process commands from queue
        def _process_queue():
            try:
                while True:
                    cmd, args = self._queue.get_nowait()
                    if cmd == "update":
                        self._do_update(*args)
                    elif cmd == "complete":
                        self._do_complete(*args)
                    elif cmd == "close":
                        self._do_close()
                        return
                    elif cmd == "cancel_btn_state":
                        self._do_set_cancel_state(*args)
                    elif cmd == "pause_btn_state":
                        self._do_set_pause_state(*args)
            except queue.Empty:
                pass
            # Schedule next check
            if self._root and not self._closed:
                self._root.after(50, _process_queue)

        # Start processing
        self._root.after(100, _process_queue)
        self._root.mainloop()

    def _tr(self, key: str) -> str:
        return get_text(key, self._lang)

    def _build_window(self):
        """Build the progress window UI"""
        win = tk.Toplevel(self._root)
        win.title(self._tr("progress_title") % self.operation)
        win.geometry("500x220")
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self._on_close_click)

        win.update_idletasks()
        x = (win.winfo_screenwidth() - 500) // 2
        y = (win.winfo_screenheight() - 220) // 2
        win.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        op_label = ttk.Label(
            main_frame,
            text=f"{self.operation}...",
            font=("Segoe UI", 12, "bold")
        )
        op_label.pack(anchor=tk.W)

        self._file_label = ttk.Label(
            main_frame,
            text=self._tr("progress_preparing"),
            font=("Segoe UI", 9),
            wraplength=460
        )
        self._file_label.pack(anchor=tk.W, pady=(10, 0))

        self._progress_bar = ttk.Progressbar(
            main_frame, mode='determinate', length=460
        )
        self._progress_bar.pack(fill=tk.X, pady=(10, 0))

        self._progress_label = ttk.Label(
            main_frame, text=self._tr("progress_files") % (0, 0, 0), font=("Segoe UI", 9)
        )
        self._progress_label.pack(anchor=tk.W)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self._speed_label = ttk.Label(
            info_frame, text=self._tr("progress_speed") % "--", font=("Segoe UI", 9)
        )
        self._speed_label.pack(side=tk.LEFT)

        self._time_label = ttk.Label(
            info_frame, text=self._tr("progress_eta") % "--:--", font=("Segoe UI", 9)
        )
        self._time_label.pack(side=tk.RIGHT)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self._pause_btn = ttk.Button(
            btn_frame, text=get_text("pause", self._lang),
            command=self._on_pause_click, width=10
        )
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._cancel_btn = ttk.Button(
            btn_frame, text=get_text("cancel", self._lang),
            command=self._on_cancel_click, width=10
        )
        self._cancel_btn.pack(side=tk.LEFT)

        win.attributes('-topmost', True)
        win.lift()
        win.focus_force()
        win.after(200, lambda: win.attributes('-topmost', False))

        self._win = win

    def update(self, current_file: str, files_done: int, bytes_done: int):
        """Thread-safe update (can call from any thread)"""
        if self._closed:
            return
        self._current_file = current_file
        self._files_done = files_done
        self._bytes_done = bytes_done

        now = time.time()
        if now - self._last_update < 0.15:
            return
        self._last_update = now

        try:
            self._queue.put_nowait(("update", (current_file, files_done, bytes_done)))
        except Exception:
            pass

    def _do_update(self, current_file, files_done, bytes_done):
        """Execute update on UI thread"""
        if self._closed or not self._win:
            return
        try:
            filename = current_file
            if len(filename) > 55:
                filename = "..." + filename[-52:]
            self._file_label.config(text=filename)

            if self.total_bytes > 0:
                pct = min(bytes_done / self.total_bytes * 100, 100)
            else:
                pct = 0
            self._progress_bar['value'] = pct
            self._progress_label.config(
                text=self._tr("progress_files") % (files_done, self.total_files, pct)
            )

            elapsed = time.time() - self._start_time
            if elapsed > 0 and bytes_done > 0:
                speed = bytes_done / elapsed
                self._speed_label.config(text=self._tr("progress_speed") % self._fmt_size(speed))
                if speed > 0 and self.total_bytes > bytes_done:
                    remain = (self.total_bytes - bytes_done) / speed
                    self._time_label.config(text=self._tr("progress_eta") % self._fmt_time(remain))
        except Exception as e:
            logger.debug("Progress update error: %s", e)

    def set_complete(self, success: bool = True, message: str = ""):
        """Thread-safe mark complete"""
        try:
            self._queue.put_nowait(("complete", (success, message)))
        except Exception:
            pass

    def _do_complete(self, success, message):
        if self._closed or not self._win:
            return
        try:
            self._progress_bar['value'] = 100
            if success:
                self._file_label.config(text=self._tr("progress_done_success"))
                self._progress_label.config(text=self._tr("progress_completed") % self.total_files)
            else:
                self._file_label.config(text=message or self._tr("progress_done_fail"))
            self._pause_btn.config(state='disabled')
            self._cancel_btn.config(text=self._tr("progress_close"))
            self._cancel_btn.config(command=self.close)
        except Exception:
            pass

    def _on_pause_click(self):
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.config(text=self._tr("resume"))
            if self.on_pause:
                self.on_pause(True)
        else:
            self._pause_btn.config(text=self._tr("pause"))
            if self.on_pause:
                self.on_pause(False)

    def _on_cancel_click(self):
        self._cancelled = True
        try:
            self._queue.put_nowait(("cancel_btn_state", ("disabled",)))
            self._queue.put_nowait(("pause_btn_state", ("disabled",)))
        except Exception:
            pass
        if self.on_cancel:
            self.on_cancel()

    def _on_close_click(self):
        self._cancelled = True
        self.close()

    def _do_set_cancel_state(self, state):
        if self._closed or not self._win:
            return
        try:
            self._cancel_btn.config(state=state)
        except Exception:
            pass

    def _do_set_pause_state(self, state):
        if self._closed or not self._win:
            return
        try:
            self._pause_btn.config(state=state)
        except Exception:
            pass

    def is_cancelled(self) -> bool:
        return self._cancelled

    def is_paused(self) -> bool:
        return self._paused

    def close(self):
        """Thread-safe close"""
        self._closed = True
        try:
            self._queue.put_nowait(("close", ()))
        except Exception:
            pass

    def _do_close(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None

    @staticmethod
    def _fmt_size(b: float) -> str:
        if b >= 1024**3:
            return f"{b / 1024**3:.1f} GB"
        elif b >= 1024**2:
            return f"{b / 1024**2:.1f} MB"
        elif b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b:.0f} B"

    @staticmethod
    def _fmt_time(s: float) -> str:
        if s < 0:
            return "--:--"
        return f"{int(s // 60):02d}:{int(s % 60):02d}"


class ProgressCallback:
    """Callback adapter for FileEngine progress - thread-safe"""

    def __init__(self, window: ProgressWindow):
        self.window = window

    def __call__(
        self,
        current_file: str,
        file_index: int,
        total_files: int,
        bytes_done: int,
        bytes_total: int,
    ) -> bool:
        self.window.update(
            current_file=current_file,
            files_done=file_index,
            bytes_done=bytes_done,
        )

        while self.window.is_paused() and not self.window.is_cancelled():
            time.sleep(0.1)

        return not self.window.is_cancelled()
