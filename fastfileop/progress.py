"""FastFileOp - Progress Window Module

Shows a progress dialog during file operations with:
- Current file name
- Overall progress (files and bytes)
- Transfer speed
- Estimated time remaining
- Pause/Resume/Cancel buttons
"""

import logging
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ProgressWindow:
    """Progress dialog for file operations"""

    def __init__(
        self,
        title: str = "FastFileOp",
        operation: str = "Copying",
        total_files: int = 0,
        total_bytes: int = 0,
        on_pause: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ):
        """Initialize progress window

        Args:
            title: Window title
            operation: Operation name (Copying, Moving, Deleting)
            total_files: Total number of files
            total_bytes: Total bytes to transfer
            on_pause: Callback when pause/resume clicked
            on_cancel: Callback when cancel clicked
        """
        self.title = title
        self.operation = operation
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.on_pause = on_pause
        self.on_cancel = on_cancel

        self._window: Optional[tk.Toplevel] = None
        self._paused = False
        self._cancelled = False
        self._closed = False

        # Progress tracking
        self._current_file = ""
        self._files_done = 0
        self._bytes_done = 0
        self._start_time = 0
        self._last_update = 0

        # UI elements
        self._file_label: Optional[ttk.Label] = None
        self._progress_bar: Optional[ttk.Progressbar] = None
        self._progress_label: Optional[ttk.Label] = None
        self._speed_label: Optional[ttk.Label] = None
        self._time_label: Optional[ttk.Label] = None
        self._pause_btn: Optional[ttk.Button] = None
        self._cancel_btn: Optional[ttk.Button] = None

    def show(self):
        """Show the progress window"""
        if self._window is not None:
            return

        self._start_time = time.time()

        # Create window in main thread
        self._create_window()

    def _create_window(self):
        """Create the progress window"""
        self._window = tk.Toplevel()
        self._window.title(f"{self.title} - {self.operation}")
        self._window.geometry("480x200")
        self._window.resizable(False, False)
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        # Center window
        self._window.update_idletasks()
        x = (self._window.winfo_screenwidth() - 480) // 2
        y = (self._window.winfo_screenheight() - 200) // 2
        self._window.geometry(f"+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self._window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Operation label
        op_label = ttk.Label(
            main_frame,
            text=f"{self.operation} files...",
            font=("Segoe UI", 12, "bold")
        )
        op_label.pack(anchor=tk.W)

        # Current file
        self._file_label = ttk.Label(
            main_frame,
            text="Preparing...",
            font=("Segoe UI", 9),
            wraplength=440
        )
        self._file_label.pack(anchor=tk.W, pady=(10, 0))

        # Progress bar
        self._progress_bar = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=440
        )
        self._progress_bar.pack(fill=tk.X, pady=(10, 0))

        # Progress label
        self._progress_label = ttk.Label(
            main_frame,
            text="0 / 0 files (0%)",
            font=("Segoe UI", 9)
        )
        self._progress_label.pack(anchor=tk.W)

        # Info frame
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        # Speed label
        self._speed_label = ttk.Label(
            info_frame,
            text="Speed: -- MB/s",
            font=("Segoe UI", 9)
        )
        self._speed_label.pack(side=tk.LEFT)

        # Time remaining
        self._time_label = ttk.Label(
            info_frame,
            text="Time remaining: --:--",
            font=("Segoe UI", 9)
        )
        self._time_label.pack(side=tk.RIGHT)

        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        # Pause button
        self._pause_btn = ttk.Button(
            btn_frame,
            text="Pause",
            command=self._on_pause_click,
            width=10
        )
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        self._cancel_btn = ttk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel_click,
            width=10
        )
        self._cancel_btn.pack(side=tk.LEFT)

        # Keep window on top
        self._window.attributes('-topmost', True)
        self._window.after(100, lambda: self._window.attributes('-topmost', False))

    def update(
        self,
        current_file: str,
        files_done: int,
        bytes_done: int,
    ):
        """Update progress

        Args:
            current_file: Current file being processed
            files_done: Number of files completed
            bytes_done: Bytes transferred
        """
        if self._closed or self._window is None:
            return

        self._current_file = current_file
        self._files_done = files_done
        self._bytes_done = bytes_done

        # Throttle updates
        now = time.time()
        if now - self._last_update < 0.1:
            return
        self._last_update = now

        # Update UI
        try:
            self._window.after(0, self._update_ui)
        except Exception:
            pass

    def _update_ui(self):
        """Update UI elements"""
        if self._closed or self._window is None:
            return

        try:
            # Current file
            filename = self._current_file
            if len(filename) > 50:
                filename = "..." + filename[-47:]
            self._file_label.config(text=filename)

            # Progress percentage
            if self.total_bytes > 0:
                pct = self._bytes_done / self.total_bytes * 100
            else:
                pct = 0

            self._progress_bar['value'] = pct

            # Progress label
            self._progress_label.config(
                text=f"{self._files_done} / {self.total_files} files ({pct:.1f}%)"
            )

            # Speed
            elapsed = time.time() - self._start_time
            if elapsed > 0 and self._bytes_done > 0:
                speed = self._bytes_done / elapsed
                speed_str = self._format_size(speed) + "/s"
                self._speed_label.config(text=f"Speed: {speed_str}")

                # Time remaining
                if speed > 0 and self.total_bytes > self._bytes_done:
                    remaining_bytes = self.total_bytes - self._bytes_done
                    remaining_sec = remaining_bytes / speed
                    self._time_label.config(
                        text=f"Time remaining: {self._format_time(remaining_sec)}"
                    )

        except Exception as e:
            logger.debug(f"Progress UI update error: {e}")

    def _format_size(self, bytes_val: float) -> str:
        """Format bytes to human readable size"""
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val / (1024*1024*1024):.1f} GB"
        elif bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024*1024):.1f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.1f} KB"
        else:
            return f"{bytes_val:.0f} B"

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        if seconds < 0:
            return "--:--"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _on_pause_click(self):
        """Handle pause button click"""
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.config(text="Resume")
            if self.on_pause:
                self.on_pause(True)
        else:
            self._pause_btn.config(text="Pause")
            if self.on_pause:
                self.on_pause(False)

    def _on_cancel_click(self):
        """Handle cancel button click"""
        self._cancelled = True
        self._cancel_btn.config(state='disabled')
        self._pause_btn.config(state='disabled')
        if self.on_cancel:
            self.on_cancel()

    def _on_close(self):
        """Handle window close"""
        self._cancelled = True
        self.close()

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self._cancelled

    def is_paused(self) -> bool:
        """Check if operation is paused"""
        return self._paused

    def close(self):
        """Close the progress window"""
        self._closed = True
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None

    def set_complete(self, success: bool = True, message: str = ""):
        """Mark operation as complete

        Args:
            success: Whether operation succeeded
            message: Optional completion message
        """
        if self._closed or self._window is None:
            return

        try:
            self._progress_bar['value'] = 100

            if success:
                self._file_label.config(text="Operation completed successfully!")
                self._progress_label.config(
                    text=f"{self.total_files} files processed"
                )
            else:
                self._file_label.config(text=message or "Operation failed")

            self._pause_btn.config(state='disabled')
            self._cancel_btn.config(text="Close")

            # Update cancel button to close window
            self._cancel_btn.config(command=self.close)

        except Exception:
            pass


class ProgressCallback:
    """Callback adapter for FileEngine progress"""

    def __init__(self, window: ProgressWindow):
        self.window = window
        self._last_file = ""

    def __call__(
        self,
        current_file: str,
        file_index: int,
        total_files: int,
        bytes_done: int,
        bytes_total: int
    ):
        """Progress callback for FileEngine"""
        self.window.update(
            current_file=current_file,
            files_done=file_index,
            bytes_done=bytes_done,
        )

        # Check for pause/cancel
        while self.window.is_paused() and not self.window.is_cancelled():
            time.sleep(0.1)

        if self.window.is_cancelled():
            return False  # Signal to cancel

        return True  # Continue
