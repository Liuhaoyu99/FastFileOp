# FastFileOp

**Replace Windows default copy, move & delete with a high-speed multi-threaded engine. 2.5–4× faster.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)

## Features

- 🚀 **High-Speed File Operations** - Multi-threaded engine with 64MB buffer, achieving 318 MB/s on SSDs
- ⌨️ **Keyboard Hook Integration** - Seamlessly intercepts Ctrl+C/X/V and Delete keys in Explorer
- 🔄 **Shell Extension DLL** - C++ COM component for drag & drop interception
- 📊 **System Tray UI** - Real-time status, pause/resume, settings GUI
- 🔁 **Auto-Start Support** - Automatically launches with Windows
- 🛡️ **Watchdog Mechanism** - Auto-recovery from pipe disconnections
- 🗑️ **Secure Delete** - 3-pass overwrite for permanent deletion
- ⏯️ **Operation Control** - Pause, resume, and cancel ongoing operations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Windows Explorer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Ctrl+C/V   │  │   Delete    │  │    Drag & Drop          │  │
│  │   Keys      │  │    Key      │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastFileOp Components                          │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ Keyboard Hook│    │  Shell Ext.  │    │   Clipboard      │   │
│  │  (Python)    │    │  DLL (C++)   │    │   Monitor        │   │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘   │
│         │                   │                     │             │
│         │                   ▼                     │             │
│         │         ┌──────────────────┐            │             │
│         │         │   Named Pipe     │            │             │
│         │         │ \\.\pipe\FFOPipe │            │             │
│         │         └────────┬─────────┘            │             │
│         │                  │                      │             │
│         ▼                  ▼                      ▼             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    File Engine                           │   │
│  │         (Multi-threaded, 64MB Buffer)                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │
│  │  │  Copy   │  │  Move   │  │ Delete  │  │   Secure    │  │   │
│  │  │         │  │         │  │(Recycle)│  │   Delete    │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│  ┌───────────────────────────┴───────────────────────────┐     │
│  │                   System Tray                          │     │
│  │    Status │ Pause/Resume │ Settings │ Exit            │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Comparison

| Metric | FastFileOp | Windows Default | Improvement |
|--------|------------|-----------------|-------------|
| 100MB Copy Speed | **318 MB/s** | ~80-120 MB/s | **2.5-4× faster** |
| Buffer Size | 64 MB | 8-64 KB | Fewer syscalls |
| Worker Threads | 4 (configurable) | 1 | Parallel I/O |
| Large File Copy | Optimized | Standard | Significant |

### Benchmark Results

```
Test: 100MB file copy on NVMe SSD
FastFileOp: 0.31s (318.4 MB/s)
Windows Default: ~1.0-1.2s (~80-100 MB/s)
```

## Installation

### Prerequisites

- Windows 10/11 (64-bit)
- Python 3.11+ (for running from source)
- MinGW-w64 (for building DLL from source)

### Quick Install

1. Download the latest release
2. Run `install.bat` as Administrator
3. Restart Windows Explorer (or log off/on)

```batch
# Run as Administrator
install.bat
```

### Manual Install

```batch
# 1. Build the executable
build.bat

# 2. Install to Program Files
install.bat

# 3. Register the Shell Extension
regsvr32 "C:\Program Files\FastFileOp\FastFileOpShim.dll"
```

## Uninstallation

```batch
# Run as Administrator
uninstall.bat
```

This will:
- Unregister the Shell Extension DLL
- Remove files from Program Files
- Clean up registry entries
- Remove auto-start entry

## Antivirus Whitelist

Some antivirus software (e.g., 360, Windows Defender) may flag the keyboard hook or Shell Extension as suspicious. To resolve:

### 360 Security

1. Open 360 Security Center
2. Go to **Virus Scan** → **Trusted Zone**
3. Add these files to whitelist:
   - `C:\Program Files\FastFileOp\FastFileOp.exe`
   - `C:\Program Files\FastFileOp\FastFileOpShim.dll`

### Windows Defender

1. Open Windows Security
2. Go to **Virus & threat protection** → **Exclusions**
3. Add the FastFileOp folder

## Known Limitations

1. **Drag & Drop** requires the C++ Shell Extension DLL to be registered
2. **Administrator privileges** required for installation
3. **Antivirus software** may detect keyboard hooks as keyloggers (false positive)
4. **UAC prompts** may appear during installation
5. **Some applications** with custom drag handlers may not be intercepted

## Technical Stack

| Component | Technology |
|-----------|------------|
| Backend Engine | Python 3.11+ |
| Shell Extension | C++ (Win32 API, COM) |
| IPC | Named Pipes |
| Keyboard Hook | WH_KEYBOARD_LL |
| Clipboard | CF_HDROP format |
| GUI | tkinter + pystray |
| Build | PyInstaller + MinGW-w64 |

## Project Structure

```
FastFileOp/
├── fastfileop/              # Python package
│   ├── __main__.py          # Entry point
│   ├── engine.py            # File operation engine
│   ├── pipe_server.py       # Named pipe server
│   ├── hook.py              # Keyboard hook
│   ├── clipboard.py         # Clipboard monitor
│   ├── tray.py              # System tray
│   ├── config.py            # Configuration
│   └── settings.py          # Settings GUI
├── FastFileOpShim/          # C++ Shell Extension
│   ├── CopyHook.cpp         # ICopyHook implementation
│   ├── PipeClient.cpp       # Named pipe client
│   └── dllmain.cpp          # DLL entry
├── tests/                   # Test suite
│   ├── test_engine.py       # Engine unit tests
│   ├── test_pipe.py         # Pipe communication tests
│   └── test_manual_guide.md # Manual testing guide
├── build.bat                # Build script
├── install.bat              # Installation script
├── uninstall.bat            # Uninstallation script
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Development

### Build from Source

```batch
# Build Python executable
python -m PyInstaller --onefile --windowed --name FastFileOp main.py

# Build C++ DLL (requires MinGW-w64)
g++ -shared -o FastFileOpShim.dll -static-libgcc -static-libstdc++ ^
    FastFileOpShim/*.cpp -lole32 -lshell32 -luuid -luser32
```

### Run Tests

```batch
# Engine tests
python tests/test_engine.py

# Pipe tests (requires running server)
python -m fastfileop
python tests/test_pipe.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Liu Haoyu (BakerLiu)**

---

⭐ If this project helped you, please give it a star!
