"""FastFileOp - DLL Registration Module

Handles automatic registration of the shell extension DLL.
32-bit Python cannot load a 64-bit DLL via ctypes.WinDLL, so we
write registry keys directly instead of calling DllRegisterServer.
"""

import ctypes
import logging
import os
import sys
from pathlib import Path

import winreg

logger = logging.getLogger(__name__)

# CLSIDs (must match FastFileOpShim/stdafx.h)
CLSID_COPY_HOOK = "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
CLSID_CONTEXT_MENU = "{B2C3D4E5-F6A7-8901-BCDE-F12345678901}"
CLSID_DROP_TARGET = "{C3D4E5F6-A7B8-9012-CDEF-123456789012}"
CLSID_DELETE_COMMAND = "{D4E5F6A7-B8C9-0123-DEF0-234567890123}"

# ShellEx handler entries
_SHELLEX_ENTRIES = [
    # (handler_path, handler_name, clsid)
    (r"Directory\ShellEx\CopyHookHandlers", "FastFileOp", CLSID_COPY_HOOK),
    (r"Folder\ShellEx\CopyHookHandlers", "FastFileOp", CLSID_COPY_HOOK),
    (r"Directory\ShellEx\DragDropHandlers", "FastFileOp", CLSID_DROP_TARGET),
    (r"Folder\ShellEx\DragDropHandlers", "FastFileOp", CLSID_DROP_TARGET),
    (r"*\ShellEx\ContextMenuHandlers", "FastFileOp", CLSID_CONTEXT_MENU),
    (r"Directory\ShellEx\ContextMenuHandlers", "FastFileOp", CLSID_CONTEXT_MENU),
    (r"Folder\ShellEx\ContextMenuHandlers", "FastFileOp", CLSID_CONTEXT_MENU),
    (r"*\ShellEx\ContextMenuHandlers", "FastFileOpDelete", CLSID_DELETE_COMMAND),
    (r"Directory\ShellEx\ContextMenuHandlers", "FastFileOpDelete", CLSID_DELETE_COMMAND),
]

_CLSID_DESCRIPTIONS = {
    CLSID_COPY_HOOK: "FastFileOp CopyHook",
    CLSID_CONTEXT_MENU: "FastFileOp ContextMenu",
    CLSID_DROP_TARGET: "FastFileOp DropTarget",
    CLSID_DELETE_COMMAND: "FastFileOp DeleteCommand",
}

# Mapping from old-style check keys (used by is_dll_registered)
COPY_HOOK_KEY = r"Directory\ShellEx\CopyHookHandlers\FastFileOp"
DRAG_DROP_KEY = r"Directory\ShellEx\DragDropHandlers\FastFileOp"


def is_admin() -> bool:
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _get_reg_root():
    """Return HKLM when admin, else HKCU (for per-user fallback).

    Uses KEY_WOW64_64KEY so 32-bit Python writes to the 64-bit registry
    view that 64-bit Explorer will read.
    """
    access = winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
    if is_admin():
        return winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes", access
    return winreg.HKEY_CURRENT_USER, r"Software\Classes", access


def is_dll_registered() -> bool:
    """Check if any shell extension handler is registered"""
    try:
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
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent.parent

    dll_path = exe_dir / "FastFileOpShim.dll"
    if dll_path.exists():
        return dll_path

    dist_dll = exe_dir / "dist" / "FastFileOpShim.dll"
    if dist_dll.exists():
        return dist_dll

    return None


def _write_registry_key(root_key, sub_key, value_name, value, access=winreg.KEY_WRITE):
    """Create/overwrite a registry key and set a value."""
    try:
        with winreg.CreateKeyEx(root_key, sub_key, 0, access) as hkey:
            if value_name is None:
                winreg.SetValueEx(hkey, "", 0, winreg.REG_SZ, value)
            else:
                winreg.SetValueEx(hkey, value_name, 0, winreg.REG_SZ, value)
        return True
    except Exception as e:
        logger.error(f"Failed to write registry key {sub_key}: {e}")
        return False


def _delete_registry_key(root_key, sub_key):
    """Delete a registry key and all its subkeys."""
    try:
        winreg.DeleteKey(root_key, sub_key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        logger.warning(f"Failed to delete registry key {sub_key}: {e}")
        return False


def _register_clsid(root_key, classes_root, clsid, description, dll_path_str, access):
    """Register a single CLSID with InprocServer32."""
    clsid_path = rf"{classes_root}\CLSID\{clsid}"
    inproc_path = rf"{clsid_path}\InprocServer32"

    if not _write_registry_key(root_key, clsid_path, None, description, access):
        return False
    if not _write_registry_key(root_key, inproc_path, None, dll_path_str, access):
        return False
    if not _write_registry_key(root_key, inproc_path, "ThreadingModel", "Apartment", access):
        return False
    return True


def _unregister_clsid(root_key, classes_root, clsid):
    """Unregister a single CLSID and all subkeys."""
    clsid_path = rf"{classes_root}\CLSID\{clsid}"
    inproc_path = rf"{clsid_path}\InprocServer32"

    _delete_registry_key(root_key, inproc_path)
    _delete_registry_key(root_key, clsid_path)


def _register_shellex_handler(root_key, classes_root, handler_path, handler_name, clsid, access):
    """Register a single ShellEx handler entry."""
    full_path = rf"{classes_root}\{handler_path}\{handler_name}"
    return _write_registry_key(root_key, full_path, None, clsid, access)


def _unregister_shellex_handler(root_key, classes_root, handler_path, handler_name):
    """Unregister a single ShellEx handler entry."""
    full_path = rf"{classes_root}\{handler_path}\{handler_name}"
    _delete_registry_key(root_key, full_path)


def _regsvr32_register(dll_path_str):
    """Fallback: call regsvr32.exe to register the DLL.

    regsvr32 launches a separate process with matching bitness,
    so a 32-bit regsvr32 can register a 32-bit DLL and vice versa.
    However, for our 64-bit DLL, we need the 64-bit regsvr32.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["regsvr32", "/s", dll_path_str],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            logger.info("DLL registered via regsvr32 (64-bit)")
            return True
        logger.error(f"regsvr32 returned {result.returncode}")
        return False
    except Exception as e:
        logger.error(f"regsvr32 failed: {e}")
        return False


def register_dll(dll_path: Path) -> bool:
    """Register the shell extension DLL by writing registry keys directly.

    Directly writes CLSIDs and ShellEx handler entries to the registry.
    This works regardless of Python bitness vs DLL bitness.

    Requires administrator privileges (or writes to HKCU for per-user).
    """
    if not dll_path.exists():
        logger.error(f"DLL not found: {dll_path}")
        return False

    dll_path_str = str(dll_path.resolve())
    root_key, classes_root, access = _get_reg_root()

    try:
        # Register each CLSID
        for clsid, desc in _CLSID_DESCRIPTIONS.items():
            if not _register_clsid(root_key, classes_root, clsid, desc, dll_path_str, access):
                logger.error(f"Failed to register CLSID {clsid}")
                return False

        # Register each ShellEx handler
        for handler_path, handler_name, clsid in _SHELLEX_ENTRIES:
            if not _register_shellex_handler(root_key, classes_root, handler_path, handler_name, clsid, access):
                logger.error(f"Failed to register ShellEx {handler_path}\\{handler_name}")
                return False

        # Notify shell
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)

        logger.info(f"Shell extension registered successfully (keys under {classes_root})")
        return True

    except Exception as e:
        logger.error(f"DLL registration error: {e}")
        return False


def unregister_dll(dll_path: Path) -> bool:
    """Unregister the shell extension DLL by removing registry keys.

    Requires administrator privileges (or HKCU for per-user).
    """
    dll_path_str = str(dll_path.resolve()) if dll_path else ""
    root_key, classes_root, _access = _get_reg_root()

    try:
        # Unregister ShellEx handlers
        for handler_path, handler_name, clsid in _SHELLEX_ENTRIES:
            _unregister_shellex_handler(root_key, classes_root, handler_path, handler_name)

        # Unregister CLSIDs
        for clsid in _CLSID_DESCRIPTIONS:
            _unregister_clsid(root_key, classes_root, clsid)

        # Notify shell
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)

        logger.info(f"Shell extension unregistered successfully")
        return True

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
            exe = sys.executable
            params = ' '.join(args)
        else:
            exe = sys.executable
            script = Path(__file__).parent.parent / "__main__.py"
            params = f'"{script}" ' + ' '.join(args)

        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1,
        )
        return result > 32

    except Exception as e:
        logger.error(f"Failed to request admin elevation: {e}")
        return False


def ensure_dll_registered(show_notification_callback=None) -> tuple[bool, str]:
    """Ensure the DLL is registered, attempt to register if not"""
    if is_dll_registered():
        logger.debug("DLL already registered")
        return True, "DLL already registered"

    dll_path = get_dll_path()
    if dll_path is None:
        logger.warning("FastFileOpShim.dll not found")
        return False, "DLL not found"

    logger.info(f"DLL found at: {dll_path}")

    if is_admin():
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
        msg = ("Shell extension needs to be registered. "
               "Please run FastFileOp as Administrator once, or run install.bat.")
        logger.warning(msg)

        if show_notification_callback:
            show_notification_callback(
                "FastFileOp - Registration Required",
                "Shell extension needs registration. "
                "Right-click FastFileOp.exe and select 'Run as administrator'."
            )

        return False, msg


def check_and_prompt_register() -> bool:
    """Check DLL registration and prompt user if needed"""
    if is_dll_registered():
        return True

    dll_path = get_dll_path()
    if dll_path is None:
        logger.debug("DLL not found, skipping registration check")
        return False

    msg = (
        "FastFileOp shell extension is not registered.\n\n"
        "To enable drag-and-drop and context menu acceleration, please:\n"
        "1. Right-click FastFileOp.exe\n"
        "2. Select 'Run as administrator'\n\n"
        "Or run install.bat as administrator.\n\n"
        "The application will continue to run, but Explorer operations "
        "will use the default Windows handler."
    )

    result = ctypes.windll.user32.MessageBoxW(
        0, msg,
        "FastFileOp - Registration Required",
        0x40 | 0x01,
    )

    if result == 1:
        run_as_admin(["--register-dll"])
        return False

    return False
