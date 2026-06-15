"""FastFileOp - Settings Window Module (fully translatable)

Provides tkinter-based settings interface.
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable

from .l10n import get_text, LANG_EN, LANG_ZH

logger = logging.getLogger(__name__)


class SettingsWindow:
    """Settings window with full i18n support"""

    def __init__(
        self,
        config_manager,
        on_language_change: Optional[Callable[[str], None]] = None,
    ):
        self.config_manager = config_manager
        self._on_language_change = on_language_change
        self._window: Optional[tk.Tk] = None
        self._lang: str = config_manager.config.language or LANG_EN

        # Widget references for re-translation
        self._engine_frame: Optional[ttk.LabelFrame] = None
        self._buf_label: Optional[ttk.Label] = None
        self._worker_label: Optional[ttk.Label] = None
        self._intercept_frame: Optional[ttk.LabelFrame] = None
        self._hook_copy_cb: Optional[ttk.Checkbutton] = None
        self._hook_delete_cb: Optional[ttk.Checkbutton] = None
        self._hook_drag_cb: Optional[ttk.Checkbutton] = None
        self._lang_frame: Optional[ttk.LabelFrame] = None
        self._security_frame: Optional[ttk.LabelFrame] = None
        self._confirm_delete_cb: Optional[ttk.Checkbutton] = None
        self._system_frame: Optional[ttk.LabelFrame] = None
        self._auto_start_cb: Optional[ttk.Checkbutton] = None
        self._debug_cb: Optional[ttk.Checkbutton] = None
        self._save_btn: Optional[ttk.Button] = None
        self._cancel_btn_settings: Optional[ttk.Button] = None

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
        self._create_window()

    def _create_window(self):
        config = self.config_manager.config
        self._lang = config.language or LANG_EN

        self._window = tk.Tk()
        self._window.title(self._tr("settings_title"))
        self._window.geometry("480x600")
        self._window.resizable(False, False)

        self._window.update_idletasks()
        x = (self._window.winfo_screenwidth() - 480) // 2
        y = (self._window.winfo_screenheight() - 600) // 2
        self._window.geometry(f"+{x}+{y}")

        # Canvas + scrollbar for the whole content
        canvas = tk.Canvas(self._window, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(self._window, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        # Mouse wheel (local bind — only active while mouse is over canvas)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        main_frame = ttk.Frame(scroll_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === Engine Settings ===
        self._engine_frame = ttk.LabelFrame(main_frame, text=self._tr("engine_settings"), padding=10)
        self._engine_frame.pack(fill=tk.X, pady=(0, 10))

        buf_frame = ttk.Frame(self._engine_frame)
        buf_frame.pack(fill=tk.X, pady=5)
        self._buf_label = ttk.Label(buf_frame, text=self._tr("buffer_size"))
        self._buf_label.pack(side=tk.LEFT)
        self._buffer_var = tk.IntVar(value=config.buffer_size_mb)
        self._buffer_val_label = ttk.Label(buf_frame, text=f"{config.buffer_size_mb} MB")
        self._buffer_val_label.pack(side=tk.RIGHT)
        ttk.Scale(
            buf_frame, from_=32, to=512,
            variable=self._buffer_var, orient=tk.HORIZONTAL,
            command=self._update_buffer_label,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        worker_frame = ttk.Frame(self._engine_frame)
        worker_frame.pack(fill=tk.X, pady=5)
        self._worker_label = ttk.Label(worker_frame, text=self._tr("worker_threads"))
        self._worker_label.pack(side=tk.LEFT)
        self._workers_var = tk.IntVar(value=config.worker_threads)
        ttk.Spinbox(
            worker_frame, from_=1, to=8,
            textvariable=self._workers_var, width=8,
        ).pack(side=tk.RIGHT)

        # === Interception Settings ===
        self._intercept_frame = ttk.LabelFrame(main_frame, text=self._tr("interception_settings"), padding=10)
        self._intercept_frame.pack(fill=tk.X, pady=(0, 10))

        self._hook_copy_var = tk.BooleanVar(value=config.hook_copy)
        self._hook_copy_cb = ttk.Checkbutton(
            self._intercept_frame,
            text=self._tr("intercept_copy"),
            variable=self._hook_copy_var,
        )
        self._hook_copy_cb.pack(anchor=tk.W, pady=2)

        self._hook_delete_var = tk.BooleanVar(value=config.hook_delete)
        self._hook_delete_cb = ttk.Checkbutton(
            self._intercept_frame,
            text=self._tr("intercept_delete"),
            variable=self._hook_delete_var,
        )
        self._hook_delete_cb.pack(anchor=tk.W, pady=2)

        self._hook_drag_var = tk.BooleanVar(value=config.hook_drag)
        self._hook_drag_cb = ttk.Checkbutton(
            self._intercept_frame,
            text=self._tr("intercept_drag"),
            variable=self._hook_drag_var,
        )
        self._hook_drag_cb.pack(anchor=tk.W, pady=2)

        # === Language ===
        self._lang_frame = ttk.LabelFrame(main_frame, text=self._tr("language"), padding=10)
        self._lang_frame.pack(fill=tk.X, pady=(0, 10))

        self._lang_var = tk.StringVar(value=config.language)
        ttk.Radiobutton(self._lang_frame, text="English",
                        variable=self._lang_var, value="en").pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(self._lang_frame, text="中文",
                        variable=self._lang_var, value="zh").pack(anchor=tk.W, pady=2)

        # === Security ===
        self._security_frame = ttk.LabelFrame(main_frame, text=self._tr("security"), padding=10)
        self._security_frame.pack(fill=tk.X, pady=(0, 10))

        self._confirm_delete_var = tk.BooleanVar(value=config.confirm_delete)
        self._confirm_delete_cb = ttk.Checkbutton(
            self._security_frame,
            text=self._tr("confirm_delete"),
            variable=self._confirm_delete_var,
        )
        self._confirm_delete_cb.pack(anchor=tk.W, pady=2)

        # === System Settings ===
        self._system_frame = ttk.LabelFrame(main_frame, text=self._tr("system_settings"), padding=10)
        self._system_frame.pack(fill=tk.X, pady=(0, 10))

        auto_start_registered = self.config_manager.is_auto_start_registered()
        self._auto_start_var = tk.BooleanVar(value=auto_start_registered)
        self._auto_start_cb = ttk.Checkbutton(
            self._system_frame,
            text=self._tr("start_with_windows"),
            variable=self._auto_start_var,
        )
        self._auto_start_cb.pack(anchor=tk.W, pady=2)

        self._debug_var = tk.BooleanVar(value=config.debug_mode)
        self._debug_cb = ttk.Checkbutton(
            self._system_frame,
            text=self._tr("debug_mode"),
            variable=self._debug_var,
        )
        self._debug_cb.pack(anchor=tk.W, pady=2)

        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self._save_btn = ttk.Button(
            btn_frame, text=self._tr("save"), command=self._save, width=10,
        )
        self._save_btn.pack(side=tk.RIGHT, padx=5)

        self._cancel_btn_settings = ttk.Button(
            btn_frame, text=self._tr("cancel_settings"), command=self._close, width=10,
        )
        self._cancel_btn_settings.pack(side=tk.RIGHT)

        self._window.protocol("WM_DELETE_WINDOW", self._close)
        self._window.mainloop()

    def _update_buffer_label(self, value):
        self._buffer_val_label.config(text=f"{int(float(value))} MB")

    def _save(self):
        try:
            new_lang = self._lang_var.get()
            buffer_size_mb = self._buffer_var.get()
            worker_threads = self._workers_var.get()
            hook_copy = self._hook_copy_var.get()
            hook_delete = self._hook_delete_var.get()
            hook_drag = self._hook_drag_var.get()
            confirm_delete = self._confirm_delete_var.get()
            debug_mode = self._debug_var.get()
            auto_start = self._auto_start_var.get()

            # Detect language change
            lang_changed = new_lang != self._lang

            self.config_manager.update(
                buffer_size_mb=buffer_size_mb,
                worker_threads=worker_threads,
                hook_copy=hook_copy,
                hook_delete=hook_delete,
                hook_drag=hook_drag,
                debug_mode=debug_mode,
                language=new_lang,
                confirm_delete=confirm_delete,
            )

            self.config_manager.set_auto_start(auto_start)

            from .logger import set_debug_mode
            set_debug_mode(debug_mode)

            if lang_changed:
                self._lang = new_lang
                self._re_translate()
                if self._on_language_change:
                    self._on_language_change(new_lang)

            messagebox.showinfo(
                self._tr("settings_success"),
                self._tr("settings_saved"),
                parent=self._window,
            )
            self._close()

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            messagebox.showerror(
                self._tr("settings_error_title"),
                self._tr("settings_error") % str(e),
                parent=self._window,
            )

    def _re_translate(self):
        """Update all UI text to current language"""
        self._window.title(self._tr("settings_title"))
        self._engine_frame.config(text=self._tr("engine_settings"))
        self._buf_label.config(text=self._tr("buffer_size"))
        self._worker_label.config(text=self._tr("worker_threads"))
        self._intercept_frame.config(text=self._tr("interception_settings"))
        self._hook_copy_cb.config(text=self._tr("intercept_copy"))
        self._hook_delete_cb.config(text=self._tr("intercept_delete"))
        self._hook_drag_cb.config(text=self._tr("intercept_drag"))
        self._lang_frame.config(text=self._tr("language"))
        self._security_frame.config(text=self._tr("security"))
        self._confirm_delete_cb.config(text=self._tr("confirm_delete"))
        self._system_frame.config(text=self._tr("system_settings"))
        self._auto_start_cb.config(text=self._tr("start_with_windows"))
        self._debug_cb.config(text=self._tr("debug_mode"))
        self._save_btn.config(text=self._tr("save"))
        self._cancel_btn_settings.config(text=self._tr("cancel_settings"))

    def _close(self):
        if self._window:
            try:
                self._window.unbind_all("<MouseWheel>")
            except Exception:
                pass
            self._window.destroy()
            self._window = None
