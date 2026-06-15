"""FastFileOp - System Tray Module

Creates system tray icon with right-click menu using pystray.
Icon is generated programmatically to avoid external file dependency.
Supports instability status and manual resume.
"""

import logging
import threading
import ctypes
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _create_icon_image(size: int = 64, color: tuple = (41, 128, 185)) -> Image.Image:
    """Create tray icon image programmatically

    Creates a rounded square with "F" letter.
    """
    # Create RGBA image with transparency
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    margin = 4
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=12,
        fill=color + (255,),  # Add alpha channel
    )

    # Draw "F" letter
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    # Center the text
    text = "F"
    if font:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = size // 3
        text_height = size // 2

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 2
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


def _create_paused_image(size: int = 64) -> Image.Image:
    """Create paused state icon (gray)"""
    return _create_icon_image(size, color=(128, 128, 128))


def _create_warning_image(size: int = 64) -> Image.Image:
    """Create warning/unstable state icon (orange)"""
    return _create_icon_image(size, color=(230, 126, 34))


class TrayIcon:
    """System tray icon

    Provides:
    - Status indicator (active/paused/unstable)
    - Pause/Resume menu
    - Resume from instability menu
    - Settings menu
    - Exit menu
    """

    def __init__(
        self,
        config_manager,
        on_settings: Callable,
        on_exit: Callable,
        on_toggle_pause: Optional[Callable] = None,
        on_resume_interception: Optional[Callable] = None,
        on_open_main: Optional[Callable] = None,
        on_view_log: Optional[Callable] = None,
    ):
        """
        Args:
            config_manager: Configuration manager instance
            on_settings: Callback to open settings window
            on_exit: Callback to exit application
            on_toggle_pause: Optional callback when pause state changes
            on_resume_interception: Callback to resume from instability
            on_open_main: Callback to open the main operation window
            on_view_log: Callback to open the operation log viewer
        """
        self.config_manager = config_manager
        self.on_settings = on_settings
        self.on_exit = on_exit
        self.on_toggle_pause = on_toggle_pause
        self.on_resume_interception = on_resume_interception
        self.on_open_main = on_open_main
        self.on_view_log = on_view_log

        self._icon: Optional[pystray.Icon] = None
        self._paused = config_manager.config.paused
        self._instability = False
        self._dll_registered = True  # Assume registered initially

    def set_dll_status(self, registered: bool):
        """Set DLL registration status for menu display"""
        self._dll_registered = registered
        self._refresh_icon()

    def _get_menu(self) -> pystray.Menu:
        """Create right-click menu"""
        if self._instability:
            # Instability menu
            return pystray.Menu(
                pystray.MenuItem(
                    "Status: UNSTABLE",
                    None,
                    enabled=False,
                ),
                pystray.MenuItem(
                    "Interception paused due to errors",
                    None,
                    enabled=False,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Resume Interception",
                    self._resume_interception,
                ),
                pystray.MenuItem(
                    "Open FastFileOp...",
                    self._open_main,
                ),
                pystray.MenuItem(
                    "View Log",
                    self._view_log,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Settings...",
                    self._open_settings,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit",
                    self._quit,
                ),
            )

        # Normal menu
        status_text = "Paused" if self._paused else "Active"
        pause_label = "Resume" if self._paused else "Pause"

        # DLL status item
        if self._dll_registered:
            dll_item = pystray.MenuItem(
                "DLL: Registered",
                None,
                enabled=False,
            )
        else:
            dll_item = pystray.MenuItem(
                "Register Shell Extension...",
                self._register_dll,
            )

        return pystray.Menu(
            pystray.MenuItem(
                f"Status: {status_text}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Open FastFileOp...",
                self._open_main,
            ),
            pystray.MenuItem(
                "View Log",
                self._view_log,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                pause_label,
                self._toggle_pause,
            ),
            pystray.MenuItem(
                "Settings...",
                self._open_settings,
            ),
            pystray.Menu.SEPARATOR,
            dll_item,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Exit",
                self._quit,
            ),
        )

    def _toggle_pause(self, icon, item):
        """Toggle pause state"""
        self._paused = not self._paused
        self.config_manager.update(paused=self._paused)
        self._refresh_icon()

        if self.on_toggle_pause:
            self.on_toggle_pause(self._paused)

        logger.info(f"Interception {'paused' if self._paused else 'resumed'}")

    def _resume_interception(self, icon, item):
        """Resume from instability"""
        logger.info("User requested resume from instability")

        if self.on_resume_interception:
            self.on_resume_interception()

    def _open_main(self, icon, item):
        """Open main operation window"""
        try:
            if self.on_open_main:
                self.on_open_main()
        except Exception as e:
            logger.error(f"Failed to open main window: {e}")

    def _view_log(self, icon, item):
        """Open operation log viewer"""
        try:
            if self.on_view_log:
                self.on_view_log()
        except Exception as e:
            logger.error(f"Failed to open log viewer: {e}")

    def _open_settings(self, icon, item):
        """Open settings window"""
        try:
            self.on_settings()
        except Exception as e:
            logger.error(f"Failed to open settings: {e}")

    def _register_dll(self, icon, item):
        """Register shell extension DLL"""
        logger.info("User requested DLL registration from tray menu")

        # Use tkinter for the dialog (works better in callback threads)
        import tkinter as tk
        from tkinter import messagebox

        def show_dialog():
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.attributes('-topmost', True)  # Bring to front

            result = messagebox.askokcancel(
                "FastFileOp - Register Shell Extension",
                "To register the shell extension, FastFileOp needs to run with administrator privileges.\n\n"
                "Click OK to restart as administrator and register the DLL."
            )

            root.destroy()

            if result:
                # Import here to avoid circular import
                from .register import run_as_admin
                if run_as_admin(["--register-dll"]):
                    logger.info("Admin elevation requested for DLL registration")
                    # Show notification
                    self.show_notification(
                        "FastFileOp",
                        "Restarting with administrator privileges to register DLL..."
                    )
                    # Schedule a follow-up to check install log for registration result
                    def _check_install_log():
                        import time
                        time.sleep(4)
                        try:
                            import os
                            log_path = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', r'C:\Windows\Temp')), 'fastfileop_install.log')
                            if os.path.exists(log_path):
                                # Read last 30 lines
                                with open(log_path, 'rb') as f:
                                    f.seek(0, 2)
                                    size = f.tell()
                                    f.seek(max(0, size - 16 * 1024))
                                    tail = f.read().decode('utf-8', errors='replace')
                                # Show a brief notification if errors present
                                if 'failed' in tail.lower() or 'error' in tail.lower():
                                    self.show_notification('FastFileOp - Registration', 'DLL registration appears to have failed. Check install log for details.')
                        except Exception:
                            pass

                    import threading
                    threading.Thread(target=_check_install_log, daemon=True).start()
                else:
                    logger.error("Failed to request admin elevation")
                    self.show_notification(
                        "FastFileOp - Error",
                        "Failed to request administrator privileges."
                    )

        # Run dialog in a separate thread to avoid blocking
        import threading
        thread = threading.Thread(target=show_dialog, daemon=True)
        thread.start()

    def _quit(self, icon, item):
        """Quit application"""
        logger.info("=== EXIT: User clicked Exit in tray menu ===")

        # Schedule cleanup in a separate thread to avoid blocking
        def do_exit():
            logger.info("=== EXIT: Starting exit sequence ===")
            import time
            time.sleep(0.1)  # Small delay to let menu close

            if self.on_exit:
                logger.info("=== EXIT: Calling on_exit callback ===")
                self.on_exit()

            # Stop the tray icon - this will cause icon.run() to return
            if self._icon:
                logger.info("=== EXIT: Stopping tray icon ===")
                self._icon.stop()

            logger.info("=== EXIT: Exit sequence complete ===")

        import threading
        exit_thread = threading.Thread(target=do_exit, daemon=True)
        exit_thread.start()
        logger.info("=== EXIT: Exit thread started ===")

    def _refresh_icon(self):
        """Refresh tray icon"""
        if self._icon:
            if self._instability:
                self._icon.icon = _create_warning_image()
            elif self._paused:
                self._icon.icon = _create_paused_image()
            else:
                self._icon.icon = _create_icon_image()
            self._icon.menu = self._get_menu()

    def run(self):
        """Run tray icon (blocking)"""
        try:
            if self._instability:
                image = _create_warning_image()
            elif self._paused:
                image = _create_paused_image()
            else:
                image = _create_icon_image()

            logger.debug(f"Creating tray icon with image size: {image.size}")

            def setup(icon):
                """Setup callback - make icon visible"""
                icon.visible = True
                logger.info("Tray icon made visible")

            self._icon = pystray.Icon(
                name="FastFileOp",
                icon=image,
                title="FastFileOp - High-Speed File Operations",
                menu=self._get_menu(),
            )

            logger.info("System tray icon created successfully, starting run loop")

            # Run the icon with setup callback - this blocks until icon.stop() is called
            self._icon.run(setup=setup)

        except Exception as e:
            logger.error(f"Failed to create/run tray icon: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def run_threaded(self) -> threading.Thread:
        """Run tray icon in background thread"""
        thread = threading.Thread(target=self._run_safe, daemon=False)  # Not daemon to keep alive
        thread.start()
        return thread

    def _run_safe(self):
        """Safe wrapper for tray run with error handling"""
        try:
            self.run()
        except Exception as e:
            logger.error(f"Tray thread error: {e}")
            # Try to restart tray after a delay
            import time
            time.sleep(2)
            try:
                self.run()
            except Exception as e2:
                logger.error(f"Tray restart failed: {e2}")

    def stop(self):
        """Stop tray icon"""
        if self._icon:
            self._icon.stop()

    def update_status(self, paused: bool):
        """Update status from external source"""
        if self._paused != paused:
            self._paused = paused
            self._refresh_icon()

    def update_instability_status(self, instability: bool):
        """Update instability status

        Args:
            instability: True if system is unstable
        """
        if self._instability != instability:
            self._instability = instability
            self._paused = instability  # Instability implies paused
            self._refresh_icon()

            if instability:
                logger.warning("Tray icon updated: instability mode")
            else:
                logger.info("Tray icon updated: normal mode")

    def show_notification(self, title: str, message: str):
        """Show a balloon notification from the tray icon"""
        if self._icon:
            try:
                self._icon.notify(message, title)
                logger.debug(f"Notification shown: {title} - {message}")
            except Exception as e:
                logger.error(f"Failed to show notification: {e}")
