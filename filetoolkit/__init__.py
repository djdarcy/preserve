"""
filetoolkit - A general-purpose file manipulation library.

This package provides utilities for file operations, path handling, and verification
across different platforms, with a focus on preserving file metadata.
"""

import os
import sys
import logging
from pathlib import Path

# Setup package-level logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)

# Import core functionality
from .paths import (
    normalize_path,
    is_same_file,
    split_drive_letter,
    is_unc_path,
    get_relative_path,
    create_dest_path,
    find_files,
    find_regex_files,
    collect_files_from_include_file,
    create_parent_dirs,
    ensure_unique_path,
    get_path_type
)

from .operations import (
    copy_file,
    move_file,
    collect_file_metadata,
    apply_file_metadata,
    copy_files_with_path,
    move_files_with_path,
    create_directory_structure,
    remove_file,
    remove_directory
)

from .verification import (
    calculate_file_hash,
    verify_file_hash,
    verify_files_with_manifest,
    calculate_directory_hashes,
    save_hashes_to_file,
    load_hashes_from_file,
    compare_directories,
    verify_copied_files
)

__version__ = '0.1.0'

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configure logging for filetoolkit.
    
    Args:
        level: Logging level
        log_file: Optional path to log file
    """
    logger.setLevel(level)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
        
    logger.debug(f"Logging configured with level {level}")

def enable_verbose_logging():
    """Enable verbose (debug) logging."""
    configure_logging(logging.DEBUG)

# Platform-specific functions can be imported conditionally
if sys.platform == 'win32':
    pass
    # Windows-specific functions
    # try:
        # from .platform.windows import (
        #     Import Windows-specific functions when implemented
        # )
    # except ImportError:
    #     logger.debug("Windows-specific functions not available")
else:
    pass
    # Unix-specific functions
    # try:
        # from .platform.unix import (
        #     Import Unix-specific functions when implemented
        # )
    # except ImportError:
    #     logger.debug("Unix-specific functions not available")

# __all__ defines the public API
__all__ = [
    # Version
    '__version__',
    
    # Logging functions
    'configure_logging',
    'enable_verbose_logging',
    
    # Path functions
    'normalize_path',
    'is_same_file',
    'split_drive_letter',
    'is_unc_path',
    'get_relative_path',
    'create_dest_path',
    'find_files',
    'find_regex_files',
    'collect_files_from_include_file',
    'create_parent_dirs',
    'ensure_unique_path',
    'get_path_type',
    
    # Operation functions
    'copy_file',
    'move_file',
    'collect_file_metadata',
    'apply_file_metadata',
    'copy_files_with_path',
    'move_files_with_path',
    'create_directory_structure',
    'remove_file',
    'remove_directory',
    
    # Verification functions
    'calculate_file_hash',
    'verify_file_hash',
    'verify_files_with_manifest',
    'calculate_directory_hashes',
    'save_hashes_to_file',
    'load_hashes_from_file',
    'compare_directories',
    'verify_copied_files'
]