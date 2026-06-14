"""FastFileOp - Global Keyboard Hook Module

Uses SetWindowsHookEx with WH_KEYBOARD_LL to intercept:
- Ctrl+V: Check clipboard for files, intercept paste in Explorer
- Delete / Shift+Delete: Get selected files in Explorer, intercept delete
"""

import ctypes
import ctypes.wintypes as wintypes
import logging
import queue
import threading
import time
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)

# Windows constants
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

# Explorer window class names
EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Low-level keyboard hook structure"""
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


# Hook callback type
HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_int,      # nCode
    wintypes.WPARAM,   # wParam
    wintypes.LPARAM,   # lParam
)


class KeyboardHook:
    """Global keyboard hook

    Intercepts Ctrl+V and Delete/Shift+Delete in Windows Explorer.
    Uses queue for communication with main thread.
    """

    def __init__(
        self,
        action_queue: queue.Queue,
        is_hooking_enabled: Callable[[], bool],
    ):
        """
        Args:
            action_queue: Queue to send intercepted actions
            is_hooking_enabled: Callback to check if hooking is enabled
        """
        self.action_queue = action_queue
        self.is_hooking_enabled = is_hooking_enabled

        self._hook_id = None
        self._hook_proc = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """Start the keyboard hook in a background thread"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._hook_loop, daemon=True)
        self._thread.start()
        logger.info("Keyboard hook started")

    def stop(self):
        """Stop the keyboard hook"""
        self._running = False

        if self._hook_id:
            user32.UnhookWindowsHookEx(self._hook_id)
            self._hook_id = None

        if self._thread and self._thread.is_alive():
            # Post quit message to exit message loop
            user32.PostThreadMessageW(
                kernel32.GetThreadId(self._thread.ident),
                0x0012,  # WM_QUIT
                0, 0,
            )

        logger.info("Keyboard hook stopped")

    def _hook_loop(self):
        """Hook thread message loop"""
        self._hook_proc = HOOKPROC(self._low_level_keyboard_proc)

        self._hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            kernel32.GetModuleHandleW(None),
            0,
        )

        if not self._hook_id:
            logger.error("Failed to set keyboard hook")
            self._running = False
            return

        # Message loop
        msg = wintypes.MSG()
        while self._running:
            result = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
            if result:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                kernel32.Sleep(1)

    def _low_level_keyboard_proc(self, nCode, wParam, lParam):
        """Low-level keyboard hook callback"""
        if nCode >= 0 and self.is_hooking_enabled():
            kb = KBDLLHOOKSTRUCT.from_address(lParam)
            vk = kb.vkCode

            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # Ctrl+V
                if vk == VK_V and self._is_ctrl_pressed():
                    if self._is_explorer_window():
                        self.action_queue.put(("paste", None))
                        return 1  # Intercept

                # Delete / Shift+Delete
                if vk == VK_DELETE:
                    if self._is_explorer_window():
                        shift = self._is_shift_pressed()
                        self.action_queue.put(("delete", shift))
                        return 1  # Intercept

        return user32.CallNextHookEx(self._hook_id, nCode, wParam, lParam)

    @staticmethod
    def _is_ctrl_pressed() -> bool:
        """Check if Ctrl key is pressed"""
        return bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

    @staticmethod
    def _is_shift_pressed() -> bool:
        """Check if Shift key is pressed"""
        return bool(
            user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
            or user32.GetAsyncKeyState(VK_LSHIFT) & 0x8000
            or user32.GetAsyncKeyState(VK_RSHIFT) & 0x8000
        )

    @staticmethod
    def _is_explorer_window() -> bool:
        """Check if foreground window is Windows Explorer"""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        return class_name.value in EXPLORER_CLASSES

    @staticmethod
    def get_foreground_explorer_hwnd() -> Optional[int]:
        """Get foreground Explorer window handle if it's Explorer"""
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
        """Send Ctrl+V keystroke (for forwarding non-file paste)"""
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
        """Send Delete keystroke (for forwarding)"""
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
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_DELETE, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=VK_DELETE, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
        ]

        n = len(inputs)
        arr = (INPUT * n)(*inputs)
        user32.SendInput(n, ctypes.byref(arr), ctypes.sizeof(INPUT))
