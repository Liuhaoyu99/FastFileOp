"""FastFileOp - 全局键盘钩子模块

使用 WH_KEYBOARD_LL 全局键盘钩子拦截：
- Ctrl+V：当剪贴板含文件且当前窗口为资源管理器时接管粘贴
- Delete / Shift+Delete：当当前窗口为资源管理器时接管删除
"""

import ctypes
import ctypes.wintypes as wintypes
import threading
import queue
from typing import Callable, Optional

from .logger import get_logger

logger = get_logger(__name__)

# Windows 常量
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_DELETE = 0x2E
VK_V = 0x56
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 窗口类名常量
EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


# 钩子回调类型
HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,    # nCode
    wintypes.WPARAM,  # wParam
    wintypes.LPARAM,  # lParam
)


class KeyboardHook:
    """全局键盘钩子

    拦截 Ctrl+V 和 Delete/Shift+Delete，通过队列与主引擎通信。
    """

    def __init__(
        self,
        action_queue: queue.Queue,
        is_intercepting: Callable[[], bool],
    ):
        """
        Args:
            action_queue: 动作队列，钩子检测到需要接管的操作时放入队列
            is_intercepting: 返回是否正在拦截的回调
        """
        self.action_queue = action_queue
        self.is_intercepting = is_intercepting

        self._hook_id = None
        self._hook_proc = None
        self._thread = None
        self._running = False

    def start(self):
        """启动键盘钩子（在新线程中运行消息循环）"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._thread.start()
        logger.info("键盘钩子已启动")

    def stop(self):
        """停止键盘钩子"""
        self._running = False
        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None
        if self._thread and self._thread.is_alive():
            # 发送消息以退出消息循环
            user32.PostThreadMessageW(
                kernel32.GetThreadId(self._thread.ident),
                0x0012,  # WM_QUIT
                0, 0,
            )
        logger.info("键盘钩子已停止")

    def _hook_loop(self):
        """钩子线程的消息循环"""
        self._hook_proc = HOOKPROC(self._low_level_keyboard_proc)
        self._hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            kernel32.GetModuleHandleW(None),
            0,
        )

        if not self._hook_id:
            logger.error("设置键盘钩子失败")
            self._running = False
            return

        # 消息循环
        msg = wintypes.MSG()
        while self._running:
            result = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
            if result:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                ctypes.windll.kernel32.Sleep(1)

    def _low_level_keyboard_proc(self, nCode, wParam, lParam):
        """低级键盘钩子回调"""
        if nCode >= 0 and self.is_intercepting():
            kb = KBDLLHOOKSTRUCT.from_address(lParam)
            vk = kb.vkCode

            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # Ctrl+V
                if vk == VK_V and self._is_ctrl_pressed():
                    if self._is_explorer_window():
                        self.action_queue.put(("paste", None))
                        return 1  # 拦截

                # Delete / Shift+Delete
                if vk == VK_DELETE:
                    if self._is_explorer_window():
                        shift = self._is_shift_pressed()
                        self.action_queue.put(("delete", shift))
                        return 1  # 拦截

        return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)

    @staticmethod
    def _is_ctrl_pressed() -> bool:
        """检查 Ctrl 键是否按下"""
        return bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

    @staticmethod
    def _is_shift_pressed() -> bool:
        """检查 Shift 键是否按下"""
        return bool(
            user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
            or user32.GetAsyncKeyState(VK_LSHIFT) & 0x8000
            or user32.GetAsyncKeyState(VK_RSHIFT) & 0x8000
        )

    @staticmethod
    def _is_explorer_window() -> bool:
        """检查当前前台窗口是否为资源管理器"""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        return class_name.value in EXPLORER_CLASSES

    @staticmethod
    def get_foreground_explorer_hwnd() -> Optional[int]:
        """获取当前前台资源管理器窗口句柄"""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in EXPLORER_CLASSES:
            return hwnd
        return None

    @staticmethod
    def send_paste():
        """模拟发送 Ctrl+V 键盘事件（放行时使用）"""
        import ctypes

        VK_CONTROL = 0x11
        VK_V = 0x56

        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong),
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]

            _anonymous_ = ("_input",)
            _fields_ = [
                ("type", wintypes.DWORD),
                ("_input", _INPUT),
            ]

        inputs = [
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
        ]

        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))

    @staticmethod
    def send_delete():
        """模拟发送 Delete 键盘事件（放行时使用）"""
        INPUT_KEYBOARD = 1
        KEYEVENTF_KEYUP = 0x0002
        VK_DELETE = 0x2E

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong),
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]

            _anonymous_ = ("_input",)
            _fields_ = [
                ("type", wintypes.DWORD),
                ("_input", _INPUT),
            ]

        inputs = [
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_DELETE, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_DELETE, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
        ]

        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))
