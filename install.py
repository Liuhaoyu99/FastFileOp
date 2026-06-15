import ctypes, os, sys, shutil, subprocess
from pathlib import Path

INSTALL_DIR = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "FastFileOp"
SCRIPT_DIR = Path(sys.argv[0]).parent.resolve()
INSTALL_LOG = Path(os.environ["TEMP"]) / "fastfileop_install.log"

def log(msg):
    with open(INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

def find_src(name):
    for base in [SCRIPT_DIR, SCRIPT_DIR / "dist"]:
        p = base / name
        if p.exists():
            return p
    return None

def main():
    if not is_admin():
        print("Requesting Administrator privileges...")
        run_as_admin()

    print("=" * 60)
    print("FastFileOp Installation Script")
    print("=" * 60)
    print()
    print(f"Installing to: {INSTALL_DIR}")
    print()

    log(f"===== FastFileOp install started =====")
    log(f"Installing to: {INSTALL_DIR}")

    # Step 1: Check source files
    print("[Step 1/5] Checking source files...")
    src_exe = find_src("FastFileOp.exe")
    src_dll = find_src("FastFileOpShim.dll")
    src_gcc = find_src("libgcc_s_dw2-1.dll")
    src_pthread = find_src("libwinpthread-1.dll")

    if not src_exe:
        print("ERROR: FastFileOp.exe not found!")
        log("ERROR: FastFileOp.exe not found!")
        input("Press Enter to exit...")
        sys.exit(1)

    skip_dll = src_dll is None
    if skip_dll:
        print("WARNING: FastFileOpShim.dll not found, skipping shell extension.")
        log("WARNING: FastFileOpShim.dll not found, skipping shell extension.")

    print("Source files OK.")
    print()

    # Step 2: Create installation directory
    print("[Step 2/5] Creating installation directory...")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    print("Installation directory created.")
    print()

    # Step 3: Copy files
    print("[Step 3/5] Copying files...")
    shutil.copy2(src_exe, INSTALL_DIR / "FastFileOp.exe")

    if not skip_dll:
        shutil.copy2(src_dll, INSTALL_DIR / "FastFileOpShim.dll")
        if src_gcc:
            shutil.copy2(src_gcc, INSTALL_DIR / "libgcc_s_dw2-1.dll")
        if src_pthread:
            shutil.copy2(src_pthread, INSTALL_DIR / "libwinpthread-1.dll")

    for doc in ["README.md", "README_zh.md", "LICENSE", "benchmark.png"]:
        src = find_src(doc)
        if src:
            shutil.copy2(src, INSTALL_DIR / doc)

    print("Files copied successfully.")
    print()

    # Step 4: Register shell extension
    print("[Step 4/5] Registering shell extension...")
    if skip_dll:
        print("Skipping shell extension registration.")
    else:
        dll_path = INSTALL_DIR / "FastFileOpShim.dll"
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(INSTALL_DIR) + os.pathsep + old_path
        try:
            dll = ctypes.WinDLL(str(dll_path))
            func = getattr(dll, "DllRegisterServer@0")
            result = func()
            if result == 0:
                print("Shell extension registered.")
                log("Shell extension registered.")
            else:
                raise RuntimeError(f"DllRegisterServer returned {result}")
        except Exception as e:
            print(f"WARNING: Failed to register shell extension: {e}")
            print("The application will still work, but drag-and-drop interception may not function.")
            log(f"WARNING: Failed to register shell extension: {e}")
        finally:
            os.environ["PATH"] = old_path
    print()

    # Step 5: Register auto-start and launch
    print("[Step 5/5] Configuring auto-start and launching...")
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)
    exe_path = str(INSTALL_DIR / "FastFileOp.exe")
    shortcut_path = str(startup_dir / "FastFileOp.lnk")
    ps_cmd = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}');"
        f"$s.TargetPath='{exe_path}';$s.Arguments='--silent';"
        f"$s.WorkingDirectory='{INSTALL_DIR}';$s.Save()"
    )
    result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
    if result.returncode == 0:
        print("Auto-start configured.")
    else:
        print("WARNING: Failed to configure auto-start.")
    print()

    print("Starting FastFileOp...")
    subprocess.Popen([str(INSTALL_DIR / "FastFileOp.exe")], shell=True)

    print()
    print("=" * 60)
    print("Installation complete!")
    print("=" * 60)
    print()
    print(f"Location: {INSTALL_DIR}")
    print()
    print("To uninstall, run uninstall.exe as Administrator.")
    print()

    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
