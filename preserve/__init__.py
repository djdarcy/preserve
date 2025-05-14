"""
preserve - A cross-platform file preservation tool with path normalization and verification.

This package provides the preserve command-line tool for copying, moving, and restoring files
with path preservation, file verification, and detailed operation tracking.
"""

import logging

# Version information
__version__ = "0.1.0"

# Set up package-level logger
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
from .preserve import main

__all__ = ['main']
