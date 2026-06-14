"""FastFileOp - Main Entry Module

Coordinates all components:
1. System tray icon
2. Global keyboard hook
3. Named pipe server
4. File operation engine
5. Watchdog for instability detection
"""

import argparse
import logging
import queue
import sys
import threading
import time

from .clipboard import ClipboardMonitor
from .config import ConfigManager
from .engine import FileEngine, OpState
from .hook import KeyboardHook
from .logger import configure_root_logger, set_debug_mode
from .pipe_server import PipeServer
from .shell import ShellHelper
from .settings import SettingsWindow
from .tray import TrayIcon

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="FastFileOp - High-Speed File Operations")
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Silent mode - start minimized to tray (for auto-start)",
    )
    return parser.parse_args()


class FastFileOpApp:
    """FastFileOp main application

    Coordinates:
    - System tray icon
    - Global keyboard hook (Ctrl+V, Delete)
    - Named pipe server (DLL communication)
    - File operation engine
    - Watchdog for instability detection
    """

    def __init__(self, silent: bool = False):
        self._silent = silent

        # Initialize configuration
        self.config_manager = ConfigManager()
        self.config_manager.load()

        # Configure logging
        configure_root_logger(self.config_manager.config.debug_mode)

        # Components
        self.action_queue: queue.Queue = queue.Queue()
        self.clipboard = ClipboardMonitor()
        self.shell = ShellHelper()
        self.engine: FileEngine = None
        self._engine_lock = threading.Lock()
        self._running = True
        self._instability_detected = False

        # Keyboard hook
        self.hook = KeyboardHook(
            action_queue=self.action_queue,
            is_hooking_enabled=self._is_hooking_enabled,
        )

        # System tray
        self.tray = TrayIcon(
            config_manager=self.config_manager,
            on_settings=self._open_settings,
            on_exit=self._quit,
            on_toggle_pause=self._on_pause_toggle,
            on_resume_interception=self._on_resume_interception,
        )

        # Named pipe server with watchdog
        self.pipe_server = PipeServer(
            engine_factory=self._create_engine,
            on_instability=self._on_instability_detected,
        )

    def _is_hooking_enabled(self) -> bool:
        """Check if hooking is enabled"""
        # Also check for instability
        if self._instability_detected:
            return False
        return self.config_manager.is_hooking_enabled()

    def _on_pause_toggle(self, paused: bool):
        """Handle pause toggle from tray"""
        logger.info(f"Interception {'paused' if paused else 'resumed'}")

    def _on_resume_interception(self):
        """Handle manual resume from instability"""
        logger.info("Manual resume from instability")
        self._instability_detected = False
        self.config_manager.update(paused=False)
        self.pipe_server.reset_watchdog()
        self.tray.update_instability_status(False)

    def _on_instability_detected(self):
        """Handle instability detected by watchdog"""
        logger.error("Instability detected by watchdog - pausing interception")

        self._instability_detected = True
        self.config_manager.update(paused=True)

        # Update tray status
        self.tray.update_instability_status(True)

        # Show notification
        self.tray.show_notification(
            "FastFileOp - Instability Detected",
            "Interception paused due to instability. Check logs for details. Use tray menu to resume."
        )

    def _open_settings(self):
        """Open settings window in separate thread"""
        def _show():
            settings = SettingsWindow(self.config_manager)
            settings.show()

        thread = threading.Thread(target=_show, daemon=True)
        thread.start()

    def _quit(self):
        """Quit application"""
        logger.info("Shutting down FastFileOp...")
        self._running = False
        self.hook.stop()
        self.pipe_server.stop()
        self.tray.stop()

    def _create_engine(self) -> FileEngine:
        """Create file engine with current config"""
        config = self.config_manager.config
        return FileEngine(
            buffer_size=config.buffer_size,
            max_workers=config.worker_threads,
            progress_callback=self._on_progress,
        )

    def _on_progress(self, current_file: str, file_index: int, total_files: int,
                     bytes_done: int, bytes_total: int):
        """Progress callback for file operations"""
        if bytes_total > 0:
            pct = bytes_done / bytes_total * 100
            logger.debug(f"Progress: {pct:.1f}% ({file_index}/{total_files}) - {current_file}")

    def _handle_paste(self):
        """Handle paste operation (Ctrl+V)"""
        config = self.config_manager.config

        # Check if copy/move hook is enabled
        if not config.hook_copy:
            KeyboardHook.send_paste()
            return

        # Get clipboard files
        result = self.clipboard.get_clipboard_files()
        if result is None:
            # No files in clipboard, forward original keystroke
            KeyboardHook.send_paste()
            return

        files, is_cut = result
        if not files:
            KeyboardHook.send_paste()
            return

        # Get target directory
        hwnd = KeyboardHook.get_foreground_explorer_hwnd()
        dst_dir = self.shell.get_current_directory(hwnd) if hwnd else None

        if not dst_dir:
            logger.warning("Cannot get target directory, forwarding original paste")
            KeyboardHook.send_paste()
            return

        # Execute operation
        with self._engine_lock:
            self.engine = self._create_engine()

        def _run():
            try:
                if is_cut:
                    logger.info(f"Hook: Move {len(files)} items -> {dst_dir}")
                    self.engine.move(files, dst_dir)
                else:
                    logger.info(f"Hook: Copy {len(files)} items -> {dst_dir}")
                    self.engine.copy(files, dst_dir)

                failed = self.engine.get_failed()
                if failed:
                    logger.warning(f"Operation completed with {len(failed)} failures")
                    for fp in failed:
                        logger.warning(f"  Failed: {fp.src} - {fp.error}")
            except Exception as e:
                logger.error(f"File operation error: {e}")
            finally:
                with self._engine_lock:
                    self.engine = None

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _handle_delete(self, shift_pressed: bool):
        """Handle delete operation (Delete / Shift+Delete)"""
        config = self.config_manager.config

        # Check if delete hook is enabled
        if not config.hook_delete:
            KeyboardHook.send_delete()
            return

        # Get selected files
        hwnd = KeyboardHook.get_foreground_explorer_hwnd()
        files = self.shell.get_selected_files(hwnd) if hwnd else []

        if not files:
            logger.debug("No files selected, forwarding original delete")
            KeyboardHook.send_delete()
            return

        permanent = shift_pressed

        with self._engine_lock:
            self.engine = self._create_engine()

        def _run():
            try:
                mode = "permanent" if permanent else "recycle"
                logger.info(f"Hook: Delete {len(files)} items ({mode})")
                self.engine.delete(files, permanent=permanent)

                failed = self.engine.get_failed()
                if failed:
                    logger.warning(f"Delete completed with {len(failed)} failures")
                    for fp in failed:
                        logger.warning(f"  Failed: {fp.src} - {fp.error}")
            except Exception as e:
                logger.error(f"Delete operation error: {e}")
            finally:
                with self._engine_lock:
                    self.engine = None

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _process_actions(self):
        """Main action processing loop"""
        while self._running:
            try:
                action, param = self.action_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if action == "paste":
                    self._handle_paste()
                elif action == "delete":
                    self._handle_delete(param)
                else:
                    logger.warning(f"Unknown action: {action}")
            except Exception as e:
                logger.error(f"Action processing error: {e}")

    def run(self):
        """Run the application"""
        logger.info("=" * 50)
        logger.info("FastFileOp starting...")
        if self._silent:
            logger.info("Mode: Silent (auto-start)")
        logger.info("=" * 50)

        # Check for existing instance
        if PipeServer.is_server_running():
            logger.error("Another instance is already running!")
            print("Error: FastFileOp is already running.", file=sys.stderr)
            sys.exit(1)

        # Ensure auto-start is registered (first run)
        first_run = self.config_manager.ensure_auto_start_registered()
        if first_run:
            logger.info("Auto-start registered for first run")

        # Start system tray (in background thread)
        tray_thread = self.tray.run_threaded()

        # Show notification if first run
        if first_run:
            # Wait a moment for tray to be ready
            time.sleep(0.5)
            self.tray.show_notification(
                "FastFileOp",
                "FastFileOp has been set to start with Windows. You can change this in Settings."
            )

        # Start keyboard hook
        self.hook.start()

        # Start named pipe server
        self.pipe_server.start()

        # Run action processing loop
        self._process_actions()

        # Wait for tray thread
        tray_thread.join(timeout=5)

        logger.info("FastFileOp exited")


def main():
    """Main entry point"""
    args = parse_args()
    app = FastFileOpApp(silent=args.silent)
    app.run()


if __name__ == "__main__":
    main()
