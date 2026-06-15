"""Centralized constants and limits for FastFileOp."""

# ── Buffer ─────────────────────────────────────────────────
BUFFER_SIZE_DEFAULT_MB: int = 64
BUFFER_SIZE_MIN_MB: int = 32
BUFFER_SIZE_MAX_MB: int = 512

# ── Threading ──────────────────────────────────────────────
WORKER_THREADS_DEFAULT: int = 4
WORKER_THREADS_MIN: int = 1
WORKER_THREADS_MAX: int = 8

# ── Named Pipe ─────────────────────────────────────────────
PIPE_NAME: str = r"\\.\pipe\FastFileOpPipe"
PIPE_BUFFER_SIZE: int = 65536
PIPE_MAX_INSTANCES: int = 4

# ── Pipe Watchdog ──────────────────────────────────────────
WATCHDOG_WINDOW_SECONDS: int = 30
WATCHDOG_MAX_DISCONNECTS: int = 3
WATCHDOG_RECONNECT_DELAY: float = 2.0

# ── Secure Delete ──────────────────────────────────────────
SECURE_DELETE_PASSES: int = 3
SECURE_DELETE_CHUNK_MAX: int = 1048576
SECURE_DELETE_FLUSH_INTERVAL: int = 8

# ── Progress UI ────────────────────────────────────────────
PROGRESS_WINDOW_WIDTH: int = 500
PROGRESS_WINDOW_HEIGHT: int = 220
PROGRESS_UPDATE_THROTTLE: float = 0.15
PROGRESS_POLL_INTERVAL: int = 50
PROGRESS_INITIAL_DELAY: float = 0.2
PROGRESS_FILENAME_MAX_CHARS: int = 55

# ── Tray ───────────────────────────────────────────────────
TRAY_ICON_SIZE: int = 64
TRAY_LOG_TAIL_BYTES: int = 16384
TRAY_RESTART_DELAY: float = 2.0

# ── Logger ─────────────────────────────────────────────────
LOG_ROTATION_INTERVAL_DAYS: int = 1
LOG_RETENTION_DAYS: int = 7

# ── Notifications ──────────────────────────────────────────
NOTIFICATION_PS_TIMEOUT: int = 10

# ── Timing ─────────────────────────────────────────────────
ACTION_QUEUE_POLL_INTERVAL: float = 0.5
ACTION_THREAD_JOIN_TIMEOUT: float = 2.0
PAUSE_LOOP_SLEEP: float = 0.05
PAUSE_WORKER_SLEEP: float = 0.1
PIPE_THREAD_JOIN_TIMEOUT: int = 2

# ── File Size Display Thresholds ───────────────────────────
SIZE_KB: int = 1024
SIZE_MB: int = 1048576
SIZE_GB: int = 1073741824

# ── Move File Flags (Windows API) ──────────────────────────
MOVEFILE_REPLACE_EXISTING: int = 0x1
MOVEFILE_WRITE_THROUGH: int = 0x8

# ── Clipboard ──────────────────────────────────────────────
CF_HDROP: int = 15
DROPEFFECT_COPY: int = 1
DROPEFFECT_MOVE: int = 2

# ── Keyboard Hook ──────────────────────────────────────────
WH_KEYBOARD_LL: int = 13
WM_KEYDOWN: int = 0x0100
WM_KEYUP: int = 0x0101
WM_SYSKEYDOWN: int = 0x0104
WM_SYSKEYUP: int = 0x0105
VK_DELETE: int = 0x2E
VK_V: int = 0x56
VK_CONTROL: int = 0x11
VK_SHIFT: int = 0x10
VK_LSHIFT: int = 0xA0
VK_RSHIFT: int = 0xA1
EXPLORER_CLASSES: set = {"CabinetWClass", "ExploreWClass"}

# ── DLL Registration ───────────────────────────────────────
COPY_HOOK_KEY: str = r"Directory\shellex\CopyHookHandlers\FastFileOp"
DRAG_DROP_KEY: str = r"Directory\shellex\DragDropHandlers\FastFileOp"
CLSID_KEY: str = r"CLSID\{12345678-1234-1234-1234-123456789ABC}"

# ── Engine ─────────────────────────────────────────────────
BUFFER_SIZE_DEFAULT_BYTES: int = BUFFER_SIZE_DEFAULT_MB * SIZE_MB
