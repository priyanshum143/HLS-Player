"""
This file will contain the code to setup logging
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


def setup_logger(name: str, log_file: str = None, level=logging.DEBUG):
    """
    Set up a logger with console and file handlers.

    :param name: Logger name (usually __name__ from calling module)
    :param log_file: Path to log file (optional, defaults to logs/search_engine.log)
    :param level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :return logging.Logger: Configured logger instance
    """

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Default log file with timestamp
    if log_file is None:
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d")
        log_file = log_dir / f"hls_player_{timestamp}.log"
    else:
        log_file = log_dir / log_file

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # Console handler (INFO and above, simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # File handler (DEBUG and above, detailed format)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str):
    """
    Get or create a logger for a module.

    :param name: Usually __name__ from the calling module
    :return logging.Logger: Logger instance
    """

    return setup_logger(name)
