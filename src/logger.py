"""
Centralized logging configuration for the YouTube Summarizer application.
Provides colored console output and timestamped log files.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style


class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output"""

    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"

        # Format the message
        return super().format(record)


def setup_logging(log_dir: Path = None) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        log_dir: Directory to save log files. If None, uses 'logs' in project root.

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        # Default to logs directory in project root
        from config import config
        log_dir = config.BASE_DIR / 'logs'

    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped log file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'ytb_summarizer_{timestamp}.log'

    # Create root logger
    logger = logging.getLogger('ytb_summarizer')
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler - detailed format without colors
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler - colored format
    console_formatter = ColoredConsoleFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Log the initialization
    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger


def get_logger(name: str = 'ytb_summarizer') -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (module name)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
