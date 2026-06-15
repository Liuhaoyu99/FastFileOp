"""FastFileOp - Operation Log

In-memory ring buffer of recent operations with a tkinter log viewer.
"""

import logging
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from .l10n import get_text, LANG_EN

logger = logging.getLogger(__name__)

MAX_LOG_ENTRIES = 500


class LogEntry:
    __slots__ = ("timestamp", "message")

    def __init__(self, message: str):
        self.timestamp = time.time()
        self.message = message


class OperationLog:
    """Thread-safe ring-buffer operation log"""

    def __init__(self, max_entries: int = MAX_LOG_ENTRIES):
        self._entries: list[LogEntry] = []
        self._max = max_entries
        self._lock = threading.Lock()

    def add(self, message: str):
        with self._lock:
            self._entries.append(LogEntry(message))
            if len(self._entries) > self._max:
                self._entries = self._entries[-self._max:]

    def get_all(self) -> list[LogEntry]:
        with self._lock:
            return list(self._entries)

    @staticmethod
    def fmt_time(ts: float) -> str:
        return time.strftime("%H:%M:%S", time.localtime(ts))


class LogViewer:
    """tkinter log viewer window"""

    def __init__(self, op_log: OperationLog, lang: str = LANG_EN):
        self._op_log = op_log
        self._lang = lang
        self._window: Optional[tk.Toplevel] = None

    def _tr(self, key: str) -> str:
        return get_text(key, self._lang)

    def show(self):
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except tk.TclError:
                self._window = None

        root = tk.Tk()
        root.withdraw()

        win = tk.Toplevel(root)
        win.title(self._tr("log_title"))
        win.geometry("620x400")
        win.resizable(True, True)
        win.transient(root)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 9),
                       state='disabled', bg="white", fg="#222")
        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=vsb.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        text.configure(state='normal')
        for entry in self._op_log.get_all():
            line = f"[{LogViewer.fmt_time(entry.timestamp)}] {entry.message}\n"
            text.insert(tk.END, line)
        text.configure(state='disabled')
        text.see(tk.END)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text=self._tr("log_close"), command=win.destroy).pack(side=tk.RIGHT)

        win.update_idletasks()
        x = (win.winfo_screenwidth() - 620) // 2
        y = (win.winfo_screenheight() - 400) // 2
        win.geometry(f"+{x}+{y}")

        win.deiconify()
        win.lift()
        win.focus_force()

        self._window = win
        root.mainloop()

    @staticmethod
    def fmt_time(ts: float) -> str:
        return time.strftime("%H:%M:%S", time.localtime(ts))
