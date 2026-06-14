"""FastFileOp - 主入口模块

启动系统托盘、键盘钩子和操作处理循环。
"""

import queue
import sys
import threading
import time

from .clipboard import ClipboardMonitor
from .config import ConfigManager
from .engine import FileEngine, OpState
from .hook import KeyboardHook
from .logger import get_logger
from .shell import ShellHelper
from .tray import TrayIcon

logger = get_logger(__name__)


class FastFileOpApp:
    """FastFileOp 主应用

    协调各模块工作：
    1. 系统托盘图标
    2. 全局键盘钩子
    3. 剪贴板监控
    4. 文件操作引擎
    """

    def __init__(self):
        self.config_manager = ConfigManager()
        self.config_manager.load()

        self.action_queue: queue.Queue = queue.Queue()
        self.clipboard = ClipboardMonitor()
        self.shell = ShellHelper()
        self.engine: FileEngine = None  # 当前正在执行的引擎
        self._engine_lock = threading.Lock()
        self._running = True

        # 键盘钩子
        self.hook = KeyboardHook(
            action_queue=self.action_queue,
            is_intercepting=self._is_intercepting,
        )

        # 系统托盘
        self.tray = TrayIcon(
            config_manager=self.config_manager,
            on_settings=self._open_settings,
            on_exit=self._quit,
        )

    def _is_intercepting(self) -> bool:
        """判断当前是否应该拦截键盘操作"""
        return self.config_manager.is_intercepting()

    def _open_settings(self):
        """打开设置窗口（在独立线程中）"""
        from .settings import SettingsWindow

        def _show():
            settings = SettingsWindow(self.config_manager)
            settings.show()

        thread = threading.Thread(target=_show, daemon=True)
        thread.start()

    def _quit(self):
        """退出程序"""
        logger.info("正在退出 FastFileOp...")
        self._running = False
        self.hook.stop()
        self.tray.stop()

    def _create_engine(self) -> FileEngine:
        """根据当前配置创建文件操作引擎"""
        config = self.config_manager.config
        return FileEngine(
            buffer_size=config.buffer_size,
            max_workers=config.max_workers,
            on_progress=self._on_progress,
        )

    def _on_progress(self, progress):
        """操作进度回调"""
        if progress.state == OpState.RUNNING:
            pct = progress.percent
            logger.debug(
                f"进度: {pct:.1f}% "
                f"({progress.completed_files}/{progress.total_files} 文件)"
            )

    def _handle_paste(self):
        """处理粘贴操作"""
        config = self.config_manager.config

        # 获取剪贴板文件
        result = self.clipboard.get_clipboard_files()
        if result is None:
            # 剪贴板无文件，放行
            KeyboardHook.send_paste()
            return

        files, is_cut = result
        if not files:
            KeyboardHook.send_paste()
            return

        # 检查是否启用拦截
        if is_cut and not config.intercept_move:
            KeyboardHook.send_paste()
            return
        if not is_cut and not config.intercept_copy:
            KeyboardHook.send_paste()
            return

        # 获取目标目录
        hwnd = KeyboardHook.get_foreground_explorer_hwnd()
        dst_dir = self.shell.get_current_directory(hwnd) if hwnd else None
        if not dst_dir:
            logger.warning("无法获取目标目录，放行原操作")
            KeyboardHook.send_paste()
            return

        # 执行操作
        with self._engine_lock:
            engine = self._create_engine()
            self.engine = engine

        def _run():
            try:
                if is_cut:
                    logger.info(f"接管移动: {len(files)} 个文件 -> {dst_dir}")
                    engine.move(files, dst_dir)
                else:
                    logger.info(f"接管复制: {len(files)} 个文件 -> {dst_dir}")
                    engine.copy(files, dst_dir)

                failed = engine.get_failed()
                if failed:
                    logger.warning(f"操作完成，{len(failed)} 个文件失败")
                    for fp in failed:
                        logger.warning(f"  失败: {fp.src} - {fp.error}")
            except Exception as e:
                logger.error(f"文件操作异常: {e}")
            finally:
                with self._engine_lock:
                    self.engine = None

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _handle_delete(self, shift_pressed: bool):
        """处理删除操作"""
        config = self.config_manager.config
        if not config.intercept_delete:
            KeyboardHook.send_delete()
            return

        # 获取选中的文件
        hwnd = KeyboardHook.get_foreground_explorer_hwnd()
        files = self.shell.get_selected_files(hwnd) if hwnd else []
        if not files:
            logger.warning("未获取到选中文件，放行原操作")
            KeyboardHook.send_delete()
            return

        permanent = shift_pressed

        with self._engine_lock:
            engine = self._create_engine()
            self.engine = engine

        def _run():
            try:
                mode = "永久删除" if permanent else "移到回收站"
                logger.info(f"接管删除({mode}): {len(files)} 个文件")
                engine.delete(files, permanent=permanent)

                failed = engine.get_failed()
                if failed:
                    logger.warning(f"删除完成，{len(failed)} 个文件失败")
                    for fp in failed:
                        logger.warning(f"  失败: {fp.src} - {fp.error}")
            except Exception as e:
                logger.error(f"删除操作异常: {e}")
            finally:
                with self._engine_lock:
                    self.engine = None

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _process_actions(self):
        """处理动作队列的主循环"""
        while self._running:
            try:
                action, param = self.action_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if action == "paste":
                    self._handle_paste()
                elif action == "delete":
                    self._handle_delete(param)
                else:
                    logger.warning(f"未知动作: {action}")
            except Exception as e:
                logger.error(f"处理动作失败: {e}")

    def run(self):
        """启动应用"""
        logger.info("=" * 50)
        logger.info("FastFileOp 启动")
        logger.info("=" * 50)

        # 启动系统托盘（阻塞主线程）
        tray_thread = self.tray.run_threaded()

        # 启动键盘钩子
        self.hook.start()

        # 启动动作处理循环
        self._process_actions()

        # 等待托盘线程结束
        tray_thread.join(timeout=5)

        logger.info("FastFileOp 已退出")


def main():
    """主入口"""
    app = FastFileOpApp()
    app.run()


if __name__ == "__main__":
    main()
