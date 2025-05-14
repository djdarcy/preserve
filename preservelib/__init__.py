"""
preservelib - Library for file preservation with path normalization and verification.

This package provides tools for copying, moving, and restoring files with path preservation,
file verification, and detailed operation tracking through manifests.
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

__version__ = '0.1.0'

def configure_logging(level=logging.INFO, log_file=None):
    """
    Configure logging for preservelib.
    
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
