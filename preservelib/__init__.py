"""
preservelib - Library for file preservation with path normalization and verification.

This package provides tools for copying, moving, and restoring files with path preservation,
file verification, and detailed operation tracking through manifests.
"""

import os
import sys
import logging
from pathlib import Path

# Setup package-level logger (without handlers - will be configured by preserve.py)
# Note: This is only used when the package is imported directly, not through preserve.py
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# propagate=True by default, so we don't need to set it explicitly

# Import core functionality
from .manifest import (
    PreserveManifest,
    calculate_file_hash,
    verify_file_hash,
    create_manifest_for_path,
    read_manifest
)

from .operations import (
    copy_operation,
    move_operation,
    verify_operation,
    restore_operation
)

from .metadata import (
    collect_file_metadata,
    apply_file_metadata,
    compare_metadata
)

from .restore import (
    restore_file_to_original,
    restore_files_from_manifest,
    find_restoreable_files
)

# Import version from preserve package
try:
    from preserve.version import __version__
except ImportError:
    # Fallback if preserve package is not installed
    __version__ = '0.4.0'

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configure logging for preservelib.
    
    This is primarily for standalone usage of preservelib (when not imported by preserve.py).
    When used with preserve.py, logging will be configured there.
    
    Args:
        level: Logging level
        log_file: Optional path to log file
    """
    # Set up a standard format for all handlers
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Configure the root logger (to handle all propagated messages)
    root_logger = logging.getLogger()
    
    # Only configure if not already configured
    if not root_logger.handlers:
        root_logger.setLevel(level)
        
        # Add console handler to root logger
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        root_logger.addHandler(console_handler)
        
        # Add file handler to root logger if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
    
    # Set the level on the preservelib and submodule loggers
    for module_name in [__name__, 'preservelib.operations', 'preservelib.dazzlelink']:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(level)
        # Keep propagate=True to avoid duplicate logging
    
    logger.debug(f"Logging configured for preservelib with level {level}")

def enable_verbose_logging():
    """Enable verbose (debug) logging."""
    configure_logging(logging.DEBUG)

# __all__ defines the public API
__all__ = [
    # Version
    '__version__',
    
    # Logging functions
    'configure_logging',
    'enable_verbose_logging',
    
    # Manifest functions
    'PreserveManifest',
    'calculate_file_hash',
    'verify_file_hash',
    'create_manifest_for_path',
    'read_manifest',
    
    # Operation functions
    'copy_operation',
    'move_operation',
    'verify_operation',
    'restore_operation',
    
    # Metadata functions
    'collect_file_metadata',
    'apply_file_metadata',
    'compare_metadata',
    
    # Restore functions
    'restore_file_to_original',
    'restore_files_from_manifest',
    'find_restoreable_files'
]
