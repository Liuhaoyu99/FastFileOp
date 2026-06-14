"""FastFileOp - Clipboard Monitoring Module

Monitors clipboard for CF_HDROP format (file list) and
detects copy vs cut operation via Preferred DropEffect.
"""

import ctypes
from ctypes import wintypes
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Windows clipboard constants
CF_HDROP = 15

DROPEFFECT_COPY = 1
DROPEFFECT_MOVE = 2

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class ClipboardMonitor:
    """Clipboard monitor

    Detects files in clipboard (CF_HDROP) and determines
    if it's a copy or cut operation.
    """

    def __init__(self):
        self._cf_preferred_drop_effect = 0

    def _register_format(self) -> int:
        """Register or get clipboard format"""
        if self._cf_preferred_drop_effect == 0:
            self._cf_preferred_drop_effect = user32.RegisterClipboardFormatW(
                "Preferred DropEffect"
            )
        return self._cf_preferred_drop_effect

    def get_clipboard_files(self) -> Optional[Tuple[List[str], bool]]:
        """Get files from clipboard and operation type

        Returns:
            (file_list, is_cut) or None if no files in clipboard
        """
        files = None
        is_cut = False

        if not user32.OpenClipboard(0):
            logger.debug("Cannot open clipboard")
            return None

        try:
            # Check for CF_HDROP
            h_drop = user32.GetClipboardData(CF_HDROP)
            if not h_drop:
                return None

            # Read file list
            files = self._read_hdrop(h_drop)
            if not files:
                return None

            # Check if cut operation
            is_cut = self._check_cut()

        finally:
            user32.CloseClipboard()

        return files, is_cut

    def _read_hdrop(self, h_drop: int) -> List[str]:
        """Read file paths from CF_HDROP handle"""
        files = []

        try:
            ptr = kernel32.GlobalLock(h_drop)
            if not ptr:
                return files

            try:
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
                    # Unicode strings
                    char_ptr = ctypes.c_wchar_p(ptr + offset)
                    i = 0
                    while True:
                        s = char_ptr.value
                        if not s:
                            # Check for double null terminator
                            char_ptr2 = ctypes.c_wchar_p(
                                ptr + offset + (i + 1) * ctypes.sizeof(ctypes.c_wchar)
                            )
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
                    # ANSI strings
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
            logger.error(f"Failed to read clipboard files: {e}")

        return files

    def _check_cut(self) -> bool:
        """Check if clipboard contains cut operation (Preferred DropEffect)"""
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
            logger.error(f"Failed to check cut flag: {e}")
            return False

    def has_files(self) -> bool:
        """Quick check if clipboard contains files"""
        if not user32.OpenClipboard(0):
            return False
        try:
            return bool(user32.IsClipboardFormatAvailable(CF_HDROP))
        finally:
            user32.CloseClipboard()
