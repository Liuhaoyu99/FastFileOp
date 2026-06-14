"""FastFileOp - DLL Registration Module

Handles automatic registration of the shell extension DLL.
"""

import ctypes
import logging
import os
import subprocess
import sys
from pathlib import Path

import winreg

logger = logging.getLogger(__name__)

# Registry keys for shell extension registration
COPY_HOOK_KEY = r"Directory\shellex\CopyHookHandlers\FastFileOp.CopyHook"
DRAG_DROP_KEY = r"Directory\shellex\DragDropHandlers\FastFileOp.DragDropHandler"
CLSID_KEY = r"CLSID\{12345678-1234-1234-1234-123456789ABC}"


def is_admin() -> bool:
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def is_dll_registered() -> bool:
    """Check if the shell extension DLL is registered"""
    try:
        # Check if CopyHook handler is registered
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, COPY_HOOK_KEY):
            pass
        logger.debug("DLL is registered (CopyHook handler found)")
        return True
    except FileNotFoundError:
        logger.debug("DLL is not registered (CopyHook handler not found)")
        return False
    except Exception as e:
        logger.debug(f"Error checking DLL registration: {e}")
        return False


def get_dll_path() -> Path | None:
    """Get the path to FastFileOpShim.dll"""
    # Check same directory as executable
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        exe_dir = Path(sys.executable).parent
    else:
        # Running as script
        exe_dir = Path(__file__).parent.parent

    dll_path = exe_dir / "FastFileOpShim.dll"
    if dll_path.exists():
        return dll_path

    # Check dist directory (for development)
    dist_dll = exe_dir / "dist" / "FastFileOpShim.dll"
    if dist_dll.exists():
        return dist_dll

    return None


def register_dll(dll_path: Path) -> bool:
    """Register the DLL using regsvr32

    Requires administrator privileges.

    Args:
        dll_path: Path to the DLL file

    Returns:
        True if registration succeeded
    """
    if not is_admin():
        logger.warning("Cannot register DLL: administrator privileges required")
        return False

    if not dll_path.exists():
        logger.error(f"DLL not found: {dll_path}")
        return False

    try:
        # Use regsvr32 to register the DLL
        result = subprocess.run(
            ["regsvr32", "/s", str(dll_path)],
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(f"DLL registered successfully: {dll_path}")
            return True
        else:
            logger.error(f"DLL registration failed with code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("DLL registration timed out")
        return False
    except Exception as e:
        logger.error(f"DLL registration error: {e}")
        return False


def unregister_dll(dll_path: Path) -> bool:
    """Unregister the DLL using regsvr32

    Requires administrator privileges.

    Args:
        dll_path: Path to the DLL file

    Returns:
        True if unregistration succeeded
    """
    if not is_admin():
        logger.warning("Cannot unregister DLL: administrator privileges required")
        return False

    try:
        result = subprocess.run(
            ["regsvr32", "/s", "/u", str(dll_path)],
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(f"DLL unregistered successfully: {dll_path}")
            return True
        else:
            logger.error(f"DLL unregistration failed with code {result.returncode}")
            return False

    except Exception as e:
        logger.error(f"DLL unregistration error: {e}")
        return False


def run_as_admin(args: list[str] = None) -> bool:
    """Re-run the current script/executable with admin privileges

    Args:
        args: Additional command line arguments

    Returns:
        True if elevation request succeeded
    """
    if args is None:
        args = []

    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            exe = sys.executable
            params = ' '.join(args)
        else:
            # Running as script
            exe = sys.executable
            script = Path(__file__).parent.parent / "__main__.py"
            params = f'"{script}" ' + ' '.join(args)

        # Request elevation
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operation (run as admin)
            exe,            # executable
            params,         # parameters
            None,           # directory
            1,              # show command (SW_SHOWNORMAL)
        )

        # ShellExecuteW returns > 32 on success
        return result > 32

    except Exception as e:
        logger.error(f"Failed to request admin elevation: {e}")
        return False


def ensure_dll_registered(show_notification_callback=None) -> tuple[bool, str]:
    """Ensure the DLL is registered, attempt to register if not

    This function checks if the DLL is registered. If not, it will:
    1. If running as admin, register the DLL directly
    2. If not admin, return a status indicating admin is needed

    Args:
        show_notification_callback: Optional callback to show notification
            Signature: callback(title: str, message: str)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if DLL is already registered
    if is_dll_registered():
        logger.debug("DLL already registered")
        return True, "DLL already registered"

    # Find DLL
    dll_path = get_dll_path()
    if dll_path is None:
        logger.warning("FastFileOpShim.dll not found")
        return False, "DLL not found"

    logger.info(f"DLL found at: {dll_path}")

    # Check if we have admin privileges
    if is_admin():
        # Register directly
        if register_dll(dll_path):
            msg = "Shell extension registered successfully"
            if show_notification_callback:
                show_notification_callback("FastFileOp", msg)
            return True, msg
        else:
            msg = "Failed to register shell extension"
            if show_notification_callback:
                show_notification_callback("FastFileOp", msg)
            return False, msg
    else:
        # Need admin privileges
        msg = "Shell extension needs to be registered. Please run FastFileOp as Administrator once, or run install.bat."
        logger.warning(msg)

        if show_notification_callback:
            show_notification_callback(
                "FastFileOp - Registration Required",
                "Shell extension needs registration. Right-click FastFileOp.exe and select 'Run as administrator'."
            )

        return False, msg


def check_and_prompt_register() -> bool:
    """Check DLL registration and prompt user if needed

    This is a convenience function that can be called at startup.
    It will show a message box if registration is needed.

    Returns:
        True if DLL is registered (or was successfully registered)
    """
    if is_dll_registered():
        return True

    dll_path = get_dll_path()
    if dll_path is None:
        logger.debug("DLL not found, skipping registration check")
        return False

    # Show message box asking user to run as admin
    msg = (
        "FastFileOp shell extension is not registered.\n\n"
        "To enable drag-and-drop acceleration, please:\n"
        "1. Right-click FastFileOp.exe\n"
        "2. Select 'Run as administrator'\n\n"
        "Or run install.bat as administrator.\n\n"
        "The application will continue to run, but drag-and-drop "
        "operations will use the default Windows handler."
    )

    result = ctypes.windll.user32.MessageBoxW(
        0,  # No parent window
        msg,
        "FastFileOp - Registration Required",
        0x40 | 0x01  # MB_ICONINFORMATION | MB_OKCANCEL
    )

    # If user clicked OK, try to run as admin
    if result == 1:  # IDOK
        run_as_admin(["--register-dll"])
        return False

    return False
