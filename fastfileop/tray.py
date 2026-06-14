"""FastFileOp - System Tray Module

Creates system tray icon with right-click menu using pystray.
Icon is embedded as base64 to avoid external file dependency.
Supports instability status and manual resume.
"""

import base64
import io
import logging
import threading
from typing import Callable, Optional

import pystray
from PIL import Image

logger = logging.getLogger(__name__)

# Embedded icon (64x64 PNG, blue background with white "F")
ICON_DATA = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAB"
    "hklEQVR4nO2YsU7DMBCGP0QHqKVD6CB1kjqIDlKHqSNUo6qigqKKKgo2qGjRpeYA8Cf2JXuYxJfU"
    "NE0yxN/8fz8+M5KZkRCi/4gBkAAWwDpgB+wBu4AcsAtoAQeAN+AXsA9YASeAAXAOuAN2gCVwDLgD"
    "doEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2"
    "gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aB"
    "HXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEd"
    "cAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1w"
    "DLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAM"
    "uAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4"
    "A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD"
    "9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2"
    "gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aB"
    "HXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEd"
    "cAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1w"
    "DLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAM"
    "uAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4"
    "A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD9oEdcAy4A/aBHXAMuAP2gR1wDLgD"
    "9oEdcAy4A/aBHXAM+BeGBQ4wEj3R2QAAAABJRU5ErkJggg=="
)


def _create_icon_image(size: int = 64, color: tuple = (41, 128, 185)) -> Image.Image:
    """Create tray icon image"""
    try:
        img = Image.open(io.BytesIO(ICON_DATA))
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
    except Exception:
        pass

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.rounded_rectangle(
        [(margin, margin), (size - margin, size - margin)],
        radius=12,
        fill=color,
    )
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    draw.text((size // 3, size // 6), "F", fill=(255, 255, 255), font=font)
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
    ):
        """
        Args:
            config_manager: Configuration manager instance
            on_settings: Callback to open settings window
            on_exit: Callback to exit application
            on_toggle_pause: Optional callback when pause state changes
            on_resume_interception: Callback to resume from instability
        """
        self.config_manager = config_manager
        self.on_settings = on_settings
        self.on_exit = on_exit
        self.on_toggle_pause = on_toggle_pause
        self.on_resume_interception = on_resume_interception

        self._icon: Optional[pystray.Icon] = None
        self._paused = config_manager.config.paused
        self._instability = False

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

        return pystray.Menu(
            pystray.MenuItem(
                f"Status: {status_text}",
                None,
                enabled=False,
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

    def _open_settings(self, icon, item):
        """Open settings window"""
        try:
            self.on_settings()
        except Exception as e:
            logger.error(f"Failed to open settings: {e}")

    def _quit(self, icon, item):
        """Quit application"""
        logger.info("User requested exit")
        icon.stop()
        self.on_exit()

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
        if self._instability:
            image = _create_warning_image()
        elif self._paused:
            image = _create_paused_image()
        else:
            image = _create_icon_image()

        self._icon = pystray.Icon(
            name="FastFileOp",
            icon=image,
            title="FastFileOp - High-Speed File Operations",
            menu=self._get_menu(),
        )

        logger.info("System tray icon created")
        self._icon.run()

    def run_threaded(self) -> threading.Thread:
        """Run tray icon in background thread"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

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
