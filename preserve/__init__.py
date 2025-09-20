"""
preserve - A cross-platform file preservation tool with path normalization and verification.

This package provides the preserve command-line tool for copying, moving, and restoring files
with path preservation, file verification, and detailed operation tracking.
"""

import logging

# Version information
__version__ = "0.4.0"

# Set up package-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Don't add handlers here - they will be configured by preserve.py's setup_logging
# We'll let the root logger handle output to avoid duplication

# Import core functionality
from .preserve import main

__all__ = ['main']
