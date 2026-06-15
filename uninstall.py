import ctypes, os, sys, shutil, subprocess
from pathlib import Path

INSTALL_DIR = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "FastFileOp"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

def main():
    if not is_admin():
        print("Requesting Administrator privileges...")
        run_as_admin()

    print("=" * 60)
    print("FastFileOp Uninstallation Script")
    print("=" * 60)
    print()
    print("WARNING: This will remove FastFileOp from your system.")
    print()
    input("Press Enter to continue...")

    # Step 1: Stop running process
    print("[Step 1/4] Stopping FastFileOp process...")
    subprocess.run(["taskkill", "/f", "/im", "FastFileOp.exe"], capture_output=True)
    print("FastFileOp process stopped.")
    import time
    time.sleep(2)

    # Step 2: Unregister shell extension
    print("[Step 2/4] Unregistering shell extension...")
    dll_path = INSTALL_DIR / "FastFileOpShim.dll"
    if dll_path.exists():
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(INSTALL_DIR) + os.pathsep + old_path
        try:
            dll = ctypes.WinDLL(str(dll_path))
            func = getattr(dll, "DllUnregisterServer@0")
            result = func()
            if result == 0:
                print("Shell extension unregistered.")
            else:
                print(f"WARNING: DllUnregisterServer returned {result}")
        except Exception as e:
            print(f"WARNING: Failed to unregister shell extension: {e}")
        finally:
            os.environ["PATH"] = old_path

    for key in [
        r"HKCR\Directory\ShellEx\CopyHookHandlers\FastFileOp",
        r"HKCR\Folder\ShellEx\CopyHookHandlers\FastFileOp",
        r"HKCR\*\ShellEx\ContextMenuHandlers\FastFileOp",
        r"HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOp",
        r"HKCR\Folder\ShellEx\ContextMenuHandlers\FastFileOp",
        r"HKCR\Directory\ShellEx\DragDropHandlers\FastFileOp",
        r"HKCR\Folder\ShellEx\DragDropHandlers\FastFileOp",
        r"HKCR\*\ShellEx\ContextMenuHandlers\FastFileOpDelete",
        r"HKCR\Directory\ShellEx\ContextMenuHandlers\FastFileOpDelete",
        r"HKCR\CLSID\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}",
        r"HKCR\CLSID\{B2C3D4E5-F6A7-8901-BCDE-F12345678901}",
        r"HKCR\CLSID\{C3D4E5F6-A7B8-9012-CDEF-123456789012}",
        r"HKCR\CLSID\{D4E5F6A7-B8C9-0123-DEF0-234567890123}",
    ]:
        subprocess.run(["reg", "delete", key, "/f"], capture_output=True)
    print()

    # Step 3: Remove auto-start entry
    print("[Step 3/4] Removing auto-start entry...")
    shortcut = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "FastFileOp.lnk"
    if shortcut.exists():
        shortcut.unlink()
        print("Auto-start entry removed.")
    else:
        print("No auto-start entry found.")
    print()

    # Step 4: Remove installation directory
    print("[Step 4/4] Removing installation directory...")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
        if not INSTALL_DIR.exists():
            print("Installation directory removed.")
        else:
            print("WARNING: Could not remove installation directory.")
            print("Some files may be in use. Please restart your computer and try again.")
    else:
        print("Installation directory not found.")
    print()

    print("=" * 60)
    print("Uninstallation complete!")
    print("=" * 60)
    print()
    print("FastFileOp has been removed from your system.")
    print()
    print(f"User config in %APPDATA%\\FastFileOp has been preserved.")
    print("To remove it too, manually delete that folder.")
    print()

    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
