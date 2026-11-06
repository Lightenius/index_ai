import os
import sys
import logging
from datetime import datetime

# Define a custom 'SYSTEM' log level (between INFO and WARNING)
SYSTEM_LEVEL = 25
logging.addLevelName(SYSTEM_LEVEL, "SYSTEM")


class AlignedFormatter(logging.Formatter):
    """Formats logs into <date-time> | <log-type> | <text> with column padding."""
    
    TYPE_COLUMN_WIDTH = 8

    def format(self, record):
        # 1. Format date and time
        dt_str = self.formatTime(record, self.datefmt)
        
        # 2. Normalize and pad the log type (levelname) for vertical alignment
        levelname = record.levelname
        padded_type = levelname.ljust(self.TYPE_COLUMN_WIDTH)
        
        # 3. Format message
        message = record.getMessage()
        
        # Assemble plain text format for file
        plain_formatted = f"{dt_str} | {padded_type} | {message}"
        
        # Apply ANSI coloring if enabled for console output
        if getattr(record, 'use_color', False):
            color = self.COLORS.get(levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            colored_type = f"{color}{padded_type}{reset}"
            return f"{dt_str} | {colored_type} | {message}"
            
        return plain_formatted

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'SYSTEM': '\033[35m',     # Magenta
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
        'RESET': '\033[0m'
    }


class Logger:
    """Static logger wrapper providing global access across the application."""
    
    _logger = None
    _log_file = None

    @classmethod
    def initialize(cls, log_dir="./logs/", name="AppLogger", level=logging.DEBUG):
        """Initializes the logger handlers. Safe to call multiple times."""
        if cls._logger is not None:
            return cls._logger

        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        cls._log_file = os.path.join(log_dir, f"app_{timestamp}.log")

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        if not logger.handlers:
            date_format = "%Y-%m-%d %H:%M:%S"

            # 1. Console Handler (With ANSI colors)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(AlignedFormatter(datefmt=date_format))

            # 2. File Handler (Plain text, no ANSI)
            file_handler = logging.FileHandler(cls._log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(AlignedFormatter(datefmt=date_format))

            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

        cls._logger = logger
        return cls._logger

    @classmethod
    def _get_logger(cls):
        if cls._logger is None:
            cls.initialize()
        return cls._logger

    @classmethod
    def debug(cls, message, *args, **kwargs):
        cls._get_logger().debug(message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def info(cls, message, *args, **kwargs):
        cls._get_logger().info(message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def system(cls, message, *args, **kwargs):
        """Custom log level for infrastructure/system events."""
        cls._get_logger().log(SYSTEM_LEVEL, message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def warning(cls, message, *args, **kwargs):
        cls._get_logger().warning(message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def error(cls, message, *args, **kwargs):
        cls._get_logger().error(message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def critical(cls, message, *args, **kwargs):
        cls._get_logger().critical(message, *args, **kwargs, extra={'use_color': True})

    @classmethod
    def get_log_file_path(cls):
        return cls._log_file