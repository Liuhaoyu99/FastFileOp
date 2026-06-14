"""FastFileOp - 日志模块

日志记录到 %APPDATA%\FastFileOp\logs\ 目录下。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# 日志目录
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FastFileOp")
LOG_DIR = os.path.join(APP_DATA_DIR, "logs")

# 模块级 logger 缓存
_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """获取模块 logger

    Args:
        name: logger 名称（通常为模块名）

    Returns:
        配置好的 Logger 实例
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
    if not logger.handlers:
        # 确保日志目录存在
        os.makedirs(LOG_DIR, exist_ok=True)

        # 文件 handler - 按大小轮转
        log_file = os.path.join(LOG_DIR, "fastfileop.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger
