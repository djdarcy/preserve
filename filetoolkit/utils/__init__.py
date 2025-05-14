"""
Initialization file for the filetoolkit.utils package.

This package provides utility functions for the filetoolkit library.
"""

import logging
from pathlib import Path

# Set up package-level logger
logger = logging.getLogger(__name__)

# Import module functions
from .compat import (
    is_windows, is_unix, is_admin, is_root,
    fix_path_separators, fix_path_case, get_system_encoding,
    get_system_temp_dir, get_home_dir, get_app_data_dir
)

from .validation import (
    is_valid_path, is_safe_path, validate_path_chars,
    is_absolute_path, is_relative_path, is_unc_path,
    is_hidden_path, is_symlink, is_junction
)

from .logger import (
    setup_logger, set_log_level, add_log_file,
    get_all_logger_names, ColoredFormatter
)

# Define exported functions
__all__ = [
    # Compatibility functions
    'is_windows', 'is_unix', 'is_admin', 'is_root',
    'fix_path_separators', 'fix_path_case', 'get_system_encoding',
    'get_system_temp_dir', 'get_home_dir', 'get_app_data_dir',
    
    # Validation functions
    'is_valid_path', 'is_safe_path', 'validate_path_chars',
    'is_absolute_path', 'is_relative_path', 'is_unc_path',
    'is_hidden_path', 'is_symlink', 'is_junction',
    
    # Logger functions
    'setup_logger', 'set_log_level', 'add_log_file',
    'get_all_logger_names', 'ColoredFormatter'
]
