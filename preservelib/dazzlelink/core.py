"""
Core functionality for dazzlelink integration.

This module provides functions for integrating with the dazzlelink library,
implementing creation, discovery, and restoration of dazzlelinks.

It provides a simplified implementation when the dazzlelink library is not available,
while using the full functionality when it is.
"""

import os
import sys
import logging
import json
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, Any
from collections import Counter

# Turn on debug logging
DEBUG = True

# Set up module-level logger
logger = logging.getLogger(__name__)

def find_longest_common_path_prefix(paths):
    """Find the longest common directory prefix of a list of paths."""
    if not paths:
        return None
        
    # Convert all paths to Path objects and normalize separators
    normalized_paths = []
    for p in paths:
        try:
            # Convert to string for consistent handling
            path_str = str(p)
            # Convert to forward slashes for consistency
            norm_path = path_str.replace('\\', '/')
            normalized_paths.append(norm_path)
        except Exception:
            # Skip invalid paths
            continue
            
    if not normalized_paths:
        return None
        
    # Split all paths into parts
    parts_list = [p.split('/') for p in normalized_paths]
    
    # Find common prefix parts
    common_parts = []
    for parts_tuple in zip(*parts_list):
        if len(set(parts_tuple)) == 1:  # All parts at this position are the same
            common_parts.append(parts_tuple[0])
        else:
            break
            
    # Special handling for Windows drive letters
    if sys.platform == 'win32' and len(common_parts) > 0:
        # If only the drive letter is common, it's not a useful prefix
        if len(common_parts) == 1 and common_parts[0].endswith(':'):
            drive_letter = common_parts[0]
            # Check if next part is common even if not all paths have it
            next_parts = set()
            for parts in parts_list:
                if len(parts) > 1:
                    next_parts.add(parts[1])
            # If there's a common next part, include it
            if len(next_parts) == 1:
                common_parts.append(next_parts.pop())
                
    # Build the common prefix
    if not common_parts:
        return None
    
    # Join with appropriate separator and convert back to Path
    common_prefix = '/'.join(common_parts)
    # For Windows, we need to add back the path separator if it's just a drive
    if sys.platform == 'win32' and common_prefix.endswith(':'):
        common_prefix += '/'
        
    # Convert to a proper Path object using original separators
    if sys.platform == 'win32':
        common_prefix = common_prefix.replace('/', '\\')
        
    return Path(common_prefix)

def detect_common_dir_patterns(path_str, all_paths=None):
    """
    Detect common directory patterns in a path string.
    Returns a tuple of (pattern_type, base_path, rel_path) if a pattern is found,
    or None if no pattern is detected.
    
    Args:
        path_str: Path string to analyze
        all_paths: Optional list of all paths for context
        
    Returns:
        Tuple of (pattern_type, base_path, rel_path) if a pattern is found,
        or None if no pattern is detected
    """
    # Use the pathutils module for pattern detection
    try:
        from .. import pathutils
        return pathutils.detect_path_patterns(path_str, all_paths)
    except ImportError as e:
        logger.debug(f"Error importing pathutils: {e}")
    
    # Fallback if pathutils is not available
    try:
        # Simple detection of parent directories
        path_obj = Path(path_str)
        parent = path_obj.parent
        
        # Only use non-root parents
        if parent != Path(parent.root):
            rel_path = path_obj.name
            return ('parent_dir', parent, Path(rel_path))
    except Exception as e:
        logger.debug(f"Error in simplified pattern detection: {e}")
    
    # No pattern detected
    return None

# Helper function to ensure a file has the .dazzlelink extension
def ensure_dazzlelink_extension(file_path: Union[str, Path]) -> Path:
    """
    Ensure that a file has the .dazzlelink extension.
    If it doesn't, rename it to add the extension.
    
    Args:
        file_path: The path to check and potentially rename
        
    Returns:
        The path with the .dazzlelink extension
    """
    path_obj = Path(file_path)
    
    if DEBUG:
        logger.debug(f"[DEBUG] Checking path: {path_obj}, ends with .dazzlelink: {str(path_obj).endswith('.dazzlelink')}")
    
    if not str(path_obj).endswith('.dazzlelink'):
        # If the path doesn't have the extension, add it
        new_path = Path(str(path_obj) + '.dazzlelink')
        try:
            if path_obj.exists():
                logger.debug(f"[DEBUG] Renaming {path_obj} to {new_path} to add .dazzlelink extension")
                shutil.move(str(path_obj), str(new_path))
                return new_path
            else:
                logger.debug(f"[DEBUG] Path doesn't exist, can't rename: {path_obj}")
                # Just return the path with extension added
                return new_path
        except Exception as rename_error:
            logger.warning(f"[DEBUG] Failed to rename dazzlelink file: {rename_error}")
    
    return path_obj

# Check if dazzlelink is available
HAVE_DAZZLELINK = False
try:
    import dazzlelink
    HAVE_DAZZLELINK = True
    logger.debug("Dazzlelink module available, using full implementation")
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
        logger.debug("Bundled dazzlelink module available, using full implementation")
    except ImportError:
        logger.debug("Dazzlelink module not available, using simplified implementation")


def is_available() -> bool:
    """
    Check if dazzlelink integration is available.
    
    Returns:
        True if dazzlelink is available, False otherwise
    """
    return HAVE_DAZZLELINK


class SimpleDazzleLinkData:
    """
    A simplified version of dazzlelink's DazzleLinkData class.
    Used when the dazzlelink library is not available.
    """
    
    def __init__(self):
        """Initialize the data structure."""
        self.data = {
            "original_path": None,
            "target_path": None,
            "created_at": datetime.datetime.now().isoformat(),
            "timestamps": {
                "created": None,
                "modified": None,
                "accessed": None
            },
            "metadata": {},
            "config": {
                "default_mode": "info"  # Default mode for dazzlelink execution
            }
        }
    
    def set_original_path(self, path: str) -> None:
        """Set the original path."""
        self.data["original_path"] = path
    
    def set_target_path(self, path: str) -> None:
        """Set the target path."""
        self.data["target_path"] = path
    
    def get_original_path(self) -> Optional[str]:
        """Get the original path."""
        return self.data["original_path"]
    
    def get_target_path(self) -> Optional[str]:
        """Get the target path."""
        return self.data["target_path"]
    
    def get_creation_date(self) -> str:
        """Get the creation date."""
        return self.data["created_at"]
    
    def set_link_timestamps(self, **kwargs) -> None:
        """Set link timestamps."""
        for key, value in kwargs.items():
            if key in self.data["timestamps"]:
                self.data["timestamps"][key] = value
    
    def get_link_timestamps(self) -> Dict[str, Any]:
        """Get link timestamps."""
        return self.data["timestamps"]
        
    def set_default_mode(self, mode: str) -> None:
        """Set the default execution mode."""
        if "config" not in self.data:
            self.data["config"] = {}
        self.data["config"]["default_mode"] = mode
        
    def get_default_mode(self) -> str:
        """Get the default execution mode."""
        if "config" in self.data and "default_mode" in self.data["config"]:
            return self.data["config"]["default_mode"]
        return "info"  # Default to info mode
    
    def to_json(self) -> str:
        """Convert data to JSON string."""
        return json.dumps(self.data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SimpleDazzleLinkData':
        """Create instance from JSON string."""
        instance = cls()
        try:
            instance.data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in dazzlelink data")
        return instance
    
    @classmethod
    def from_file(cls, path: str) -> 'SimpleDazzleLinkData':
        """Load from a file."""
        instance = cls()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                instance.data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            logger.error(f"Error loading dazzlelink data from {path}: {e}")
        return instance
    
    def save_to_file(self, path: str, make_executable: bool = False) -> bool:
        """Save to a file."""
        try:
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            
            if make_executable and sys.platform != 'win32':
                # Make file executable on Unix-like systems
                mode = os.stat(path).st_mode
                os.chmod(path, mode | 0o111)  # Add executable bit
            
            return True
        except Exception as e:
            logger.error(f"Error saving dazzlelink data to {path}: {e}")
            return False


def create_dazzlelink(
    source_path: Union[str, Path], 
    dest_path: Union[str, Path],
    dazzlelink_dir: Optional[Union[str, Path]] = None,
    path_style: str = 'relative',
    dest_base: Optional[Union[str, Path]] = None,
    mode: str = 'info',  # Default mode: 'info', 'open', 'auto', etc.
    all_source_files: Optional[List[Union[str, Path]]] = None,  # Added all_source_files parameter
    options: Optional[Dict[str, Any]] = None  # Additional options parameter
) -> Optional[Path]:
    """
    Create a dazzlelink from a source file to a destination file.
    
    Args:
        source_path: Original source path
        dest_path: Destination file path
        dazzlelink_dir: Directory for dazzlelinks (optional)
        path_style: Path preservation style ('relative', 'absolute', 'flat')
        dest_base: Base destination directory (required for relative/absolute path styles)
        mode: Execution mode for the dazzlelink ('info', 'open', 'auto')
        all_source_files: List of all source files for path pattern detection
        options: Additional options for dazzlelink creation
        
    Returns:
        Path to the created dazzlelink, or None if creation failed
    """
    # Initialize options if not provided
    if options is None:
        options = {}
        
    # Use all_source_files parameter, or extract from options if not provided directly
    if all_source_files is None:
        all_source_files = options.get('all_source_files', [])
    
    # First try to use the real dazzlelink library if available
    if HAVE_DAZZLELINK:
        try:
            # Determine link path
            link_path = None
            if dazzlelink_dir:
                # Create path in dazzlelink_dir that mirrors destination structure
                dazzle_dir = Path(dazzlelink_dir)
                dazzle_dir.mkdir(parents=True, exist_ok=True)
                
                # Different behavior based on path style
                if path_style == 'flat' or not dest_base:
                    # For flat structure, just use filename with .dazzlelink extension
                    filename = Path(dest_path).name + '.dazzlelink'
                    link_path = dazzle_dir / filename
                    logger.debug(f"[DEBUG] Real impl - flat path style: {link_path}")
                else:
                    # For relative or absolute, mirror the structure
                    try:
                        if path_style == 'relative':
                            # For relative style, use source_path to ensure directory structure is preserved
                            try:
                                # Try to identify common base directory
                                source_path_obj = Path(source_path)
                                dest_path_obj = Path(dest_path)
                                
                                # Define a helper function to handle potential errors
                                def try_relative_to(path_obj, base_path):
                                    try:
                                        return path_obj.relative_to(base_path), True
                                    except ValueError:
                                        return None, False
                                    except Exception as e:
                                        logger.error(f"Error in try_relative_to: {e}")
                                        return None, False
                                
                                # The link path should match the destination path structure
                                # First get the directory structure from the destination path
                                dest_rel_path = None
                                if dest_base:
                                    dest_rel_path, success = try_relative_to(dest_path_obj, Path(dest_base))
                                    if success and dest_rel_path:
                                        filename = dest_rel_path.name + '.dazzlelink'
                                        link_path = dazzle_dir / dest_rel_path.parent / filename
                                        logger.debug(f"[DEBUG] Real impl - using dest structure: {link_path}")
                                
                                # If that fails, try automatic detection of path patterns
                                if not dest_rel_path:
                                    source_path_str = str(source_path_obj)
                                    
                                    # Try to detect common directory patterns first
                                    # Use the all_source_files parameter 
                                    all_paths = all_source_files if all_source_files else None
                                    
                                    # Call detect_common_dir_patterns with all_paths if available
                                    pattern_result = detect_common_dir_patterns(source_path_str, all_paths)
                                    if pattern_result:
                                        pattern_type, base_path, rel_path = pattern_result
                                        logger.debug(f"[DEBUG] Real impl - detected pattern: {pattern_type}, base: {base_path}, rel: {rel_path}")
                                        filename = rel_path.name + '.dazzlelink'
                                        link_path = dazzle_dir / rel_path.parent / filename
                                        logger.debug(f"[DEBUG] Real impl - using detected pattern: {link_path}")
                                    else:
                                        # If no specific pattern matches, try with common prefix algorithm
                                        common_base = None
                                        if all_paths and len(all_paths) > 1:
                                            common_base = find_longest_common_path_prefix(all_paths)
                                            
                                        if common_base:
                                            try:
                                                rel_path = source_path_obj.relative_to(common_base)
                                                filename = rel_path.name + '.dazzlelink'
                                                link_path = dazzle_dir / rel_path.parent / filename
                                                logger.debug(f"[DEBUG] Real impl - using common base: {common_base}, path: {link_path}")
                                            except ValueError:
                                                # Couldn't make relative to common base
                                                pass
                                                
                                        # Last resort - just use the filename
                                        if not locals().get('link_path'):
                                            filename = source_path_obj.name + '.dazzlelink'
                                            link_path = dazzle_dir / filename
                                            logger.debug(f"[DEBUG] Real impl - filename only: {link_path}")
                            except ValueError:
                                # Ultimate fallback to just the filename
                                filename = Path(dest_path).name + '.dazzlelink'
                                link_path = dazzle_dir / filename
                                logger.debug(f"[DEBUG] Real impl - relative path fallback: {link_path}")
                        elif path_style == 'absolute':
                            # For absolute style, use source_path for path structure (this is the key fix)
                            # This ensures we use the original path, not the destination path that includes dest_base
                            source_path_obj = Path(source_path)
                            if sys.platform == 'win32':
                                # Windows: use drive letter as directory
                                drive, path_part = os.path.splitdrive(str(source_path_obj))
                                drive = drive.rstrip(':')  # Remove colon
                                # Extract filename and add .dazzlelink extension
                                path_obj = Path(path_part.lstrip('\\/'))
                                filename = path_obj.name + '.dazzlelink'
                                link_path = dazzle_dir / drive / path_obj.parent / filename
                                logger.debug(f"[DEBUG] Real impl - absolute path style (Windows): {link_path}")
                            else:
                                # Unix: use root-relative path
                                path_obj = Path(str(source_path_obj).lstrip('/'))
                                filename = path_obj.name + '.dazzlelink'
                                link_path = dazzle_dir / path_obj.parent / filename
                                logger.debug(f"[DEBUG] Real impl - absolute path style (Unix): {link_path}")
                    except Exception as e:
                        # Fallback to just using the filename with .dazzlelink extension
                        logger.warning(f"Error mirroring path structure: {e}")
                        # Even in fallback, use source_path for absolute style
                        if path_style == 'absolute':
                            filename = Path(source_path).name + '.dazzlelink'
                        else:
                            filename = Path(dest_path).name + '.dazzlelink'
                        link_path = dazzle_dir / filename
                        logger.debug(f"[DEBUG] Real impl - path structure fallback: {link_path}")
                
                # Create parent directory if needed
                link_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Create link alongside destination
                link_path = Path(str(dest_path) + '.dazzlelink')
            
            # Create the dazzlelink using the real library
            if hasattr(dazzlelink, 'create_link'):
                # Use the function directly if available
                logger.debug(f"[DEBUG] Calling dazzlelink.create_link with source={source_path}, link_path={link_path}, mode={mode}")
                dazzlelink_path = dazzlelink.create_link(str(source_path), str(link_path), mode=mode)
                logger.debug(f"[DEBUG] Created dazzlelink with create_link function: {dazzlelink_path} -> {source_path}")
                
                # Use helper function to ensure proper extension
                result_path = ensure_dazzlelink_extension(dazzlelink_path)
                return result_path
                
            elif hasattr(dazzlelink, 'export_link'):
                # Use export_link function if available (newer versions)
                logger.debug(f"[DEBUG] Calling dazzlelink.export_link with source={source_path}, link_path={link_path}, mode={mode}")
                dazzlelink_path = dazzlelink.export_link(str(source_path), str(link_path), mode=mode)
                logger.debug(f"[DEBUG] Created dazzlelink with export_link function: {dazzlelink_path} -> {source_path}")
                
                # Use helper function to ensure proper extension
                result_path = ensure_dazzlelink_extension(dazzlelink_path)
                return result_path
                
            elif hasattr(dazzlelink, 'DazzleLink'):
                # Use the class if the functions aren't available
                dl = dazzlelink.DazzleLink()
                # Check which method is available (API evolved over time)
                if hasattr(dl, 'serialize_link'):
                    logger.debug(f"[DEBUG] Calling DazzleLink.serialize_link with link_path={source_path}, output_path={link_path}, mode={mode}")
                    dazzlelink_path = dl.serialize_link(
                        link_path=str(source_path),
                        output_path=str(link_path),
                        require_symlink=False,
                        mode=mode
                    )
                    logger.debug(f"[DEBUG] DazzleLink.serialize_link returned: {dazzlelink_path}")
                    
                    # Use helper function to ensure proper extension
                    result_path = ensure_dazzlelink_extension(dazzlelink_path)
                    dazzlelink_path = str(result_path)
                    
                elif hasattr(dl, 'create_dazzlelink'):
                    logger.debug(f"[DEBUG] Calling DazzleLink.create_dazzlelink with target={source_path}, output_path={link_path}, mode={mode}")
                    dazzlelink_path = dl.create_dazzlelink(
                        target=str(source_path),
                        output_path=str(link_path),
                        mode=mode
                    )
                    logger.debug(f"[DEBUG] DazzleLink.create_dazzlelink returned: {dazzlelink_path}")
                    
                    # Use helper function to ensure proper extension
                    result_path = ensure_dazzlelink_extension(dazzlelink_path)
                    dazzlelink_path = str(result_path)
                    
                else:
                    logger.warning("DazzleLink class found but missing expected methods")
                    raise AttributeError("DazzleLink API mismatch")
                    
                logger.debug(f"[DEBUG] Created dazzlelink with DazzleLink class: {dazzlelink_path} -> {source_path}")
                return Path(dazzlelink_path)
            else:
                logger.warning("Dazzlelink library found but API is different than expected")
                raise AttributeError("Dazzlelink API mismatch")
        except Exception as e:
            logger.warning(f"Error using dazzlelink library, falling back to simplified implementation: {e}")
            # Fall through to the simplified implementation
    
    # Use simplified implementation if real library isn't available or failed
    try:
        # Make sure all_source_files is available in the simplified implementation
        if 'all_source_files' not in locals():
            all_source_files = options.get('all_source_files', [])
            
        # Determine link path
        link_path = None
        if dazzlelink_dir:
            # Create path in dazzlelink_dir that mirrors destination structure
            dazzle_dir = Path(dazzlelink_dir)
            dazzle_dir.mkdir(parents=True, exist_ok=True)
            
            # Different behavior based on path style
            if path_style == 'flat' or not dest_base:
                # For flat structure, just use filename with .dazzlelink extension
                filename = Path(dest_path).name + '.dazzlelink'
                link_path = dazzle_dir / filename
                logger.debug(f"[DEBUG] Simplified flat path style: {link_path}")
            else:
                # For relative or absolute, mirror the structure
                try:
                    # Try to get relative path from dest_base
                    dest_path_obj = Path(dest_path)
                    dest_base_obj = Path(dest_base)
                    
                    if path_style == 'relative':
                        # For relative style, use the same algorithm as the real implementation
                        try:
                            # Use the destination path structure first if possible
                            source_path_obj = Path(source_path)
                            dest_path_obj = Path(dest_path)
                            source_path_str = str(source_path_obj)
                            
                            # Helper function for relative paths
                            def try_relative_to(path_obj, base_path):
                                try:
                                    return path_obj.relative_to(base_path), True
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"[DEBUG] Simplified try_relative_to error: {e}")
                                    return None, False
                            
                            # First try the destination structure
                            if dest_base_obj and dest_path_obj:
                                rel_path, success = try_relative_to(dest_path_obj, dest_base_obj)
                                if success and rel_path:
                                    filename = rel_path.name + '.dazzlelink'
                                    link_path = dazzle_dir / rel_path.parent / filename
                                    logger.debug(f"[DEBUG] Simplified - using dest structure: {link_path}")
                                    # We've found a good path, just continue
                            
                            # Try to detect common directory patterns first
                            # Use the all_source_files parameter
                            all_paths = all_source_files if all_source_files else None
                            
                            # Call detect_common_dir_patterns with all_paths if available
                            pattern_result = detect_common_dir_patterns(source_path_str, all_paths)
                            if pattern_result:
                                pattern_type, base_path, rel_path = pattern_result
                                logger.debug(f"[DEBUG] Simplified - detected pattern: {pattern_type}, base: {base_path}, rel: {rel_path}")
                                filename = rel_path.name + '.dazzlelink'
                                link_path = dazzle_dir / rel_path.parent / filename
                                logger.debug(f"[DEBUG] Simplified - using detected pattern: {link_path}")
                                # We've found a good path, just continue
                            
                            # Try to find common prefix if we have multiple files
                            common_base = None
                            # Use all_source_files parameter for pattern detection
                            if all_paths and len(all_paths) > 1:
                                common_base = find_longest_common_path_prefix(all_paths)
                                if common_base:
                                    try:
                                        rel_path = source_path_obj.relative_to(common_base)
                                        filename = rel_path.name + '.dazzlelink'
                                        link_path = dazzle_dir / rel_path.parent / filename
                                        logger.debug(f"[DEBUG] Simplified - using common base: {common_base}, path: {link_path}")
                                        # We've found a good path, just continue
                                    except ValueError:
                                        # Couldn't make relative to common base
                                        pass
                            
                            # Last resort - just use the filename
                            filename = source_path_obj.name + '.dazzlelink'
                            link_path = dazzle_dir / filename
                            logger.debug(f"[DEBUG] Simplified - filename only: {link_path}")
                        except ValueError:
                            # Ultimate fallback to just the filename
                            filename = dest_path_obj.name + '.dazzlelink'
                            link_path = dazzle_dir / filename
                            logger.debug(f"[DEBUG] Simplified relative path fallback: {link_path}")
                    elif path_style == 'absolute':
                        # For absolute style, use source_path for path structure (this is the key fix)
                        # This ensures we use the original path, not the destination path that includes dest_base
                        source_path_obj = Path(source_path)
                        if sys.platform == 'win32':
                            # Windows: use drive letter as directory
                            drive, path_part = os.path.splitdrive(str(source_path_obj))
                            drive = drive.rstrip(':')  # Remove colon
                            # Extract filename and add .dazzlelink extension
                            path_obj = Path(path_part.lstrip('\\/'))
                            filename = path_obj.name + '.dazzlelink'
                            link_path = dazzle_dir / drive / path_obj.parent / filename
                            logger.debug(f"[DEBUG] Simplified absolute path style (Windows): {link_path}")
                        else:
                            # Unix: use root-relative path
                            path_obj = Path(str(source_path_obj).lstrip('/'))
                            filename = path_obj.name + '.dazzlelink'
                            link_path = dazzle_dir / path_obj.parent / filename
                            logger.debug(f"[DEBUG] Simplified absolute path style (Unix): {link_path}")
                except Exception as e:
                    # Fallback to just using the filename with .dazzlelink extension
                    logger.warning(f"Error mirroring path structure: {e}")
                    # Even in fallback, use source_path for absolute style
                    if path_style == 'absolute':
                        filename = Path(source_path).name + '.dazzlelink'
                    else:
                        filename = Path(dest_path).name + '.dazzlelink'
                    link_path = dazzle_dir / filename
                    logger.debug(f"[DEBUG] Simplified path structure fallback: {link_path}")
            
            # Create parent directory if needed
            link_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Create link alongside destination
            link_path = Path(str(dest_path) + '.dazzlelink')
        
        # Create and save the dazzlelink data
        dl_data = SimpleDazzleLinkData()
        dl_data.set_original_path(str(source_path))
        dl_data.set_target_path(str(dest_path))
        dl_data.set_default_mode(mode)  # Set the requested execution mode
        
        # Try to collect file stats for timestamps
        try:
            source_stat = Path(source_path).stat()
            dl_data.set_link_timestamps(
                created=source_stat.st_ctime,
                modified=source_stat.st_mtime,
                accessed=source_stat.st_atime
            )
        except (FileNotFoundError, PermissionError):
            pass  # Ignore errors
        
        # Save the dazzlelink
        logger.debug(f"[DEBUG] Saving simplified dazzlelink to file: {link_path}")
        dl_data.save_to_file(str(link_path))
        logger.debug(f"[DEBUG] Created simplified dazzlelink: {link_path} -> {source_path}")
        return link_path
        
    except Exception as e:
        logger.error(f"Error creating simplified dazzlelink: {e}")
        return None


def find_dazzlelinks_in_dir(
    directory: Union[str, Path],
    recursive: bool = True,
    pattern: str = '*.dazzlelink'
) -> List[Path]:
    """
    Find dazzlelink files in a directory.
    
    Args:
        directory: Directory to search
        recursive: Whether to search recursively
        pattern: Glob pattern to match dazzlelink filenames
        
    Returns:
        List of dazzlelink file paths
    """
    if HAVE_DAZZLELINK:
        try:
            # Try different API versions
            if hasattr(dazzlelink, 'find_dazzlelinks'):
                # Use direct function if available
                return [Path(p) for p in dazzlelink.find_dazzlelinks(
                    [str(directory)], 
                    recursive=recursive, 
                    pattern=pattern
                )]
            elif hasattr(dazzlelink, 'DazzleLink'):
                # Try using the DazzleLink class
                dl = dazzlelink.DazzleLink()
                if hasattr(dl, 'find_dazzlelinks'):
                    return [Path(p) for p in dl.find_dazzlelinks(
                        [str(directory)],
                        recursive=recursive,
                        pattern=pattern
                    )]
            elif hasattr(dazzlelink, 'scan') and callable(dazzlelink.scan):
                # Newer versions might use scan
                return [Path(p) for p in dazzlelink.scan(
                    str(directory),
                    recursive=recursive
                ) if Path(p).match(pattern)]
            else:
                logger.warning("Dazzlelink library found but find_dazzlelinks not available")
                # Fall through to the simplified implementation
        except Exception as e:
            logger.warning(f"Error using dazzlelink library to find links, falling back to simplified implementation: {e}")
    
    # Use simplified implementation
    try:
        directory_path = Path(directory)
        found_links = []
        
        if recursive:
            # Use recursive glob
            for path in directory_path.rglob(pattern):
                if path.is_file():
                    found_links.append(path)
        else:
            # Use non-recursive glob
            for path in directory_path.glob(pattern):
                if path.is_file():
                    found_links.append(path)
        
        return found_links
    except Exception as e:
        logger.error(f"Error finding dazzlelinks: {e}")
        return []


def restore_from_dazzlelink(
    dazzlelink_path: Union[str, Path],
    target_location: Optional[Union[str, Path]] = None
) -> Optional[Path]:
    """
    Restore a file from a dazzlelink.
    
    Args:
        dazzlelink_path: Path to the dazzlelink file
        target_location: Override location for the recreated file
        
    Returns:
        Path to the original file location, or None if restoration failed
    """
    if HAVE_DAZZLELINK:
        try:
            # Try different API versions
            if hasattr(dazzlelink, 'import_link'):
                # Newer versions use import_link
                return Path(dazzlelink.import_link(
                    str(dazzlelink_path),
                    target_location=str(target_location) if target_location else None
                ))
            elif hasattr(dazzlelink, 'DazzleLink'):
                # Try using the DazzleLink class
                dl = dazzlelink.DazzleLink()
                if hasattr(dl, 'deserialize_link'):
                    return Path(dl.deserialize_link(
                        str(dazzlelink_path),
                        target_location=str(target_location) if target_location else None
                    ))
                else:
                    logger.warning("DazzleLink class found but missing deserialize_link method")
                    raise AttributeError("DazzleLink API mismatch")
            else:
                logger.warning("Dazzlelink library found but API is different than expected")
                raise AttributeError("Dazzlelink API mismatch")
        except Exception as e:
            logger.warning(f"Error using dazzlelink library to restore link, falling back to simplified implementation: {e}")
    
    # Use simplified implementation
    try:
        # Load dazzlelink data
        dl_data = SimpleDazzleLinkData.from_file(str(dazzlelink_path))
        original_path = dl_data.get_original_path()
        
        if not original_path:
            logger.error(f"No original path in dazzlelink: {dazzlelink_path}")
            return None
        
        # Return the original path
        return Path(original_path)
    except Exception as e:
        logger.error(f"Error restoring from dazzlelink: {e}")
        return None


def dazzlelink_to_manifest(
    dazzlelink_paths: List[Union[str, Path]]
) -> Dict[str, Any]:
    """
    Convert dazzlelink files to a manifest-compatible structure.
    
    Args:
        dazzlelink_paths: List of dazzlelink file paths
        
    Returns:
        Dictionary with manifest structure compatible with PreserveManifest
    """
    manifest_data = {
        "manifest_version": 1,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "files": {},
        "operations": [{
            "id": 0,
            "type": "CONVERT_DAZZLELINKS",
            "timestamp": datetime.datetime.now().isoformat(),
        }],
        "metadata": {
            "source": "dazzlelink",
            "dazzlelink_count": len(dazzlelink_paths)
        }
    }
    
    # Process each dazzlelink
    for i, dl_path in enumerate(dazzlelink_paths):
        try:
            # Load dazzlelink data
            dl_data = None
            
            if HAVE_DAZZLELINK and hasattr(dazzlelink, 'DazzleLinkData'):
                # Try using the real library first
                try:
                    dl_data = dazzlelink.DazzleLinkData.from_file(str(dl_path))
                    original_path = dl_data.get_original_path()
                    target_path = dl_data.get_target_path()
                    creation_date = dl_data.get_creation_date()
                    timestamps = dl_data.get_link_timestamps()
                except Exception as e:
                    logger.warning(f"Error using dazzlelink library to read link, falling back to simplified implementation: {e}")
                    dl_data = None
            
            # Fall back to simplified implementation if needed
            if dl_data is None:
                dl_data = SimpleDazzleLinkData.from_file(str(dl_path))
                original_path = dl_data.get_original_path()
                target_path = dl_data.get_target_path()
                creation_date = dl_data.get_creation_date()
                timestamps = dl_data.get_link_timestamps()
            
            if not original_path or not target_path:
                logger.warning(f"Missing path information in dazzlelink: {dl_path}")
                continue
            
            # Generate a unique file ID
            file_id = f"dazzlelink_{i}_{Path(original_path).name}"
            
            # Create file entry
            file_info = {
                "source_path": original_path,
                "destination_path": target_path,
                "added_at": creation_date,
                "history": [{
                    "timestamp": creation_date,
                    "operation_id": 0
                }]
            }
            
            # Add timestamps
            if timestamps:
                file_info["timestamps"] = timestamps
            
            # Add to manifest
            manifest_data["files"][file_id] = file_info
            
        except Exception as e:
            logger.error(f"Error processing dazzlelink {dl_path}: {e}")
    
    return manifest_data


def manifest_to_dazzlelinks(
    manifest: Dict[str, Any],
    output_dir: Union[str, Path],
    make_executable: bool = False
) -> List[Path]:
    """
    Convert a manifest to dazzlelink files.
    
    Args:
        manifest: Manifest data structure
        output_dir: Directory to store dazzlelink files
        make_executable: Whether to make dazzlelinks executable
        
    Returns:
        List of created dazzlelink file paths
    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    created_dazzlelinks = []
    
    # Process each file in the manifest
    for file_id, file_info in manifest.get("files", {}).items():
        source_path = file_info.get("source_path")
        destination_path = file_info.get("destination_path")
        
        if not source_path or not destination_path:
            logger.warning(f"Missing path information for file {file_id}")
            continue
        
        try:
            # Create output path for dazzlelink
            dl_name = f"{Path(source_path).name}.dazzlelink"
            dl_path = output_dir_path / dl_name
            
            # Try to use the real library first
            if HAVE_DAZZLELINK:
                try:
                    if hasattr(dazzlelink, 'create_link'):
                        # Try to create the dazzlelink directly
                        dazzlelink_path = dazzlelink.create_link(source_path, str(dl_path))
                        created_dazzlelinks.append(Path(dazzlelink_path))
                        continue  # Skip the simplified implementation
                    elif hasattr(dazzlelink, 'DazzleLinkData'):
                        # Try using DazzleLinkData if available
                        dl_data = dazzlelink.DazzleLinkData()
                        dl_data.set_original_path(source_path)
                        dl_data.set_target_path(destination_path)
                        
                        # Set timestamps if available
                        if "timestamps" in file_info:
                            timestamps = file_info["timestamps"]
                            dl_data.set_link_timestamps(
                                created=timestamps.get("created"),
                                modified=timestamps.get("modified"),
                                accessed=timestamps.get("accessed")
                            )
                        
                        # Save dazzlelink
                        if dl_data.save_to_file(str(dl_path), make_executable=make_executable):
                            created_dazzlelinks.append(dl_path)
                            continue  # Skip the simplified implementation
                except Exception as e:
                    logger.warning(f"Error using dazzlelink library to create link, falling back to simplified implementation: {e}")
            
            # Fall back to simplified implementation
            dl_data = SimpleDazzleLinkData()
            dl_data.set_original_path(source_path)
            dl_data.set_target_path(destination_path)
            
            # Set timestamps if available
            if "timestamps" in file_info:
                timestamps = file_info["timestamps"]
                dl_data.set_link_timestamps(
                    created=timestamps.get("created"),
                    modified=timestamps.get("modified"),
                    accessed=timestamps.get("accessed")
                )
            
            # Save dazzlelink
            if dl_data.save_to_file(str(dl_path), make_executable=make_executable):
                created_dazzlelinks.append(dl_path)
            
        except Exception as e:
            logger.error(f"Error creating dazzlelink for {file_id}: {e}")
    
    return created_dazzlelinks