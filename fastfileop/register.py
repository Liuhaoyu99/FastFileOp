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
        # Determine correct regsvr32 path. Use DLL PE header to detect whether
        # the DLL is 32-bit or 64-bit, and choose the corresponding regsvr32
        # executable on 64-bit Windows. If detection fails, try System32 first
        # then SysWOW64 as a fallback.
        import platform

        def _is_pe64(path: Path) -> Optional[bool]:
            """Return True if PE is 64-bit, False if 32-bit, None on failure."""
            try:
                with open(path, 'rb') as f:
                    data = f.read(0x100)
                    if len(data) < 0x40:
                        return None
                    # e_lfanew at offset 0x3C (little-endian 4 bytes)
                    e_lfanew = int.from_bytes(data[0x3C:0x40], 'little')
                    f.seek(e_lfanew + 4)
                    # Machine field is 2 bytes at IMAGE_FILE_HEADER
                    machine = int.from_bytes(f.read(2), 'little')
                    # IMAGE_FILE_MACHINE_AMD64 = 0x8664, IMAGE_FILE_MACHINE_I386 = 0x014c
                    if machine == 0x8664:
                        return True
                    if machine == 0x014c:
                        return False
                    return None
            except Exception:
                return None

        dll_is_64 = _is_pe64(dll_path)

        # Helper to run regsvr32 and capture output
        def _run_regsvr32(cmd_path: str) -> subprocess.CompletedProcess:
            return subprocess.run([cmd_path, "/s", str(dll_path)], capture_output=True, timeout=30)

        windir = os.environ.get('WINDIR', r'C:\Windows')
        tried = []

        # If on 64-bit OS, prefer matching regsvr32 based on dll bitness
        if platform.machine().endswith('64'):
            if dll_is_64 is True:
                candidates = [os.path.join(windir, 'System32', 'regsvr32.exe'), os.path.join(windir, 'SysWOW64', 'regsvr32.exe')]
            elif dll_is_64 is False:
                candidates = [os.path.join(windir, 'SysWOW64', 'regsvr32.exe'), os.path.join(windir, 'System32', 'regsvr32.exe')]
            else:
                # Unknown bitness; try System32 then SysWOW64
                candidates = [os.path.join(windir, 'System32', 'regsvr32.exe'), os.path.join(windir, 'SysWOW64', 'regsvr32.exe')]
        else:
            candidates = ['regsvr32.exe']

        last_err = None
        for reg in candidates:
            tried.append(reg)
            logger.info(f"Attempting registration with: {reg}")
            try:
                res = _run_regsvr32(reg)
            except subprocess.TimeoutExpired:
                logger.error(f"regsvr32 timed out for {reg}")
                last_err = 'timeout'
                continue
            except FileNotFoundError:
                logger.warning(f"regsvr32 not found at: {reg}")
                last_err = 'notfound'
                continue

                if res.returncode == 0:
                    logger.info(f"DLL registered successfully with {reg}: {dll_path}")
                    return True
                else:
                    stdout_out = res.stdout.decode('mbcs', errors='replace').strip()
                    stderr_out = res.stderr.decode('mbcs', errors='replace').strip()
                    logger.error(f"regsvr32 ({reg}) failed with code {res.returncode}")
                    if stdout_out:
                        logger.error(f"  stdout: {stdout_out}")
                    if stderr_out:
                        logger.error(f"  stderr: {stderr_out}")
                    # Append detailed output to install log for diagnostics
                    try:
                        log_path = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', r'C:\Windows\Temp')), 'fastfileop_install.log')
                        with open(log_path, 'a', encoding='utf-8') as lf:
                            lf.write(f"\n=== regsvr32 attempt: {reg} ===\n")
                            lf.write(f"returncode: {res.returncode}\n")
                            if stdout_out:
                                lf.write(f"stdout:\n{stdout_out}\n")
                            if stderr_out:
                                lf.write(f"stderr:\n{stderr_out}\n")
                    except Exception:
                        pass
                    last_err = stderr_out or stdout_out or str(res.returncode)

        logger.error(f"DLL registration failed after trying: {tried}")
        if last_err:
            logger.error(f"Last error: {last_err}")
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

    if not dll_path.exists():
        logger.error(f"DLL not found: {dll_path}")
        return False

    try:
        import platform

        def _is_pe64(path: Path) -> Optional[bool]:
            """Return True if PE is 64-bit, False if 32-bit, None on failure."""
            try:
                with open(path, 'rb') as f:
                    data = f.read(0x100)
                    if len(data) < 0x40:
                        return None
                    e_lfanew = int.from_bytes(data[0x3C:0x40], 'little')
                    f.seek(e_lfanew + 4)
                    machine = int.from_bytes(f.read(2), 'little')
                    if machine == 0x8664:
                        return True
                    if machine == 0x014c:
                        return False
                    return None
            except Exception:
                return None

        dll_is_64 = _is_pe64(dll_path)

        def _run_regsvr32(cmd_path: str) -> subprocess.CompletedProcess:
            return subprocess.run([cmd_path, "/s", "/u", str(dll_path)], capture_output=True, timeout=30)

        windir = os.environ.get('WINDIR', r'C:\Windows')
        tried = []

        if platform.machine().endswith('64'):
            if dll_is_64 is True:
                candidates = [os.path.join(windir, 'System32', 'regsvr32.exe'), os.path.join(windir, 'SysWOW64', 'regsvr32.exe')]
            elif dll_is_64 is False:
                candidates = [os.path.join(windir, 'SysWOW64', 'regsvr32.exe'), os.path.join(windir, 'System32', 'regsvr32.exe')]
            else:
                candidates = [os.path.join(windir, 'System32', 'regsvr32.exe'), os.path.join(windir, 'SysWOW64', 'regsvr32.exe')]
        else:
            candidates = ['regsvr32.exe']

        last_err = None
        for reg in candidates:
            tried.append(reg)
            logger.info(f"Attempting unregistration with: {reg}")
            try:
                res = _run_regsvr32(reg)
            except subprocess.TimeoutExpired:
                logger.error(f"regsvr32 timed out for {reg}")
                last_err = 'timeout'
                continue
            except FileNotFoundError:
                logger.warning(f"regsvr32 not found at: {reg}")
                last_err = 'notfound'
                continue

            if res.returncode == 0:
                logger.info(f"DLL unregistered successfully with {reg}: {dll_path}")
                return True
            else:
                stdout_out = res.stdout.decode('mbcs', errors='replace').strip()
                stderr_out = res.stderr.decode('mbcs', errors='replace').strip()
                logger.error(f"regsvr32 ({reg}) failed with code {res.returncode}")
                if stdout_out:
                    logger.error(f"  stdout: {stdout_out}")
                if stderr_out:
                    logger.error(f"  stderr: {stderr_out}")
                last_err = stderr_out or stdout_out or str(res.returncode)

        logger.error(f"DLL unregistration failed after trying: {tried}")
        if last_err:
            logger.error(f"Last error: {last_err}")
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
