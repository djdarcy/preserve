"""
Dazzlelink integration for preserve.py.

This package provides integration with the dazzlelink library, allowing
preserve to work with dazzlelink files for alternative metadata storage.
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, Any

# Set up package-level logger
logger = logging.getLogger(__name__)

# Check if dazzlelink is available
HAVE_DAZZLELINK = False
try:
    import dazzlelink
    HAVE_DAZZLELINK = True
    logger.debug("Dazzlelink library found, integration enabled")
except ImportError:
    # Try with the bundled version
    try:
        import sys
        from pathlib import Path
        # Look for bundled dazzlelink in parent directory of preservelib
        bundled_path = Path(__file__).parent.parent.parent / 'dazzlelink'
        if bundled_path.exists() and str(bundled_path) not in sys.path:
            sys.path.insert(0, str(bundled_path))
        import dazzlelink
        HAVE_DAZZLELINK = True
        logger.debug("Bundled dazzlelink library found, integration enabled")
    except ImportError:
        logger.debug("Dazzlelink library not found, integration disabled")

def is_available() -> bool:
    """
    Check if dazzlelink integration is available.
    
    Returns:
        True if dazzlelink is available, False otherwise
    """
    return HAVE_DAZZLELINK

# Import functions from the main dazzlelink module if available
if HAVE_DAZZLELINK:
    try:
        from .core import (
            create_dazzlelink,
            find_dazzlelinks_in_dir,
            restore_from_dazzlelink,
            dazzlelink_to_manifest,
            manifest_to_dazzlelinks
        )
        
        # Export the functions
        __all__ = [
            'is_available',
            'create_dazzlelink',
            'find_dazzlelinks_in_dir',
            'restore_from_dazzlelink',
            'dazzlelink_to_manifest',
            'manifest_to_dazzlelinks'
        ]
    except ImportError as e:
        logger.warning(f"Error importing dazzlelink functionality: {e}")
        __all__ = ['is_available']
else:
    __all__ = ['is_available']
