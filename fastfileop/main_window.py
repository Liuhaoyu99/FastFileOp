"""FastFileOp - Main Window (FastCopy-style GUI)

Provides the primary operation interface with:
- Source / Target path selection
- Operation options (multi-workers, override mode, folder mirroring)
- Start / Cancel controls
- Real-time file list with progress
- Progress bar + speed / ETA display
- Chinese / English language switching
"""

import logging
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .engine import FileEngine
from .config import ConfigManager
from .l10n import get_text, get_available_languages, LANG_ZH, LANG_EN

logger = logging.getLogger(__name__)


class MainWindow:
    """FastCopy-style main operation window with i18n support"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._window: Optional[tk.Tk] = None
        self._engine: Optional[FileEngine] = None
        self._engine_lock = threading.Lock()
        self._running = False
        self._start_time = 0.0
        self._last_update = 0.0
        self._lang = config_manager.config.language or LANG_EN

        # Saved widget references for re-translation
        self._src_label: Optional[ttk.Label] = None
        self._dst_label: Optional[ttk.Label] = None
        self._opt_frame: Optional[ttk.LabelFrame] = None
        self._top_frame: Optional[ttk.LabelFrame] = None
        self._list_frame: Optional[ttk.LabelFrame] = None
        self._start_btn: Optional[ttk.Button] = None
        self._pause_btn: Optional[ttk.Button] = None
        self._cancel_btn: Optional[ttk.Button] = None
        self._src_browse_btn: Optional[ttk.Button] = None
        self._dst_browse_btn: Optional[ttk.Button] = None
        self._multi_cb: Optional[ttk.Checkbutton] = None
        self._override_cb: Optional[ttk.Checkbutton] = None
        self._mirror_cb: Optional[ttk.Checkbutton] = None
        self._tree: Optional[ttk.Treeview] = None
        self._progress_bar: Optional[ttk.Progressbar] = None
        self._stats_label: Optional[ttk.Label] = None
        self._lang_combo: Optional[ttk.Combobox] = None

        # State variables (created in show() after Tk root exists)
        self._src_var: Optional[tk.StringVar] = None
        self._dst_var: Optional[tk.StringVar] = None
        self._multi_worker_var: Optional[tk.BooleanVar] = None
        self._override_newer_var: Optional[tk.BooleanVar] = None
        self._mirror_folder_var: Optional[tk.BooleanVar] = None

    def show(self):
        """Show the main window (blocking, call from background thread)"""
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except tk.TclError:
                self._window = None

        self._window = tk.Tk()
        self._window.withdraw()

        # Create tk variables (need Tk root to exist)
        self._src_var = tk.StringVar()
        self._dst_var = tk.StringVar()
        self._multi_worker_var = tk.BooleanVar(value=True)
        self._override_newer_var = tk.BooleanVar(value=False)
        self._mirror_folder_var = tk.BooleanVar(value=True)

        self._build_window()

        # Apply language from config
        initial_display = "中文" if self._lang == LANG_ZH else "English"
        self._lang_combo.set(initial_display)
        if self._lang == LANG_ZH:
            self._re_translate()

        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        self._window.mainloop()

    def _tr(self, key: str) -> str:
        return get_text(key, self._lang)

    def _build_window(self):
        """Build the main window UI"""
        win = self._window
        win.title(self._tr("window_title"))
        win.geometry("720x540")
        win.minsize(640, 480)

        # ── Top: Source / Target ──
        self._top_frame = ttk.LabelFrame(win, text=self._tr("copy_move"), padding=10)
        self._top_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Source
        src_frame = ttk.Frame(self._top_frame)
        src_frame.pack(fill=tk.X, pady=3)
        self._src_label = ttk.Label(src_frame, text=self._tr("source"), width=8)
        self._src_label.pack(side=tk.LEFT)
        src_entry = ttk.Entry(src_frame, textvariable=self._src_var)
        src_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._src_browse_btn = ttk.Button(
            src_frame, text=self._tr("browse"), command=self._browse_src, width=10,
        )
        self._src_browse_btn.pack(side=tk.RIGHT)

        # Target
        dst_frame = ttk.Frame(self._top_frame)
        dst_frame.pack(fill=tk.X, pady=3)
        self._dst_label = ttk.Label(dst_frame, text=self._tr("target"), width=8)
        self._dst_label.pack(side=tk.LEFT)
        dst_entry = ttk.Entry(dst_frame, textvariable=self._dst_var)
        dst_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._dst_browse_btn = ttk.Button(
            dst_frame, text=self._tr("browse"), command=self._browse_dst, width=10,
        )
        self._dst_browse_btn.pack(side=tk.RIGHT)

        # ── Middle: Options ──
        self._opt_frame = ttk.LabelFrame(win, text=self._tr("options"), padding=10)
        self._opt_frame.pack(fill=tk.X, padx=10, pady=5)

        # Language selector (top-right of options)
        lang_frame = ttk.Frame(self._opt_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 5))
        lang_frame.columnconfigure(1, weight=1)
        self._lang_combo = ttk.Combobox(
            lang_frame, state="readonly", width=10,
        )
        lang_codes = []
        self._lang_map = {}
        for code, display in get_available_languages():
            lang_codes.append(display)
            self._lang_map[display] = code
        self._lang_combo['values'] = lang_codes
        self._lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)
        self._lang_combo.pack(side=tk.RIGHT)

        self._multi_cb = ttk.Checkbutton(
            self._opt_frame,
            text=self._tr("multi_workers"),
            variable=self._multi_worker_var,
        )
        self._multi_cb.pack(anchor=tk.W, pady=1)

        self._override_cb = ttk.Checkbutton(
            self._opt_frame,
            text=self._tr("override_newer"),
            variable=self._override_newer_var,
        )
        self._override_cb.pack(anchor=tk.W, pady=1)

        self._mirror_cb = ttk.Checkbutton(
            self._opt_frame,
            text=self._tr("mirror_folder"),
            variable=self._mirror_folder_var,
        )
        self._mirror_cb.pack(anchor=tk.W, pady=1)

        # ── Control buttons ──
        ctrl_frame = ttk.Frame(win)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

        self._start_btn = ttk.Button(
            ctrl_frame, text=self._tr("start"), command=self._on_start, width=12,
        )
        self._start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._pause_btn = ttk.Button(
            ctrl_frame, text=self._tr("pause"), command=self._on_pause, width=12,
            state='disabled',
        )
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._cancel_btn = ttk.Button(
            ctrl_frame, text=self._tr("cancel"), command=self._on_cancel, width=12,
            state='disabled',
        )
        self._cancel_btn.pack(side=tk.LEFT)

        # ── File list ──
        self._list_frame = ttk.LabelFrame(win, text=self._tr("file_progress"), padding=5)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "size", "status")
        self._tree = ttk.Treeview(self._list_frame, columns=columns, show="headings",
                                   height=8, selectmode='none')
        self._tree.heading("name", text=self._tr("file_name"))
        self._tree.heading("size", text=self._tr("file_size"))
        self._tree.heading("status", text=self._tr("status"))
        self._tree.column("name", width=400, minwidth=200)
        self._tree.column("size", width=100, minwidth=80, anchor=tk.E)
        self._tree.column("status", width=120, minwidth=80, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(self._list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Bottom: progress bar + stats ──
        bottom_frame = ttk.Frame(win)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._progress_bar = ttk.Progressbar(bottom_frame, mode='determinate', length=200)
        self._progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self._stats_label = ttk.Label(bottom_frame, text=self._tr("ready"), font=("Segoe UI", 9))
        self._stats_label.pack(side=tk.RIGHT)

        # Center window
        win.update_idletasks()
        x = (win.winfo_screenwidth() - 720) // 2
        y = (win.winfo_screenheight() - 540) // 2
        win.geometry(f"+{x}+{y}")

        win.deiconify()
        win.lift()
        win.focus_force()

    def _on_language_change(self, event=None):
        """Handle language combobox selection"""
        display_name = self._lang_combo.get()
        new_lang = self._lang_map.get(display_name, LANG_EN)
        if new_lang == self._lang:
            return
        self._lang = new_lang
        self._re_translate()

    def _re_translate(self):
        """Update all UI text to current language"""
        self._window.title(self._tr("window_title"))
        self._top_frame.config(text=self._tr("copy_move"))
        self._src_label.config(text=self._tr("source"))
        self._dst_label.config(text=self._tr("target"))
        self._src_browse_btn.config(text=self._tr("browse"))
        self._dst_browse_btn.config(text=self._tr("browse"))
        self._opt_frame.config(text=self._tr("options"))
        self._multi_cb.config(text=self._tr("multi_workers"))
        self._override_cb.config(text=self._tr("override_newer"))
        self._mirror_cb.config(text=self._tr("mirror_folder"))
        self._start_btn.config(text=self._tr("start"))
        pause_text = self._pause_btn.cget("text")
        if pause_text == get_text("pause", LANG_EN) or pause_text == get_text("pause", LANG_ZH):
            self._pause_btn.config(text=self._tr("pause"))
        else:
            self._pause_btn.config(text=self._tr("resume"))
        self._cancel_btn.config(text=self._tr("cancel"))
        self._list_frame.config(text=self._tr("file_progress"))
        self._tree.heading("name", text=self._tr("file_name"))
        self._tree.heading("size", text=self._tr("file_size"))
        self._tree.heading("status", text=self._tr("status"))
        # Stats label — keep existing content if it's a progress format
        current_text = self._stats_label.cget("text")
        if current_text in (get_text("ready", LANG_EN), get_text("ready", LANG_ZH),
                            get_text("starting", LANG_EN), get_text("starting", LANG_ZH),
                            get_text("cancelled", LANG_EN), get_text("cancelled", LANG_ZH)):
            self._stats_label.config(text=self._tr("ready" if current_text in (
                get_text("ready", LANG_EN), get_text("ready", LANG_ZH)) else "starting"))

    # ── Browse helpers ──

    def _browse_src(self):
        d = filedialog.askdirectory(title=self._tr("browse"))
        if d:
            self._src_var.set(d)

    def _browse_dst(self):
        d = filedialog.askdirectory(title=self._tr("browse"))
        if d:
            self._dst_var.set(d)

    # ── Control handlers ──

    def _on_start(self):
        src = self._src_var.get().strip()
        dst = self._dst_var.get().strip()
        if not src:
            messagebox.showwarning(self._tr("window_title"), self._tr("warn_no_source"), parent=self._window)
            return
        if not dst:
            messagebox.showwarning(self._tr("window_title"), self._tr("warn_no_target"), parent=self._window)
            return
        if not os.path.isdir(src) and not os.path.isfile(src):
            messagebox.showwarning(
                self._tr("window_title"),
                self._tr("warn_source_not_exist") % src,
                parent=self._window,
            )
            return

        # Resolve source items
        if os.path.isdir(src):
            src_items = [src]
            use_mirror = self._mirror_folder_var.get()
        else:
            src_items = [os.path.dirname(src), os.path.basename(src)]
            use_mirror = False

        # Resolve destination
        if use_mirror:
            folder_name = os.path.basename(src.rstrip("\\/"))
            dst_dir = os.path.join(dst, folder_name) if folder_name else dst
        else:
            dst_dir = dst

        # Create engine
        config = self.config_manager.config
        max_workers = config.worker_threads if self._multi_worker_var.get() else 1
        self._engine = FileEngine(
            buffer_size=config.buffer_size,
            max_workers=max_workers,
            progress_callback=self._on_progress,
        )

        # Reset UI
        self._running = True
        self._start_time = time.time()
        self._start_btn.config(state='disabled')
        self._pause_btn.config(state='normal', text=self._tr("pause"))
        self._cancel_btn.config(state='normal')
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._progress_bar['value'] = 0
        self._stats_label.config(text=self._tr("starting"))

        # Run in background thread
        def _run():
            try:
                logger.info("MainWindow: Copy %s -> %s", src_items, dst_dir)
                self._engine.copy(src_items, dst_dir)
                failed = self._engine.get_failed()
                if failed:
                    msg = self._tr("completed_fail") % len(failed)
                else:
                    msg = self._tr("completed_success")
                self._set_complete(msg)
            except Exception as e:
                logger.error("MainWindow copy error: %s", e)
                self._set_complete(f"{self._tr('error_prefix')} {e}")
            finally:
                with self._engine_lock:
                    self._engine = None
                    self._running = False

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _on_progress(self, current_file: str, file_index: int, total_files: int,
                     bytes_done: int, bytes_total: int):
        """Progress callback from engine (called from worker threads)"""
        now = time.time()
        if now - self._last_update < 0.15:
            return
        self._last_update = now

        if not self._window:
            return
        try:
            pct = (bytes_done / bytes_total * 100) if bytes_total > 0 else 0
            elapsed = now - self._start_time
            speed = bytes_done / elapsed if elapsed > 0 else 0

            self._window.after(0, lambda: self._do_update(
                current_file, file_index, total_files, pct, speed,
            ))
        except Exception:
            pass

    def _do_update(self, current_file, file_index, total_files, pct, speed):
        """Execute progress update on UI thread"""
        try:
            self._progress_bar['value'] = pct
            self._stats_label.config(
                text=self._tr("files_progress") % (file_index, total_files, pct, self._fmt_speed(speed))
            )

            # Add new file to the list
            if current_file:
                name = os.path.basename(current_file)
                children = self._tree.get_children()
                if len(children) < 1000:
                    fsize = ""
                    try:
                        fsize = self._fmt_size(os.path.getsize(current_file))
                    except Exception:
                        pass
                    self._tree.insert("", tk.END, values=(name, fsize, self._tr("status_copying")))
                if children:
                    self._tree.see(children[-1])
        except Exception:
            pass

    def _set_complete(self, message: str):
        """Thread-safe completion signal"""
        if not self._window:
            return
        try:
            self._window.after(0, lambda: self._do_complete(message))
        except Exception:
            pass

    def _do_complete(self, message: str):
        """Update UI on completion"""
        try:
            self._progress_bar['value'] = 100
            self._stats_label.config(text=message)
            self._start_btn.config(state='normal')
            self._pause_btn.config(state='disabled')
            self._cancel_btn.config(state='disabled')
        except Exception:
            pass

    def _on_pause(self):
        with self._engine_lock:
            if not self._engine:
                return
            if self._pause_btn.cget('text') == self._tr("pause"):
                self._engine.pause()
                self._pause_btn.config(text=self._tr("resume"))
            else:
                self._engine.resume()
                self._pause_btn.config(text=self._tr("pause"))

    def _on_cancel(self):
        with self._engine_lock:
            if self._engine:
                self._engine.cancel()
        self._set_complete(self._tr("cancelled"))
        self._start_btn.config(state='normal')
        self._pause_btn.config(state='disabled')
        self._cancel_btn.config(state='disabled')

    def _on_close(self):
        if self._running:
            if not messagebox.askokcancel(
                self._tr("confirm_close_title"),
                self._tr("confirm_close_msg"),
                parent=self._window,
            ):
                return
        with self._engine_lock:
            if self._engine:
                self._engine.cancel()
                self._engine = None
        if self._window:
            self._window.destroy()
            self._window = None

    @staticmethod
    def _fmt_size(b: float) -> str:
        if b >= 1024 ** 3:
            return f"{b / 1024**3:.1f} GB"
        elif b >= 1024 ** 2:
            return f"{b / 1024**2:.1f} MB"
        elif b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b:.0f} B"

    @staticmethod
    def _fmt_speed(bps: float) -> str:
        if bps >= 1024 ** 3:
            return f"{bps / 1024**3:.1f} GB/s"
        elif bps >= 1024 ** 2:
            return f"{bps / 1024**2:.1f} MB/s"
        elif bps >= 1024:
            return f"{bps / 1024:.1f} KB/s"
        return f"{bps:.0f} B/s"
