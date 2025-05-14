"""
Path validation utilities for filetoolkit.

This module provides functions for validating path strings and objects,
ensuring they meet the requirements for various file operations.
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import Union, List, Set, Optional

# Set up module-level logger
logger = logging.getLogger(__name__)

# Platform detection
IS_WINDOWS = sys.platform == 'win32'

# Invalid characters for various platforms
WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')
UNIX_INVALID_CHARS = set('')  # Unix allows almost any character

# Invalid names on Windows (case-insensitive)
WINDOWS_INVALID_NAMES = {
    'con', 'prn', 'aux', 'nul',
    'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

def is_valid_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is valid on the current platform.
    
    Args:
        path: Path to validate
        
    Returns:
        True if path is valid, False otherwise
    """
    path_str = str(path)
    
    # Check for empty path
    if not path_str:
        return False
    
    # Platform-specific checks
    if IS_WINDOWS:
        return _is_valid_windows_path(path_str)
    else:
        return _is_valid_unix_path(path_str)

def _is_valid_windows_path(path: str) -> bool:
    """
    Check if a path is valid on Windows.
    
    Args:
        path: Path string to validate
        
    Returns:
        True if path is valid, False otherwise
    """
    # Check for total path length limit (260 characters)
    if len(path) > 260:
        # Check if path is in long path format (\\?\)
        if not path.startswith('\\\\?\\'):
            logger.debug(f"Path exceeds Windows 260 character limit: {path}")
            return False
    
    # Check for invalid characters in path
    for part in path.split('\\'):
        # Skip drive letter (e.g., "C:")
        if len(part) == 2 and part[1] == ':':
            continue
            
        # Check for invalid characters
        if any(c in WINDOWS_INVALID_CHARS for c in part):
            logger.debug(f"Path contains invalid characters: {path}")
            return False
        
        # Check for reserved names
        name = part.split('.')[0].lower()
        if name in WINDOWS_INVALID_NAMES:
            logger.debug(f"Path contains reserved name: {path}")
            return False
        
        # Check for leading/trailing spaces or periods
        if part.strip() != part or part.rstrip('.') != part:
            logger.debug(f"Path contains invalid leading/trailing spaces or periods: {path}")
            return False
    
    return True

def _is_valid_unix_path(path: str) -> bool:
    """
    Check if a path is valid on Unix-like systems.
    
    Args:
        path: Path string to validate
        
    Returns:
        True if path is valid, False otherwise
    """
    # Unix allows almost any character in paths
    # Just ensure it's not empty and doesn't have NULL characters
    return bool(path) and '\0' not in path

def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """
    Check if a path is safe (doesn't escape outside its base directory).
    
    Args:
        path: Path to validate
        base_dir: Base directory that the path should be under
        
    Returns:
        True if path is safe, False otherwise
    """
    # Resolve both paths
    try:
        path_obj = Path(path).resolve()
        base_dir_obj = Path(base_dir).resolve()
        
        # Check if the path is a descendant of the base directory
        return str(path_obj).startswith(str(base_dir_obj))
    except Exception as e:
        logger.debug(f"Error checking safe path: {e}")
        return False

def validate_path_chars(path: Union[str, Path]) -> List[str]:
    """
    Validate characters in a path and return any errors.
    
    Args:
        path: Path to validate
        
    Returns:
        List of error messages (empty if path is valid)
    """
    path_str = str(path)
    errors = []
    
    # Check for empty path
    if not path_str:
        errors.append("Path is empty")
        return errors
    
    # Platform-specific checks
    if IS_WINDOWS:
        # Check for invalid characters
        for char in WINDOWS_INVALID_CHARS:
            if char in path_str:
                errors.append(f"Invalid character '{char}' in path")
        
        # Check path length
        if len(path_str) > 260 and not path_str.startswith('\\\\?\\'):
            errors.append("Path exceeds 260 character limit")
        
        # Check for reserved names
        for part in path_str.split('\\'):
            # Skip drive letter (e.g., "C:")
            if len(part) == 2 and part[1] == ':':
                continue
                
            # Check for reserved names
            name = part.split('.')[0].lower()
            if name in WINDOWS_INVALID_NAMES:
                errors.append(f"Reserved name '{part}' in path")
            
            # Check for trailing spaces or periods
            if part.strip() != part:
                errors.append(f"Path component '{part}' has leading or trailing spaces")
            
            if part.rstrip('.') != part:
                errors.append(f"Path component '{part}' has trailing periods")
    else:
        # Unix-like systems
        if '\0' in path_str:
            errors.append("Path contains NULL character")
    
    return errors

def is_absolute_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is absolute.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is absolute, False otherwise
    """
    return Path(path).is_absolute()

def is_relative_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is relative.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is relative, False otherwise
    """
    return not Path(path).is_absolute()

def is_unc_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is a UNC (Universal Naming Convention) path.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a UNC path, False otherwise
    """
    path_str = str(path)
    
    # UNC paths start with \\ on Windows or // on other platforms
    if IS_WINDOWS:
        return path_str.startswith('\\\\')
    else:
        return path_str.startswith('//')

def is_hidden_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is hidden.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is hidden, False otherwise
    """
    path_obj = Path(path)
    
    # Check if the path exists
    if not path_obj.exists():
        return False
    
    if IS_WINDOWS:
        try:
            import win32api
            import win32con
            attributes = win32api.GetFileAttributes(str(path_obj))
            return (attributes & win32con.FILE_ATTRIBUTE_HIDDEN) != 0
        except:
            # Fall back to checking filename
            name = path_obj.name
            return name.startswith('.') or name.endswith('.')
    else:
        # On Unix, files starting with a period are hidden
        return path_obj.name.startswith('.')

def is_symlink(path: Union[str, Path]) -> bool:
    """
    Check if a path is a symbolic link.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a symbolic link, False otherwise
    """
    return Path(path).is_symlink()

def is_junction(path: Union[str, Path]) -> bool:
    """
    Check if a path is a Windows junction point.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a junction, False otherwise
    """
    if not IS_WINDOWS:
        return False
    
    path_obj = Path(path)
    
    # Check if the path exists and is a directory
    if not path_obj.exists() or not path_obj.is_dir():
        return False
    
    try:
        import win32file
        attributes = win32file.GetFileAttributes(str(path_obj))
        return (attributes & win32file.FILE_ATTRIBUTE_REPARSE_POINT) != 0
    except:
        logger.debug("Cannot check for junction point - win32file module not available")
        return False
