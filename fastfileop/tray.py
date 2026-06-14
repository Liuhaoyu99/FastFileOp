"""FastFileOp - 系统托盘模块

使用 pystray 创建系统托盘图标和右键菜单。
"""

import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

from .config import ConfigManager
from .logger import get_logger

logger = get_logger(__name__)


class TrayIcon:
    """系统托盘图标

    右键菜单：
    - 暂停/恢复拦截
    - 设置
    - 退出
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        on_settings: Callable,
        on_exit: Callable,
    ):
        """
        Args:
            config_manager: 配置管理器
            on_settings: 打开设置窗口的回调
            on_exit: 退出程序的回调
        """
        self.config_manager = config_manager
        self.on_settings = on_settings
        self.on_exit = on_exit

        self._icon: Optional[pystray.Icon] = None
        self._paused = config_manager.config.intercept_paused

    def _create_icon_image(self) -> Image.Image:
        """创建托盘图标图像"""
        # 创建一个简单的图标：蓝色背景白色 "F" 字母
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 蓝色圆角矩形背景
        draw.rounded_rectangle(
            [(4, 4), (size - 4, size - 4)],
            radius=12,
            fill=(41, 128, 185),
        )

        # 白色 "F" 字母
        draw.text((18, 8), "F", fill=(255, 255, 255))

        return image

    def _create_paused_image(self) -> Image.Image:
        """创建暂停状态的托盘图标"""
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 灰色背景
        draw.rounded_rectangle(
            [(4, 4), (size - 4, size - 4)],
            radius=12,
            fill=(128, 128, 128),
        )

        # 白色 "F" 字母
        draw.text((18, 8), "F", fill=(255, 255, 255))

        return image

    def _get_menu(self) -> pystray.Menu:
        """创建右键菜单"""
        pause_label = "恢复拦截" if self._paused else "暂停拦截"
        status_text = "已暂停" if self._paused else "运行中"

        return pystray.Menu(
            pystray.MenuItem(
                f"状态: {status_text}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                pause_label,
                self._toggle_pause,
            ),
            pystray.MenuItem(
                "设置",
                self._open_settings,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "退出",
                self._quit,
            ),
        )

    def _toggle_pause(self, icon, item):
        """切换暂停/恢复拦截"""
        self._paused = not self._paused
        self.config_manager.update(intercept_paused=self._paused)
        self._refresh_icon()
        status = "已暂停" if self._paused else "已恢复"
        logger.info(f"拦截{status}")

    def _open_settings(self, icon, item):
        """打开设置窗口"""
        try:
            self.on_settings()
        except Exception as e:
            logger.error(f"打开设置窗口失败: {e}")

    def _quit(self, icon, item):
        """退出程序"""
        logger.info("用户选择退出")
        icon.stop()
        self.on_exit()

    def _refresh_icon(self):
        """刷新托盘图标"""
        if self._icon:
            if self._paused:
                self._icon.icon = self._create_paused_image()
            else:
                self._icon.icon = self._create_icon_image()
            self._icon.menu = self._get_menu()

    def run(self):
        """运行托盘图标（阻塞）"""
        image = self._create_paused_image() if self._paused else self._create_icon_image()
        self._icon = pystray.Icon(
            name="FastFileOp",
            icon=image,
            title="FastFileOp - 高速文件操作",
            menu=self._get_menu(),
        )
        logger.info("系统托盘图标已创建")
        self._icon.run()

    def run_threaded(self) -> threading.Thread:
        """在后台线程中运行托盘图标

        Returns:
            托盘线程对象
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        """停止托盘图标"""
        if self._icon:
            self._icon.stop()
