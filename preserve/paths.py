"""
Path handling and normalization for preserve.py.

This module handles path collection, normalization, and transformation
between source and destination paths.
"""

import os
import sys
import re
import glob
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Pattern, Any

# Set up module-level logger
logger = logging.getLogger(__name__)

class PathRegistry:
    """
    Registry for tracking source and destination paths.
    
    The PathRegistry maintains bidirectional mappings between source and destination
    paths, supports path normalization, and performs path transformations according
    to configurable rules.
    """
    
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        """
        Initialize a new path registry.
        
        Args:
            base_dir: Optional base directory for relative paths
        """
        self.base_dir = Path(base_dir).resolve() if base_dir else Path.cwd().resolve()
        self.source_to_dest = {}  # source_path -> dest_path
        self.dest_to_source = {}  # dest_path -> source_path
    
    def add_mapping(self, source_path: Union[str, Path], dest_path: Union[str, Path]) -> None:
        """
        Add a mapping between source and destination paths.
        
        Args:
            source_path: Source path
            dest_path: Destination path
        """
        source_str = str(source_path)
        dest_str = str(dest_path)
        
        self.source_to_dest[source_str] = dest_str
        self.dest_to_source[dest_str] = source_str
    
    def get_dest_for_source(self, source_path: Union[str, Path]) -> Optional[str]:
        """
        Get the destination path for a source path.
        
        Args:
            source_path: Source path
            
        Returns:
            Destination path or None if not found
        """
        return self.source_to_dest.get(str(source_path))
    
    def get_source_for_dest(self, dest_path: Union[str, Path]) -> Optional[str]:
        """
        Get the source path for a destination path.
        
        Args:
            dest_path: Destination path
            
        Returns:
            Source path or None if not found
        """
        return self.dest_to_source.get(str(dest_path))
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get all source to destination mappings.
        
        Returns:
            Dictionary of source_path -> dest_path
        """
        return self.source_to_dest.copy()
    
    def clear(self) -> None:
        """Clear all mappings."""
        self.source_to_dest.clear()
        self.dest_to_source.clear()
    
    def remove_mapping(self, source_path: Union[str, Path]) -> bool:
        """
        Remove a mapping by source path.
        
        Args:
            source_path: Source path
            
        Returns:
            True if the mapping was removed, False if not found
        """
        source_str = str(source_path)
        if source_str in self.source_to_dest:
            dest_str = self.source_to_dest[source_str]
            del self.source_to_dest[source_str]
            if dest_str in self.dest_to_source:
                del self.dest_to_source[dest_str]
            return True
        return False


class PathTransformer:
    """
    Transformer for converting source paths to destination paths.
    
    The PathTransformer applies normalization rules to convert source paths
    to destination paths according to configurable styles.
    """
    
    def __init__(self, registry: PathRegistry = None):
        """
        Initialize a new path transformer.
        
        Args:
            registry: Optional path registry to update
        """
        self.registry = registry or PathRegistry()
    
    def transform_path(self, source_path: Union[str, Path], dest_base: Union[str, Path],
                     style: str = "relative", include_base: bool = False,
                     source_base: Optional[Union[str, Path]] = None) -> Path:
        """
        Transform a source path to a destination path.
        
        Args:
            source_path: Source path
            dest_base: Base destination directory
            style: Path style ("relative", "absolute", "flat")
            include_base: Whether to include the base path in the destination
            source_base: Optional base directory for relative paths
            
        Returns:
            Transformed destination path
        """
        source_path = Path(source_path).resolve()
        dest_base = Path(dest_base).resolve()
        
        if source_base:
            source_base = Path(source_base).resolve()
        else:
            source_base = self.registry.base_dir
        
        # Apply transformation based on style
        if style == "flat":
            # Flat style: just use the filename in the destination directory
            dest_path = dest_base / source_path.name
        
        elif style == "absolute":
            # Absolute style: preserve the entire path with drive letter as directory
            if sys.platform == 'win32':
                # Windows: use drive letter as directory
                drive, path = os.path.splitdrive(str(source_path))
                drive = drive.rstrip(':')  # Remove colon from drive letter
                dest_path = dest_base / drive / path.lstrip('\\/')
            else:
                # Unix: use root-relative path
                dest_path = dest_base / str(source_path).lstrip('/')
        
        elif style == "relative":
            # Relative style: preserve path relative to source_base
            if include_base and source_base:
                # Include the base directory name
                base_name = source_base.name
                rel_path = source_path.relative_to(source_base.parent)
                dest_path = dest_base / rel_path
            else:
                # Just the path relative to source_base
                try:
                    rel_path = source_path.relative_to(source_base)
                    dest_path = dest_base / rel_path
                except ValueError:
                    # Path is not relative to source_base, use absolute style as fallback
                    logger.warning(f"Path {source_path} is not relative to {source_base}, using absolute style")
                    return self.transform_path(source_path, dest_base, "absolute", include_base)
        
        else:
            # Unknown style, use relative as default
            logger.warning(f"Unknown path style: {style}, using relative")
            return self.transform_path(source_path, dest_base, "relative", include_base, source_base)
        
        # Update registry with the mapping
        self.registry.add_mapping(str(source_path), str(dest_path))
        
        return dest_path
    
    def transform_paths(self, source_paths: List[Union[str, Path]], dest_base: Union[str, Path],
                       style: str = "relative", include_base: bool = False,
                       source_base: Optional[Union[str, Path]] = None) -> Dict[str, Path]:
        """
        Transform multiple source paths to destination paths.
        
        Args:
            source_paths: List of source paths
            dest_base: Base destination directory
            style: Path style ("relative", "absolute", "flat")
            include_base: Whether to include the base path in the destination
            source_base: Optional base directory for relative paths
            
        Returns:
            Dictionary mapping source paths to destination paths
        """
        result = {}
        
        for source_path in source_paths:
            dest_path = self.transform_path(
                source_path, dest_base, style, include_base, source_base
            )
            result[str(source_path)] = dest_path
        
        return result
    
    def restore_path(self, dest_path: Union[str, Path]) -> Optional[str]:
        """
        Restore the original source path from a destination path.
        
        Args:
            dest_path: Destination path
            
        Returns:
            Original source path or None if not found
        """
        return self.registry.get_source_for_dest(dest_path)
    
    def get_registry(self) -> PathRegistry:
        """
        Get the path registry.
        
        Returns:
            The path registry
        """
        return self.registry


def find_files(
    patterns: List[str],
    root_dirs: List[Union[str, Path]] = None,
    recursive: bool = True,
    include_dirs: bool = False,
    follow_symlinks: bool = False,
    exclude_patterns: List[str] = None
) -> List[Path]:
    """
    Find files matching patterns in directories.
    
    Args:
        patterns: List of glob patterns to match
        root_dirs: List of directories to search (default: current directory)
        recursive: Whether to recurse into subdirectories
        include_dirs: Whether to include directories in results
        follow_symlinks: Whether to follow symbolic links
        exclude_patterns: List of glob patterns to exclude
        
    Returns:
        List of matching paths
    """
    found_paths = set()
    exclude_paths = set()
    
    # Default to current directory if not specified
    if not root_dirs:
        root_dirs = [os.getcwd()]
    
    # Process exclude patterns first
    if exclude_patterns:
        for root_dir in root_dirs:
            for pattern in exclude_patterns:
                if recursive:
                    # Use ** for recursive glob
                    if '**' not in pattern:
                        pattern = os.path.join('**', pattern)
                    for path in Path(root_dir).glob(pattern):
                        exclude_paths.add(str(path.resolve()))
                else:
                    # Non-recursive glob
                    for path in Path(root_dir).glob(pattern):
                        exclude_paths.add(str(path.resolve()))
    
    # Process include patterns
    for root_dir in root_dirs:
        root_path = Path(root_dir)
        
        for pattern in patterns:
            if recursive:
                # Use ** for recursive glob
                if '**' not in pattern:
                    pattern = os.path.join('**', pattern)
                for path in root_path.glob(pattern):
                    # Check if it's a directory or file
                    if path.is_file() or (include_dirs and path.is_dir()):
                        # Check if it matches exclude patterns
                        if str(path.resolve()) not in exclude_paths:
                            found_paths.add(path.resolve())
            else:
                # Non-recursive glob
                for path in root_path.glob(pattern):
                    # Check if it's a directory or file
                    if path.is_file() or (include_dirs and path.is_dir()):
                        # Check if it matches exclude patterns
                        if str(path.resolve()) not in exclude_paths:
                            found_paths.add(path.resolve())
    
    return sorted(list(found_paths))


def find_files_by_regex(
    patterns: List[Union[str, Pattern]],
    root_dirs: List[Union[str, Path]] = None,
    recursive: bool = True,
    include_dirs: bool = False,
    follow_symlinks: bool = False,
    exclude_patterns: List[Union[str, Pattern]] = None
) -> List[Path]:
    """
    Find files matching regex patterns in directories.
    
    Args:
        patterns: List of regex patterns to match
        root_dirs: List of directories to search (default: current directory)
        recursive: Whether to recurse into subdirectories
        include_dirs: Whether to include directories in results
        follow_symlinks: Whether to follow symbolic links
        exclude_patterns: List of regex patterns to exclude
        
    Returns:
        List of matching paths
    """
    found_paths = set()
    
    # Default to current directory if not specified
    if not root_dirs:
        root_dirs = [os.getcwd()]
    
    # Compile regex patterns
    compiled_patterns = []
    for pattern in patterns:
        if isinstance(pattern, str):
            compiled_patterns.append(re.compile(pattern))
        else:
            compiled_patterns.append(pattern)
    
    # Compile exclude patterns
    compiled_excludes = []
    if exclude_patterns:
        for pattern in exclude_patterns:
            if isinstance(pattern, str):
                compiled_excludes.append(re.compile(pattern))
            else:
                compiled_excludes.append(pattern)
    
    # Walk directories
    for root_dir in root_dirs:
        for root, dirs, files in os.walk(str(root_dir), followlinks=follow_symlinks):
            # Process files
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if it matches exclude patterns
                excluded = False
                for pattern in compiled_excludes:
                    if pattern.search(file_path):
                        excluded = True
                        break
                
                if not excluded:
                    # Check if it matches include patterns
                    for pattern in compiled_patterns:
                        if pattern.search(file_path):
                            found_paths.add(Path(file_path).resolve())
                            break
            
            # Process directories if include_dirs is True
            if include_dirs:
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    
                    # Check if it matches exclude patterns
                    excluded = False
                    for pattern in compiled_excludes:
                        if pattern.search(dir_path):
                            excluded = True
                            break
                    
                    if not excluded:
                        # Check if it matches include patterns
                        for pattern in compiled_patterns:
                            if pattern.search(dir_path):
                                found_paths.add(Path(dir_path).resolve())
                                break
            
            # Stop recursion if not recursive
            if not recursive:
                break
    
    return sorted(list(found_paths))


def load_file_list(file_path: Union[str, Path]) -> List[str]:
    """
    Load a list of files from a text file.
    
    Args:
        file_path: Path to the file containing the list
        
    Returns:
        List of file paths
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        logger.error(f"Error loading file list from {file_path}: {e}")
        return []


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a path to its canonical form.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized path
    """
    return Path(path).resolve()


def is_subpath(path: Union[str, Path], parent: Union[str, Path]) -> bool:
    """
    Check if a path is a subpath of another path.
    
    Args:
        path: Path to check
        parent: Potential parent path
        
    Returns:
        True if path is a subpath of parent, False otherwise
    """
    path = Path(path).resolve()
    parent = Path(parent).resolve()
    
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def get_common_ancestor(paths: List[Union[str, Path]]) -> Optional[Path]:
    """
    Find the common ancestor of multiple paths.
    
    Args:
        paths: List of paths
        
    Returns:
        Common ancestor path, or None if no common ancestor
    """
    if not paths:
        return None
    
    # Resolve all paths
    resolved_paths = [Path(p).resolve() for p in paths]
    
    # Handle case of single path
    if len(resolved_paths) == 1:
        return resolved_paths[0].parent
    
    # Convert paths to strings for common prefix
    path_strings = [str(p) for p in resolved_paths]
    
    # Find the common prefix
    prefix = os.path.commonpath(path_strings)
    
    # If no common prefix, return None
    if not prefix:
        return None
    
    # Return the common ancestor as a Path
    return Path(prefix)


def split_path_at_base(path: Union[str, Path], base: Union[str, Path]) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Split a path into base and relative parts.
    
    Args:
        path: Path to split
        base: Base path
        
    Returns:
        Tuple of (base_part, relative_part) or (None, None) if path is not relative to base
    """
    path = Path(path).resolve()
    base = Path(base).resolve()
    
    try:
        rel_path = path.relative_to(base)
        return base, rel_path
    except ValueError:
        return None, None


def strip_drive_letter(path: Union[str, Path]) -> str:
    """
    Strip the drive letter from a Windows path.
    
    Args:
        path: Path to strip
        
    Returns:
        Path string without drive letter
    """
    if sys.platform == 'win32':
        drive, path = os.path.splitdrive(str(path))
        return path.lstrip('\\/')
    else:
        return str(path).lstrip('/')


def get_drive_letter(path: Union[str, Path]) -> Optional[str]:
    """
    Get the drive letter from a Windows path.
    
    Args:
        path: Path to get drive letter from
        
    Returns:
        Drive letter or None if not a Windows path
    """
    if sys.platform == 'win32':
        drive, _ = os.path.splitdrive(str(path))
        return drive.rstrip(':') if drive else None
    else:
        return None


def is_unc_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is a UNC path.
    
    Args:
        path: Path to check
        
    Returns:
        True if the path is a UNC path, False otherwise
    """
    path_str = str(path)
    return path_str.startswith('\\\\') or path_str.startswith('//')
