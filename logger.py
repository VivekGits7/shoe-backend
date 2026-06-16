import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import settings

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logging(level: Optional[str] = None) -> None:
    if level is None:
        level = settings.LOG_LEVEL

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    app_handler = RotatingFileHandler(
        f"{LOGS_DIR}/app.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(app_handler)

    error_handler = RotatingFileHandler(
        f"{LOGS_DIR}/error.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)

    access_logger = logging.getLogger("uvicorn.access")
    access_handler = RotatingFileHandler(
        f"{LOGS_DIR}/access.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    access_handler.setFormatter(logging.Formatter(log_format))
    access_logger.addHandler(access_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
