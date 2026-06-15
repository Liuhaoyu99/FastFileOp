"""FastFileOp - Configuration Management Module

Handles loading, saving, and managing application configuration.
Config file stored at %APPDATA%/FastFileOp/config.json
"""

import json
import os
import sys
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger(__name__)

# Paths (computed at runtime, not import time, to respect APPDATA changes in tests)
def _get_app_data_dir() -> str:
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FastFileOp")

def _get_config_file() -> str:
    return os.path.join(_get_app_data_dir(), "config.json")


@dataclass
class AppConfig:
    """Application configuration"""
    # Buffer size in MB (32-512)
    buffer_size_mb: int = 64

    # Number of worker threads (1-8)
    worker_threads: int = 4

    # Hook switches
    hook_copy: bool = True      # Intercept copy/move operations
    hook_delete: bool = True    # Intercept delete operations
    hook_drag: bool = True      # Intercept drag operations (requires DLL)

    # Auto-start on boot
    auto_start: bool = False

    # Debug mode
    debug_mode: bool = False

    # Paused state
    paused: bool = False

    # Language ("en" or "zh")
    language: str = "en"

    @property
    def buffer_size(self) -> int:
        """Buffer size in bytes"""
        return self.buffer_size_mb * 1024 * 1024


class ConfigManager:
    """Configuration manager

    Handles loading, saving, and providing access to application configuration.
    """

    def __init__(self):
        self._config = AppConfig()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        """Load configuration from file"""
        try:
            config_file = _get_config_file()
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Update only known fields
                for key, value in data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)

                logger.info(f"Configuration loaded from {config_file}")
            else:
                logger.info("Config file not found, using defaults")
                self.save()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")

        return self._config

    def save(self) -> None:
        """Save configuration to file"""
        try:
            config_file = _get_config_file()
            os.makedirs(_get_app_data_dir(), exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update(self, **kwargs) -> None:
        """Update configuration fields and save"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save()

    def _get_startup_folder_path(self) -> str:
        """Get Windows startup folder path"""
        return os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )

    def _get_shortcut_path(self) -> str:
        """Get path to the startup shortcut"""
        startup_dir = self._get_startup_folder_path()
        return os.path.join(startup_dir, "FastFileOp.lnk")

    def set_auto_start(self, enable: bool) -> None:
        """Set auto-start on boot using Windows Startup folder

        Creates/deletes a .lnk shortcut in the user's Startup folder.
        More reliable than registry and easier for users to manage.
        """
        from win32com.client import Dispatch

        shortcut_path = self._get_shortcut_path()

        # Get current exe path with --silent flag for auto-start
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
            target = exe_path
            arguments = "--silent"
        else:
            # Running as script - use the script path
            script_path = os.path.join(os.path.dirname(__file__), "__main__.py")
            exe_path = sys.executable
            # For scripts, we need to use python.exe with the script as argument
            target = exe_path
            arguments = f'"{script_path}" --silent'

        try:
            if enable:
                # Ensure startup folder exists
                startup_dir = self._get_startup_folder_path()
                os.makedirs(startup_dir, exist_ok=True)

                # Create shortcut using Windows Script Host
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = target
                shortcut.Arguments = arguments
                shortcut.WorkingDirectory = os.path.dirname(target)
                shortcut.Description = "FastFileOp - High-Speed File Operations"
                # Try to set icon to the exe itself
                shortcut.IconLocation = f"{target},0"
                shortcut.save()

                logger.info(f"Auto-start enabled: {shortcut_path}")
            else:
                # Remove shortcut if exists
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    logger.info("Auto-start disabled")

            self._config.auto_start = enable
            self.save()

        except Exception as e:
            logger.error(f"Failed to set auto-start: {e}")

    def is_auto_start_registered(self) -> bool:
        """Check if auto-start shortcut exists in Startup folder

        Returns:
            True if the shortcut exists
        """
        return os.path.exists(self._get_shortcut_path())

    def ensure_auto_start_registered(self) -> bool:
        """Ensure auto-start is registered (for first-run)

        Returns:
            True if this was the first time (newly registered)
        """
        if self.is_auto_start_registered():
            # Already registered, sync config
            if not self._config.auto_start:
                self._config.auto_start = True
                self.save()
            return False

        # Not registered, auto-register
        self.set_auto_start(True)
        return True

    def is_hooking_enabled(self) -> bool:
        """Check if any hooking is enabled and not paused"""
        if self._config.paused:
            return False
        return self._config.hook_copy or self._config.hook_delete or self._config.hook_drag
