"""
Logging utilities for filetoolkit.

This module provides a standardized logging setup for filetoolkit
and related applications, with support for console and file logging.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Union, Dict, List

# Default log format
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Default log level
DEFAULT_LOG_LEVEL = logging.INFO

class ColoredFormatter(logging.Formatter):
    """
    A formatter that adds colors to log messages based on their level.
    """
    
    # ANSI color codes
    COLORS = {
        logging.DEBUG: '\033[36m',      # Cyan
        logging.INFO: '\033[32m',       # Green
        logging.WARNING: '\033[33m',    # Yellow
        logging.ERROR: '\033[31m',      # Red
        logging.CRITICAL: '\033[35m',   # Magenta
    }
    
    # Reset code
    RESET = '\033[0m'
    
    def __init__(self, fmt: str = None, datefmt: str = None, style: str = '%', use_colors: bool = True):
        """
        Initialize the formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            style: Format style
            use_colors: Whether to use colors
        """
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors
    
    def format(self, record):
        """
        Format a log record with colors.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message with colors
        """
        # Get the original formatted message
        message = super().format(record)
        
        # Add colors if enabled
        if self.use_colors and record.levelno in self.COLORS:
            message = f"{self.COLORS[record.levelno]}{message}{self.RESET}"
        
        return message

def setup_logger(
    name: str = 'filetoolkit',
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[Union[str, Path]] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up a logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file (optional)
        log_format: Log format string
        use_colors: Whether to use colors in console output
        
    Returns:
        Configured logger
    """
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Add colored formatter to console handler if supported
    if use_colors and sys.stdout.isatty() and sys.platform != 'win32':
        console_formatter = ColoredFormatter(log_format, use_colors=True)
    else:
        console_formatter = logging.Formatter(log_format)
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        file_path = Path(log_file)
        
        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(level)
        
        # Add formatter to file handler
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
    
    return logger

def set_log_level(
    logger: Union[logging.Logger, str],
    level: Union[int, str]
) -> None:
    """
    Set the log level for a logger.
    
    Args:
        logger: Logger or logger name
        level: Log level (can be int or string like 'DEBUG', 'INFO', etc.)
    """
    # Get logger if name is provided
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Set logger level
    logger.setLevel(level)
    
    # Set handler levels
    for handler in logger.handlers:
        handler.setLevel(level)

def add_log_file(
    logger: Union[logging.Logger, str],
    log_file: Union[str, Path],
    level: Optional[int] = None,
    log_format: str = DEFAULT_LOG_FORMAT
) -> None:
    """
    Add a file handler to a logger.
    
    Args:
        logger: Logger or logger name
        log_file: Path to log file
        level: Logging level (defaults to logger's level)
        log_format: Log format string
    """
    # Get logger if name is provided
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    
    # Use logger's level if not specified
    if level is None:
        level = logger.level
    
    # Create parent directory if it doesn't exist
    file_path = Path(log_file)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create file handler
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(level)
    
    # Add formatter to file handler
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(file_handler)

def get_all_logger_names() -> List[str]:
    """
    Get the names of all loggers.
    
    Returns:
        List of logger names
    """
    return list(logging.Logger.manager.loggerDict.keys())
