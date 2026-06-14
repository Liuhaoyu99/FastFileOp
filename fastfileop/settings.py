"""FastFileOp - 设置窗口模块

使用 tkinter 实现设置界面。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from .config import ConfigManager, AppConfig
from .logger import get_logger

logger = get_logger(__name__)


class SettingsWindow:
    """设置窗口

    提供：
    - 缓冲区大小调节
    - 接管复制/移动/删除的独立开关
    - 开机自启设置
    - 最大工作线程数
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._window: Optional[tk.Tk] = None

    def show(self):
        """显示设置窗口"""
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
        self._window.title("FastFileOp 设置")
        self._window.geometry("480x400")
        self._window.resizable(False, False)

        # 居中显示
        self._window.update_idletasks()
        x = (self._window.winfo_screenwidth() - 480) // 2
        y = (self._window.winfo_screenheight() - 400) // 2
        self._window.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(self._window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === 引擎设置 ===
        engine_frame = ttk.LabelFrame(main_frame, text="引擎设置", padding=10)
        engine_frame.pack(fill=tk.X, pady=(0, 10))

        # 缓冲区大小
        buf_frame = ttk.Frame(engine_frame)
        buf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(buf_frame, text="缓冲区大小:").pack(side=tk.LEFT)
        self._buffer_var = tk.IntVar(value=config.buffer_size // (1024 * 1024))
        buf_spin = ttk.Spinbox(
            buf_frame,
            from_=1,
            to=512,
            textvariable=self._buffer_var,
            width=8,
        )
        buf_spin.pack(side=tk.LEFT, padx=5)
        ttk.Label(buf_frame, text="MB").pack(side=tk.LEFT)

        # 工作线程数
        worker_frame = ttk.Frame(engine_frame)
        worker_frame.pack(fill=tk.X, pady=5)
        ttk.Label(worker_frame, text="最大线程数:").pack(side=tk.LEFT)
        self._workers_var = tk.IntVar(value=config.max_workers)
        worker_spin = ttk.Spinbox(
            worker_frame,
            from_=1,
            to=16,
            textvariable=self._workers_var,
            width=8,
        )
        worker_spin.pack(side=tk.LEFT, padx=5)

        # === 拦截设置 ===
        intercept_frame = ttk.LabelFrame(main_frame, text="拦截设置", padding=10)
        intercept_frame.pack(fill=tk.X, pady=(0, 10))

        self._intercept_copy_var = tk.BooleanVar(value=config.intercept_copy)
        ttk.Checkbutton(
            intercept_frame,
            text="接管复制操作 (Ctrl+C / Ctrl+V)",
            variable=self._intercept_copy_var,
        ).pack(anchor=tk.W, pady=2)

        self._intercept_move_var = tk.BooleanVar(value=config.intercept_move)
        ttk.Checkbutton(
            intercept_frame,
            text="接管移动操作 (Ctrl+X / Ctrl+V)",
            variable=self._intercept_move_var,
        ).pack(anchor=tk.W, pady=2)

        self._intercept_delete_var = tk.BooleanVar(value=config.intercept_delete)
        ttk.Checkbutton(
            intercept_frame,
            text="接管删除操作 (Delete / Shift+Delete)",
            variable=self._intercept_delete_var,
        ).pack(anchor=tk.W, pady=2)

        # === 系统设置 ===
        system_frame = ttk.LabelFrame(main_frame, text="系统设置", padding=10)
        system_frame.pack(fill=tk.X, pady=(0, 10))

        self._auto_start_var = tk.BooleanVar(value=config.auto_start)
        ttk.Checkbutton(
            system_frame,
            text="开机自动启动",
            variable=self._auto_start_var,
        ).pack(anchor=tk.W, pady=2)

        # === 按钮 ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="保存", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._close).pack(side=tk.RIGHT)

        self._window.protocol("WM_DELETE_WINDOW", self._close)
        self._window.mainloop()

    def _save(self):
        """保存设置"""
        try:
            buffer_size = self._buffer_var.get() * 1024 * 1024
            max_workers = self._workers_var.get()
            intercept_copy = self._intercept_copy_var.get()
            intercept_move = self._intercept_move_var.get()
            intercept_delete = self._intercept_delete_var.get()
            auto_start = self._auto_start_var.get()

            self.config_manager.update(
                buffer_size=buffer_size,
                max_workers=max_workers,
                intercept_copy=intercept_copy,
                intercept_move=intercept_move,
                intercept_delete=intercept_delete,
            )

            # 开机自启单独处理（涉及注册表）
            self.config_manager.set_auto_start(auto_start)

            messagebox.showinfo("提示", "设置已保存", parent=self._window)
            self._close()

        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            messagebox.showerror("错误", f"保存设置失败: {e}", parent=self._window)

    def _close(self):
        """关闭窗口"""
        if self._window:
            self._window.destroy()
            self._window = None
