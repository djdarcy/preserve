"""
Metadata management for preserve.py.

This module provides functionality for collecting, storing, and applying
file metadata to preserve file attributes during copy and restore operations.
"""

import os
import sys
import stat
import shutil
import logging
import datetime
import time
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple

# Set up module-level logger
logger = logging.getLogger(__name__)

def collect_file_metadata(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Collect file metadata for preservation.
    
    Args:
        path: The file path to collect metadata from
    
    Returns:
        A dictionary of file metadata
    """
    metadata = {}
    path_obj = Path(path)
    
    try:
        # Get basic file stats
        file_stat = path_obj.stat()
        
        # Store file mode (permissions)
        metadata['mode'] = file_stat.st_mode
        
        # Store timestamps
        metadata['timestamps'] = {
            'modified': file_stat.st_mtime,
            'accessed': file_stat.st_atime,
            # Note: st_ctime means different things on Unix vs Windows
            'created': file_stat.st_ctime,
            'modified_iso': datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'accessed_iso': datetime.datetime.fromtimestamp(file_stat.st_atime).isoformat(),
            'created_iso': datetime.datetime.fromtimestamp(file_stat.st_ctime).isoformat()
        }
        
        # Store size
        metadata['size'] = file_stat.st_size
        
        # Platform-specific metadata
        if platform.system() == 'Windows':
            metadata['windows'] = _collect_windows_metadata(path_obj)
        else:
            # Unix-specific metadata
            metadata['unix'] = {
                'uid': file_stat.st_uid,
                'gid': file_stat.st_gid
            }
        
        return metadata
    except Exception as e:
        logger.error(f"Error collecting metadata for {path}: {e}")
        return metadata

def _collect_windows_metadata(path: Path) -> Dict[str, Any]:
    """
    Collect Windows-specific file metadata.
    
    Args:
        path: The file path to collect metadata from
    
    Returns:
        A dictionary of Windows-specific metadata
    """
    windows_metadata = {}
    
    if platform.system() != 'Windows':
        return windows_metadata
    
    try:
        # Try to use pywin32 if available
        try:
            import win32api
            import win32con
            
            # Get file attributes
            attrs = win32api.GetFileAttributes(str(path))
            windows_metadata['attributes'] = attrs
            windows_metadata['is_hidden'] = bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
            windows_metadata['is_system'] = bool(attrs & win32con.FILE_ATTRIBUTE_SYSTEM)
            windows_metadata['is_readonly'] = bool(attrs & win32con.FILE_ATTRIBUTE_READONLY)
            windows_metadata['is_archive'] = bool(attrs & win32con.FILE_ATTRIBUTE_ARCHIVE)
            
            # Get security information
            try:
                import win32security
                security_info = win32security.GetFileSecurity(
                    str(path), 
                    win32security.OWNER_SECURITY_INFORMATION | 
                    win32security.GROUP_SECURITY_INFORMATION | 
                    win32security.DACL_SECURITY_INFORMATION
                )
                
                # Get owner and group
                owner_sid = security_info.GetSecurityDescriptorOwner()
                group_sid = security_info.GetSecurityDescriptorGroup()
                
                try:
                    # Convert SIDs to names
                    owner_name, owner_domain, owner_type = win32security.LookupAccountSid(None, owner_sid)
                    group_name, group_domain, group_type = win32security.LookupAccountSid(None, group_sid)
                    
                    windows_metadata['owner'] = f"{owner_domain}\\{owner_name}"
                    windows_metadata['group'] = f"{group_domain}\\{group_name}"
                except:
                    # If lookup fails, just use the SID
                    windows_metadata['owner_sid'] = str(owner_sid)
                    windows_metadata['group_sid'] = str(group_sid)
                
                # Store security descriptor for later use
                windows_metadata['security_descriptor'] = security_info
            except Exception as e:
                logger.debug(f"Error getting security info: {e}")
            
        except ImportError:
            logger.debug("pywin32 not available, using limited Windows metadata collection")
            
            # Use attrib command as fallback
            try:
                import subprocess
                result = subprocess.run(['attrib', str(path)], capture_output=True, text=True)
                if result.returncode == 0:
                    attrs_line = result.stdout.strip()
                    windows_metadata['attrib_output'] = attrs_line
                    
                    # Parse attrib output
                    windows_metadata['is_readonly'] = 'R' in attrs_line
                    windows_metadata['is_hidden'] = 'H' in attrs_line
                    windows_metadata['is_system'] = 'S' in attrs_line
                    windows_metadata['is_archive'] = 'A' in attrs_line
            except Exception as attrib_error:
                logger.debug(f"Error running attrib command: {attrib_error}")
        
        return windows_metadata
    except Exception as e:
        logger.error(f"Error collecting Windows metadata for {path}: {e}")
        return windows_metadata

def apply_file_metadata(path: Union[str, Path], metadata: Dict[str, Any]) -> bool:
    """
    Apply metadata to a file.
    
    Args:
        path: The file path to apply metadata to
        metadata: The metadata to apply
    
    Returns:
        True if successful, False otherwise
    """
    path_obj = Path(path)
    success = True
    
    try:
        # Apply mode (permissions)
        if 'mode' in metadata:
            try:
                os.chmod(path_obj, metadata['mode'])
            except Exception as e:
                logger.warning(f"Error applying permissions to {path}: {e}")
                success = False
        
        # Apply timestamps
        if 'timestamps' in metadata:
            timestamps = metadata['timestamps']
            try:
                os.utime(
                    path_obj,
                    (timestamps['accessed'], timestamps['modified'])
                )
            except Exception as e:
                logger.warning(f"Error applying timestamps to {path}: {e}")
                success = False
        
        # Apply platform-specific metadata
        if platform.system() == 'Windows' and 'windows' in metadata:
            success = success and _apply_windows_metadata(path_obj, metadata['windows'])
        elif platform.system() != 'Windows' and 'unix' in metadata:
            success = success and _apply_unix_metadata(path_obj, metadata['unix'])
        
        return success
    except Exception as e:
        logger.error(f"Error applying metadata to {path}: {e}")
        return False

def _apply_windows_metadata(path: Path, metadata: Dict[str, Any]) -> bool:
    """
    Apply Windows-specific metadata to a file.
    
    Args:
        path: The file path to apply metadata to
        metadata: The Windows-specific metadata to apply
    
    Returns:
        True if successful, False otherwise
    """
    if platform.system() != 'Windows':
        return False
    
    success = True
    
    try:
        # Try to use pywin32 if available
        try:
            import win32api
            import win32con
            import win32security
            
            # Apply file attributes
            if 'attributes' in metadata:
                win32api.SetFileAttributes(str(path), metadata['attributes'])
            else:
                # Apply individual attributes
                current_attrs = win32api.GetFileAttributes(str(path))
                
                if 'is_readonly' in metadata:
                    if metadata['is_readonly']:
                        current_attrs |= win32con.FILE_ATTRIBUTE_READONLY
                    else:
                        current_attrs &= ~win32con.FILE_ATTRIBUTE_READONLY
                
                if 'is_hidden' in metadata:
                    if metadata['is_hidden']:
                        current_attrs |= win32con.FILE_ATTRIBUTE_HIDDEN
                    else:
                        current_attrs &= ~win32con.FILE_ATTRIBUTE_HIDDEN
                
                if 'is_system' in metadata:
                    if metadata['is_system']:
                        current_attrs |= win32con.FILE_ATTRIBUTE_SYSTEM
                    else:
                        current_attrs &= ~win32con.FILE_ATTRIBUTE_SYSTEM
                
                if 'is_archive' in metadata:
                    if metadata['is_archive']:
                        current_attrs |= win32con.FILE_ATTRIBUTE_ARCHIVE
                    else:
                        current_attrs &= ~win32con.FILE_ATTRIBUTE_ARCHIVE
                
                win32api.SetFileAttributes(str(path), current_attrs)
            
            # Apply security information if available
            if 'security_descriptor' in metadata:
                try:
                    win32security.SetFileSecurity(
                        str(path),
                        win32security.OWNER_SECURITY_INFORMATION | 
                        win32security.GROUP_SECURITY_INFORMATION | 
                        win32security.DACL_SECURITY_INFORMATION,
                        metadata['security_descriptor']
                    )
                except Exception as e:
                    logger.warning(f"Error applying security information to {path}: {e}")
                    success = False
        
        except ImportError:
            logger.debug("pywin32 not available, using limited Windows metadata application")
            
            # Use attrib command as fallback
            if 'attrib_output' in metadata:
                import subprocess
                
                # Reset attributes first
                subprocess.run(['attrib', '-R', '-H', '-S', '-A', str(path)])
                
                # Apply stored attributes
                attrs = ""
                if metadata.get('is_readonly', False):
                    attrs += "+R "
                if metadata.get('is_hidden', False):
                    attrs += "+H "
                if metadata.get('is_system', False):
                    attrs += "+S "
                if metadata.get('is_archive', False):
                    attrs += "+A "
                
                if attrs:
                    subprocess.run(['attrib', *attrs.strip().split(), str(path)])
        
        return success
    
    except Exception as e:
        logger.error(f"Error applying Windows metadata to {path}: {e}")
        return False

def _apply_unix_metadata(path: Path, metadata: Dict[str, Any]) -> bool:
    """
    Apply Unix-specific metadata to a file.
    
    Args:
        path: The file path to apply metadata to
        metadata: The Unix-specific metadata to apply
    
    Returns:
        True if successful, False otherwise
    """
    if platform.system() == 'Windows':
        return False
    
    success = True
    
    try:
        # Apply owner and group
        if 'uid' in metadata and 'gid' in metadata:
            try:
                os.chown(path, metadata['uid'], metadata['gid'])
            except Exception as e:
                logger.warning(f"Error applying owner/group to {path}: {e}")
                success = False
        
        return success
    
    except Exception as e:
        logger.error(f"Error applying Unix metadata to {path}: {e}")
        return False

def compare_metadata(metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two metadata dictionaries and return differences.
    
    Args:
        metadata1: First metadata dictionary
        metadata2: Second metadata dictionary
    
    Returns:
        Dictionary of differences
    """
    differences = {}
    
    # Compare sizes
    if metadata1.get('size') != metadata2.get('size'):
        differences['size'] = {
            'old': metadata1.get('size'),
            'new': metadata2.get('size')
        }
    
    # Compare timestamps
    if 'timestamps' in metadata1 and 'timestamps' in metadata2:
        timestamps1 = metadata1['timestamps']
        timestamps2 = metadata2['timestamps']
        
        timestamp_diffs = {}
        
        for key in ('modified', 'accessed', 'created'):
            if abs((timestamps1.get(key, 0) or 0) - (timestamps2.get(key, 0) or 0)) > 2:
                # Allow 2-second difference to account for filesystem precision
                timestamp_diffs[key] = {
                    'old': timestamps1.get(key),
                    'old_iso': timestamps1.get(f"{key}_iso"),
                    'new': timestamps2.get(key),
                    'new_iso': timestamps2.get(f"{key}_iso")
                }
        
        if timestamp_diffs:
            differences['timestamps'] = timestamp_diffs
    
    # Compare modes (permissions)
    if metadata1.get('mode') != metadata2.get('mode'):
        differences['mode'] = {
            'old': metadata1.get('mode'),
            'new': metadata2.get('mode'),
            'old_octal': oct(metadata1.get('mode', 0)) if metadata1.get('mode') is not None else None,
            'new_octal': oct(metadata2.get('mode', 0)) if metadata2.get('mode') is not None else None
        }
    
    # Compare platform-specific metadata
    if platform.system() == 'Windows':
        # Compare Windows metadata
        if 'windows' in metadata1 and 'windows' in metadata2:
            windows1 = metadata1['windows']
            windows2 = metadata2['windows']
            
            windows_diffs = {}
            
            # Compare attributes
            for attr in ('is_readonly', 'is_hidden', 'is_system', 'is_archive'):
                if windows1.get(attr) != windows2.get(attr):
                    windows_diffs[attr] = {
                        'old': windows1.get(attr),
                        'new': windows2.get(attr)
                    }
            
            if windows_diffs:
                differences['windows'] = windows_diffs
    else:
        # Compare Unix metadata
        if 'unix' in metadata1 and 'unix' in metadata2:
            unix1 = metadata1['unix']
            unix2 = metadata2['unix']
            
            unix_diffs = {}
            
            if unix1.get('uid') != unix2.get('uid'):
                unix_diffs['uid'] = {
                    'old': unix1.get('uid'),
                    'new': unix2.get('uid')
                }
            
            if unix1.get('gid') != unix2.get('gid'):
                unix_diffs['gid'] = {
                    'old': unix1.get('gid'),
                    'new': unix2.get('gid')
                }
            
            if unix_diffs:
                differences['unix'] = unix_diffs
    
    return differences

def get_metadata_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a human-readable summary of file metadata.
    
    Args:
        metadata: The metadata to summarize
    
    Returns:
        Dictionary with summarized metadata
    """
    summary = {}
    
    # Size
    if 'size' in metadata:
        size = metadata['size']
        if size < 1024:
            summary['size'] = f"{size} bytes"
        elif size < 1024 * 1024:
            summary['size'] = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            summary['size'] = f"{size / (1024 * 1024):.1f} MB"
        else:
            summary['size'] = f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    # Timestamps
    if 'timestamps' in metadata:
        timestamps = metadata['timestamps']
        summary['timestamps'] = {
            'modified': timestamps.get('modified_iso', 'Unknown'),
            'accessed': timestamps.get('accessed_iso', 'Unknown'),
            'created': timestamps.get('created_iso', 'Unknown')
        }
    
    # Mode (permissions)
    if 'mode' in metadata:
        mode = metadata['mode']
        summary['permissions'] = oct(mode)[2:] if mode is not None else 'Unknown'
    
    # Platform-specific
    if platform.system() == 'Windows' and 'windows' in metadata:
        windows = metadata['windows']
        summary['attributes'] = []
        
        if windows.get('is_readonly', False):
            summary['attributes'].append('Read-only')
        if windows.get('is_hidden', False):
            summary['attributes'].append('Hidden')
        if windows.get('is_system', False):
            summary['attributes'].append('System')
        if windows.get('is_archive', False):
            summary['attributes'].append('Archive')
        
        if 'owner' in windows:
            summary['owner'] = windows['owner']
    
    elif platform.system() != 'Windows' and 'unix' in metadata:
        unix = metadata['unix']
        summary['owner'] = f"UID: {unix.get('uid', 'Unknown')}, GID: {unix.get('gid', 'Unknown')}"
    
    return summary

def metadata_to_json(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert metadata to a JSON-serializable format.
    
    Args:
        metadata: The metadata to convert
    
    Returns:
        JSON-serializable dictionary
    """
    # Create a copy to avoid modifying the original
    result = {}
    
    for key, value in metadata.items():
        if isinstance(value, dict):
            # Recursively convert nested dictionaries
            result[key] = metadata_to_json(value)
        elif isinstance(value, (int, float, str, bool, type(None))):
            # These types are already JSON-serializable
            result[key] = value
        elif isinstance(value, (bytes, bytearray)):
            # Convert bytes to base64
            import base64
            result[key] = base64.b64encode(value).decode('ascii')
        elif hasattr(value, '__dict__'):
            # For custom objects
            try:
                result[key] = str(value)
            except:
                result[key] = f"<non-serializable: {type(value).__name__}>"
        else:
            # For other types, convert to string
            try:
                result[key] = str(value)
            except:
                result[key] = f"<non-serializable: {type(value).__name__}>"
    
    return result

def collect_timestamp_info(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Collect timestamp information from a file.
    
    Args:
        path: Path to the file
    
    Returns:
        Dictionary with timestamp information
    """
    result = {}
    path_obj = Path(path)
    
    try:
        if path_obj.exists():
            stat_result = path_obj.stat()
            
            result = {
                'created': stat_result.st_ctime,
                'modified': stat_result.st_mtime,
                'accessed': stat_result.st_atime,
                'created_iso': datetime.datetime.fromtimestamp(stat_result.st_ctime).isoformat(),
                'modified_iso': datetime.datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
                'accessed_iso': datetime.datetime.fromtimestamp(stat_result.st_atime).isoformat()
            }
    except Exception as e:
        logger.warning(f"Error collecting timestamp info for {path}: {e}")
    
    return result

def apply_timestamp_strategy(path: Union[str, Path], strategy: str, link_timestamps: Optional[Dict[str, Any]] = None, 
                          target_timestamps: Optional[Dict[str, Any]] = None) -> bool:
    """
    Apply timestamps to a file based on a strategy.
    
    Args:
        path: Path to the file
        strategy: Strategy to use ('current', 'symlink', 'target', 'preserve-all')
        link_timestamps: Timestamps from the original symlink (optional)
        target_timestamps: Timestamps from the target file (optional)
    
    Returns:
        True if successful, False otherwise
    """
    path_obj = Path(path)
    
    try:
        if strategy == 'current':
            # Use current time (do nothing)
            return True
            
        elif strategy == 'symlink' and link_timestamps:
            # Use symlink timestamps
            modified = link_timestamps.get('modified')
            accessed = link_timestamps.get('accessed')
            
            if modified and accessed:
                os.utime(path_obj, (accessed, modified))
                return True
            else:
                logger.warning(f"Missing timestamp information for {path}")
                return False
                
        elif strategy == 'target' and target_timestamps:
            # Use target timestamps
            modified = target_timestamps.get('modified')
            accessed = target_timestamps.get('accessed')
            
            if modified and accessed:
                os.utime(path_obj, (accessed, modified))
                return True
            else:
                logger.warning(f"Missing timestamp information for {path}")
                return False
                
        elif strategy == 'preserve-all':
            # Try to preserve all timestamps
            # For Windows, we need extra work for creation time
            
            if platform.system() == 'Windows':
                try:
                    import win32file
                    import win32con
                    import pywintypes
                    
                    # Apply creation time if available
                    created = None
                    if link_timestamps and 'created' in link_timestamps:
                        created = link_timestamps['created']
                    elif target_timestamps and 'created' in target_timestamps:
                        created = target_timestamps['created']
                    
                    if created:
                        # Convert to Windows filetime
                        wintime = pywintypes.Time(created)
                        
                        # Open file and set creation time
                        handle = win32file.CreateFile(
                            str(path_obj),
                            win32con.FILE_WRITE_ATTRIBUTES,
                            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                            None,
                            win32con.OPEN_EXISTING,
                            win32con.FILE_ATTRIBUTE_NORMAL,
                            None
                        )
                        
                        win32file.SetFileTime(handle, wintime)
                        handle.close()
                except ImportError:
                    logger.debug("pywin32 not available, skipping creation time preservation")
                except Exception as e:
                    logger.warning(f"Error setting creation time for {path}: {e}")
            
            # Apply modified and accessed times
            # Try symlink timestamps first, then target timestamps
            modified = None
            accessed = None
            
            if link_timestamps:
                modified = link_timestamps.get('modified')
                accessed = link_timestamps.get('accessed')
            
            if (not modified or not accessed) and target_timestamps:
                modified = modified or target_timestamps.get('modified')
                accessed = accessed or target_timestamps.get('accessed')
            
            if modified and accessed:
                os.utime(path_obj, (accessed, modified))
                return True
            else:
                logger.warning(f"Missing timestamp information for {path}")
                return False
        
        else:
            logger.warning(f"Unknown timestamp strategy: {strategy}")
            return False
            
    except Exception as e:
        logger.error(f"Error applying timestamps to {path}: {e}")
        return False
