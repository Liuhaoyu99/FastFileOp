"""FastFileOp - Configuration Management Module

Handles loading, saving, and managing application configuration.
Config file stored at %APPDATA%\FastFileOp\config.json
"""

import json
import os
import sys
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger(__name__)

# Paths
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FastFileOp")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")


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
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Update only known fields
                for key, value in data.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)

                logger.info(f"Configuration loaded from {CONFIG_FILE}")
            else:
                logger.info("Config file not found, using defaults")
                self.save()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")

        return self._config

    def save(self) -> None:
        """Save configuration to file"""
        try:
            os.makedirs(APP_DATA_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def update(self, **kwargs) -> None:
        """Update configuration fields and save"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save()

    def set_auto_start(self, enable: bool) -> None:
        """Set auto-start on boot

        Writes to HKCU\Software\Microsoft\Windows\CurrentVersion\Run
        """
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "FastFileOp"

        # Get current exe path with --silent flag for auto-start
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(sys.argv[0])

        # Add --silent flag for auto-start
        exe_path_with_args = f'"{exe_path}" --silent'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path_with_args)
                logger.info(f"Auto-start enabled: {exe_path_with_args}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("Auto-start disabled")
                except FileNotFoundError:
                    pass

            winreg.CloseKey(key)
            self._config.auto_start = enable
            self.save()

        except Exception as e:
            logger.error(f"Failed to set auto-start: {e}")

    def is_auto_start_registered(self) -> bool:
        """Check if auto-start is registered in Windows registry

        Returns:
            True if the registry key exists
        """
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "FastFileOp"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, WindowsError):
            return False
        except Exception as e:
            logger.error(f"Failed to check auto-start registry: {e}")
            return False

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
