"""FastFileOp - Logging Module

Configures logging with daily rotation, keeping last 7 days.
Log files stored at %APPDATA%/FastFileOp/logs/
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

# Paths (computed at runtime)
def _get_log_dir() -> str:
    app_data = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FastFileOp")
    return os.path.join(app_data, "logs")

# Module-level logger cache
_loggers: dict = {}

# Root logger configured flag
_root_configured = False


def configure_root_logger(debug: bool = False) -> None:
    """Configure the root logger

    Args:
        debug: If True, set log level to DEBUG
    """
    global _root_configured

    if _root_configured:
        return

    _root_configured = True

    # Ensure log directory exists
    log_dir = _get_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers
    root_logger.handlers.clear()

    # File handler - daily rotation, keep 7 days
    log_file = os.path.join(log_dir, "fastfileop.log")
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.suffix = "%Y-%m-%d"
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured Logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


def set_debug_mode(debug: bool) -> None:
    """Set debug mode

    Args:
        debug: If True, set log level to DEBUG
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Also update console handler
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, TimedRotatingFileHandler):
            handler.setLevel(logging.DEBUG if debug else logging.INFO)
