"""FastFileOp - 配置管理模块"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from .logger import get_logger

logger = get_logger(__name__)

# 配置文件路径
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FastFileOp")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")


@dataclass
class AppConfig:
    """应用配置"""
    # 缓冲区大小（字节），默认 64MB
    buffer_size: int = 64 * 1024 * 1024

    # 最大工作线程数
    max_workers: int = 4

    # 是否接管复制操作
    intercept_copy: bool = True

    # 是否接管移动操作
    intercept_move: bool = True

    # 是否接管删除操作
    intercept_delete: bool = True

    # 是否开机自启
    auto_start: bool = False

    # 是否暂停拦截
    intercept_paused: bool = False


class ConfigManager:
    """配置管理器

    负责加载、保存和提供应用配置。
    配置文件存储在 %APPDATA%\FastFileOp\config.json
    """

    def __init__(self):
        self._config = AppConfig()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        """从文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 只更新已知字段
                for key, value in data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)
                logger.info(f"配置已加载: {CONFIG_FILE}")
            else:
                logger.info("配置文件不存在，使用默认配置")
                self.save()
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")

        return self._config

    def save(self) -> None:
        """保存配置到文件"""
        try:
            os.makedirs(APP_DATA_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def update(self, **kwargs) -> None:
        """更新配置字段并保存"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save()

    def is_intercepting(self) -> bool:
        """当前是否处于拦截状态"""
        if self._config.intercept_paused:
            return False
        return (
            self._config.intercept_copy
            or self._config.intercept_move
            or self._config.intercept_delete
        )

    def set_auto_start(self, enable: bool) -> None:
        """设置开机自启

        通过在注册表 HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
        添加/删除条目实现。
        """
        import winreg

        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        app_name = "FastFileOp"
        # 获取当前 exe 路径
        import sys
        exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                logger.info(f"已添加开机自启: {exe_path}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("已移除开机自启")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self._config.auto_start = enable
            self.save()
        except Exception as e:
            logger.error(f"设置开机自启失败: {e}")
