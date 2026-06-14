"""FastFileOp - 剪贴板监控模块

监控剪贴板中的 CF_HDROP 格式（文件列表），
判断是复制操作还是剪切操作。
"""

import ctypes
from ctypes import wintypes
from typing import List, Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)

# Windows 剪贴板常量
CF_HDROP = 15
CF_PREFERREDDROPEFFECT = ctypes.c_uint(0x00001657).value  # 注册的剪贴板格式

DROPEFFECT_COPY = 1
DROPEFFECT_MOVE = 2

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class ClipboardMonitor:
    """剪贴板监控器

    检测剪贴板中是否包含文件路径（CF_HDROP），
    并判断是复制还是剪切操作。
    """

    def __init__(self):
        self._cf_preferred_drop_effect = 0

    def _register_format(self) -> int:
        """注册或获取剪贴板格式"""
        if self._cf_preferred_drop_effect == 0:
            self._cf_preferred_drop_effect = user32.RegisterClipboardFormatW(
                "Preferred DropEffect"
            )
        return self._cf_preferred_drop_effect

    def get_clipboard_files(self) -> Optional[Tuple[List[str], bool]]:
        """获取剪贴板中的文件列表和操作类型

        Returns:
            (文件路径列表, 是否为剪切操作) 或 None（剪贴板无文件）
        """
        files = None
        is_cut = False

        if not user32.OpenClipboard(0):
            logger.debug("无法打开剪贴板")
            return None

        try:
            # 检查是否有 CF_HDROP
            h_drop = user32.GetClipboardData(CF_HDROP)
            if not h_drop:
                return None

            # 读取文件列表
            files = self._read_hdrop(h_drop)
            if not files:
                return None

            # 检查是否为剪切操作
            is_cut = self._check_cut()

        finally:
            user32.CloseClipboard()

        return files, is_cut

    def _read_hdrop(self, h_drop: int) -> List[str]:
        """从 CF_HDROP 句柄读取文件路径列表"""
        files = []
        try:
            # 锁定内存获取指针
            ptr = kernel32.GlobalLock(h_drop)
            if not ptr:
                return files

            try:
                # DROPFILES 结构体: 第一个 DWORD 是结构体大小
                class DROPFILES(ctypes.Structure):
                    _fields_ = [
                        ("pFiles", wintypes.DWORD),
                        ("pt", wintypes.POINT),
                        ("fNC", wintypes.BOOL),
                        ("fWide", wintypes.BOOL),
                    ]

                dropfiles = DROPFILES.from_address(ptr)
                offset = dropfiles.pFiles

                if dropfiles.fWide:
                    # Unicode 字符串
                    char_ptr = ctypes.c_wchar_p(ptr + offset)
                    i = 0
                    while True:
                        s = char_ptr.value
                        if not s:
                            # 双 null 结尾，连续两个空字符串表示结束
                            # 检查下一个
                            char_ptr2 = ctypes.c_wchar_p(ptr + offset + (i + 1) * ctypes.sizeof(ctypes.c_wchar))
                            if not char_ptr2.value:
                                break
                            i += 1
                            continue
                        files.append(s)
                        i += 1
                        char_ptr = ctypes.c_wchar_p(
                            ptr + offset + i * ctypes.sizeof(ctypes.c_wchar)
                        )
                else:
                    # ANSI 字符串
                    char_ptr = ctypes.c_char_p(ptr + offset)
                    while True:
                        s = char_ptr.value
                        if not s:
                            break
                        files.append(s.decode("mbcs"))
                        char_ptr = ctypes.c_char_p(
                            ptr + offset + len(s) + 1
                        )
            finally:
                kernel32.GlobalUnlock(h_drop)

        except Exception as e:
            logger.error(f"读取剪贴板文件列表失败: {e}")

        return files

    def _check_cut(self) -> bool:
        """检查剪贴板是否为剪切操作（Preferred DropEffect）"""
        try:
            fmt = self._register_format()
            h_data = user32.GetClipboardData(fmt)
            if not h_data:
                return False

            ptr = kernel32.GlobalLock(h_data)
            if not ptr:
                return False

            try:
                drop_effect = ctypes.c_uint.from_address(ptr).value
                return bool(drop_effect & DROPEFFECT_MOVE)
            finally:
                kernel32.GlobalUnlock(h_data)

        except Exception as e:
            logger.error(f"检查剪切标志失败: {e}")
            return False

    def has_files(self) -> bool:
        """快速检查剪贴板是否包含文件"""
        if not user32.OpenClipboard(0):
            return False
        try:
            return bool(user32.IsClipboardFormatAvailable(CF_HDROP))
        finally:
            user32.CloseClipboard()
