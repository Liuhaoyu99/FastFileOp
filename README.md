# FastFileOp - High-Speed File Operations for Windows

Replace Windows default file copy/move/delete with a custom high-speed multi-threaded engine.

## Architecture

```
+-------------------+          Named Pipe          +-------------------+
|                   |   \\.\pipe\FastFileOpPipe   |                   |
|  FastFileOpShim   |<--------------------------->|   Python Service  |
|  (C++ Shell Ext)  |         JSON Messages        |   (FastFileOp)    |
|                   |                              |                   |
+-------------------+                              +-------------------+
        |                                                   |
        | Intercepts:                                       | Components:
        | - Copy/Move (ICopyHook)                          | - FileEngine
        | - Paste (IContextMenu)                           | - KeyboardHook
        | - Drag (IDropTarget)                             | - PipeServer
        | - Delete (IExplorerCommand)                      | - TrayIcon
        v                                                   v
+-------------------+                              +-------------------+
| Windows Explorer  |                              |   File System     |
+-------------------+                              +-------------------+

+-------------------+
| Keyboard Hook     |  (Python - WH_KEYBOARD_LL)
| - Ctrl+V          |
| - Delete          |
| - Shift+Delete    |
+-------------------+
```

## Features

- **High-Speed Engine**: Multi-threaded file operations with configurable buffer size (32MB-512MB)
- **Smart Move**: Same-drive uses rename, cross-drive uses copy+delete
- **Secure Delete**: 3-pass overwrite for permanent deletion
- **Dual Interception**: Both C++ Shell Extension and Python keyboard hook
- **System Tray**: Status indicator with pause/resume and settings
- **Named Pipe IPC**: Communication between C++ DLL and Python service

## Project Structure

```
fastfileop/
├── fastfileop/              # Python package
│   ├── __init__.py
│   ├── __main__.py          # Main entry point
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging with daily rotation
│   ├── engine.py            # High-speed file operation engine
│   ├── pipe_server.py       # Named pipe server
│   ├── hook.py              # Global keyboard hook
│   ├── clipboard.py         # Clipboard monitoring
│   ├── shell.py             # Shell COM integration
│   ├── tray.py              # System tray icon
│   └── settings.py          # Settings window
│
├── FastFileOpShim/          # C++ Shell Extension
│   ├── FastFileOpShim.sln
│   ├── FastFileOpShim.vcxproj
│   ├── *.h / *.cpp
│   ├── *.rgs
│   ├── install.bat
│   └── uninstall.bat
│
├── requirements.txt
├── FastFileOp.spec          # PyInstaller config
└── README.md
```

## Installation

### Python Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python -m fastfileop
```

### C++ Shell Extension

1. Open `FastFileOpShim/FastFileOpShim.sln` in Visual Studio 2022
2. Build in `Release | x64` configuration
3. Run `install.bat` as Administrator
4. Restart Explorer or log off/on

## Usage

1. Start the Python service (runs in system tray)
2. Optionally install the C++ Shell Extension for drag/drop interception
3. Use Ctrl+C/X/V or Delete in Windows Explorer
4. Operations are intercepted and handled by FastFileOp

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+C then Ctrl+V | Copy files |
| Ctrl+X then Ctrl+V | Move files |
| Delete | Move to recycle bin |
| Shift+Delete | Permanent delete (3-pass overwrite) |

## Configuration

Config file: `%APPDATA%\FastFileOp\config.json`

| Setting | Default | Description |
|---------|---------|-------------|
| buffer_size_mb | 64 | Read/write buffer size (32-512 MB) |
| worker_threads | 4 | Number of concurrent threads |
| hook_copy | true | Intercept copy/move operations |
| hook_delete | true | Intercept delete operations |
| hook_drag | true | Intercept drag operations (requires DLL) |
| auto_start | false | Start with Windows |
| debug_mode | false | Enable verbose logging |

## Logs

Logs are stored in `%APPDATA%\FastFileOp\logs\` with daily rotation, keeping the last 7 days.

## Building with PyInstaller

```bash
pyinstaller FastFileOp.spec
```

Output: `dist/FastFileOp.exe`

## Known Limitations

1. **Drag & Drop**: Requires C++ Shell Extension; Python hook cannot intercept drag operations
2. **ICopyHook**: Only intercepts folder operations, not individual files
3. **Third-party File Managers**: Only works with Windows Explorer (CabinetWClass/ExploreWClass)
4. **UAC Files**: Cannot operate on files requiring administrator privileges
5. **Locked Files**: Files locked by other processes cannot be operated on
6. **Network Paths**: UNC paths may have limited support
7. **Long Paths**: Paths over 260 characters may require special handling
8. **Keyboard Hook Conflicts**: May conflict with other applications using global hooks

## Dependencies

- Python 3.11+
- pywin32 - Windows API access
- pystray - System tray icon
- Pillow - Image processing (pystray dependency)
- send2trash - Move files to recycle bin

## License

MIT License
