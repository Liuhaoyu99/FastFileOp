"""FastFileOp - Shell COM Integration Module

Uses Shell.Application COM interface to:
- Get selected files in Explorer
- Get current directory in Explorer
"""

import logging
import os
from typing import List, Optional

import pythoncom
from win32com.client import Dispatch

logger = logging.getLogger(__name__)


class ShellHelper:
    """Shell COM helper

    Provides access to Explorer selection and current directory
    via Shell.Application COM interface.
    """

    def __init__(self):
        self._shell = None

    def _get_shell(self):
        """Get Shell.Application COM object"""
        if self._shell is None:
            pythoncom.CoInitialize()
            self._shell = Dispatch("Shell.Application")
        return self._shell

    def get_selected_files(self, hwnd: int = 0) -> List[str]:
        """Get selected files in Explorer

        Args:
            hwnd: Explorer window handle, 0 for active window

        Returns:
            List of selected file paths
        """
        files = []

        try:
            shell = self._get_shell()
            windows = shell.Windows()
            target_window = None

            if hwnd == 0:
                # Get last Explorer window
                count = windows.Count
                if count > 0:
                    target_window = windows.Item(count - 1)
            else:
                # Find by hwnd
                for i in range(windows.Count):
                    win = windows.Item(i)
                    try:
                        if win.HWND == hwnd:
                            target_window = win
                            break
                    except Exception:
                        continue

            if target_window is None:
                logger.debug("Explorer window not found")
                return files

            # Get selected items
            selected_items = target_window.Document.SelectedItems()
            for i in range(selected_items.Count):
                item = selected_items.Item(i)
                path = item.Path
                if path and os.path.exists(path):
                    files.append(path)

        except Exception as e:
            logger.error(f"Failed to get selected files: {e}")

        return files

    def get_current_directory(self, hwnd: int = 0) -> Optional[str]:
        """Get current directory in Explorer

        Args:
            hwnd: Explorer window handle

        Returns:
            Current directory path or None
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
            logger.error(f"Failed to get current directory: {e}")
            return None

    def get_explorer_hwnds(self) -> List[int]:
        """Get all Explorer window handles"""
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
            logger.error(f"Failed to get Explorer windows: {e}")

        return hwnds
