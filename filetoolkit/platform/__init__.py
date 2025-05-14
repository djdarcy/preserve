"""
Platform-specific implementations for filetoolkit.

This module provides platform-specific implementations of file operations
that vary between different operating systems.
"""

import os
import sys
import logging
import platform

# Set up module-level logger
logger = logging.getLogger(__name__)

# Determine platform
PLATFORM = platform.system().lower()

# Import platform-specific functions
if PLATFORM == 'windows':
    try:
        from .windows import is_admin
        # Import other Windows-specific functions as they're implemented
        HAS_WINDOWS_SUPPORT = True
    except ImportError as e:
        logger.debug(f"Windows support not fully available: {e}")
        HAS_WINDOWS_SUPPORT = False
elif PLATFORM in ('linux', 'darwin', 'freebsd', 'openbsd', 'netbsd'):
    try:
        from .unix import is_root
        # Import other Unix-specific functions as they're implemented
        HAS_UNIX_SUPPORT = True
    except ImportError as e:
        logger.debug(f"Unix support not fully available: {e}")
        HAS_UNIX_SUPPORT = False
else:
    logger.warning(f"Unsupported platform: {PLATFORM}")
    HAS_WINDOWS_SUPPORT = False
    HAS_UNIX_SUPPORT = False

def has_admin_rights() -> bool:
    """
    Check if the current process has administrative privileges.
    
    Returns:
        bool: True if the process has admin rights, False otherwise
    """
    if PLATFORM == 'windows' and HAS_WINDOWS_SUPPORT:
        return is_admin()
    elif PLATFORM in ('linux', 'darwin', 'freebsd', 'openbsd', 'netbsd') and HAS_UNIX_SUPPORT:
        return is_root()
    else:
        logger.debug(f"Cannot check admin rights on platform: {PLATFORM}")
        return False

def get_platform_name() -> str:
    """
    Get the name of the current platform.
    
    Returns:
        str: The platform name ('windows', 'linux', 'darwin', etc.)
    """
    return PLATFORM

def is_windows() -> bool:
    """
    Check if the current platform is Windows.
    
    Returns:
        bool: True if Windows, False otherwise
    """
    return PLATFORM == 'windows'

def is_unix() -> bool:
    """
    Check if the current platform is a Unix-like system.
    
    Returns:
        bool: True if Unix-like, False otherwise
    """
    return PLATFORM in ('linux', 'darwin', 'freebsd', 'openbsd', 'netbsd')

def is_macos() -> bool:
    """
    Check if the current platform is macOS.
    
    Returns:
        bool: True if macOS, False otherwise
    """
    return PLATFORM == 'darwin'

def is_linux() -> bool:
    """
    Check if the current platform is Linux.
    
    Returns:
        bool: True if Linux, False otherwise
    """
    return PLATFORM == 'linux'
