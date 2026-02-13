"""
Logging configuration for the Cost Tracker application.
Provides both file and console logging with rotation.
"""

import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logger(name, log_file, level=logging.INFO):
    """
    Configure application logger with file and console output.

    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    # Create logs directory if not exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation (10MB max, 5 backup files)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Configure root logger so all modules' logs are captured
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Return a named logger (inherits root handlers, no duplicates)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return logger
