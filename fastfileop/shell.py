"""FastFileOp - Shell COM 集成模块

通过 Shell.Application COM 接口获取资源管理器中
当前选中的文件列表。
"""

import os
from typing import List, Optional

import pythoncom
from win32com.client import Dispatch

from .logger import get_logger

logger = get_logger(__name__)


class ShellHelper:
    """Shell COM 辅助类

    通过 Shell.Application COM 接口：
    - 获取资源管理器当前选中的文件列表
    - 获取资源管理器当前目录路径
    """

    def __init__(self):
        self._shell = None

    def _get_shell(self):
        """获取 Shell.Application COM 对象"""
        if self._shell is None:
            pythoncom.CoInitialize()
            self._shell = Dispatch("Shell.Application")
        return self._shell

    def get_selected_files(self, hwnd: int = 0) -> List[str]:
        """获取资源管理器中当前选中的文件路径列表

        Args:
            hwnd: 资源管理器窗口句柄，0 表示当前活动窗口

        Returns:
            选中的文件完整路径列表
        """
        files = []
        try:
            shell = self._get_shell()
            windows = shell.Windows()
            target_window = None

            if hwnd == 0:
                # 获取最后一个资源管理器窗口
                count = windows.Count
                if count > 0:
                    target_window = windows.Item(count - 1)
            else:
                # 根据 hwnd 查找
                for i in range(windows.Count):
                    win = windows.Item(i)
                    try:
                        if win.HWND == hwnd:
                            target_window = win
                            break
                    except Exception:
                        continue

            if target_window is None:
                logger.debug("未找到资源管理器窗口")
                return files

            # 获取选中项
            selected_items = target_window.Document.SelectedItems()
            for i in range(selected_items.Count):
                item = selected_items.Item(i)
                path = item.Path
                if path and os.path.exists(path):
                    files.append(path)

        except Exception as e:
            logger.error(f"获取选中文件失败: {e}")

        return files

    def get_current_directory(self, hwnd: int = 0) -> Optional[str]:
        """获取资源管理器当前目录路径

        Args:
            hwnd: 资源管理器窗口句柄

        Returns:
            当前目录路径，失败返回 None
        """
        try:
            shell = self._get_shell()
            windows = shell.Windows()
            target_window = None

            if hwnd == 0:
                count = windows.Count
                if count > 0:
                    target_window = windows.Item(count - 1)
            else:
                for i in range(windows.Count):
                    win = windows.Item(i)
                    try:
                        if win.HWND == hwnd:
                            target_window = win
                            break
                    except Exception:
                        continue

            if target_window is None:
                return None

            return target_window.Document.Folder.Self.Path

        except Exception as e:
            logger.error(f"获取当前目录失败: {e}")
            return None

    def get_explorer_hwnd(self) -> List[int]:
        """获取所有资源管理器窗口的句柄列表"""
        hwnds = []
        try:
            shell = self._get_shell()
            windows = shell.Windows()
            for i in range(windows.Count):
                win = windows.Item(i)
                try:
                    hwnds.append(win.HWND)
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"获取资源管理器窗口列表失败: {e}")
        return hwnds
