"""
Path utilities for preserve.py.

This module provides utilities for path analysis, pattern detection,
and optimal common directory finding.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Set, Tuple
import logging

# Set up module-level logger
logger = logging.getLogger(__name__)

class PathNode:
    """
    Node in a path tree structure.
    
    Each node represents a path component, with children representing
    subpaths. The tree structure allows analyzing path relationships
    and finding common directories.
    """
    
    def __init__(self, name: str):
        """
        Initialize a new path node.
        
        Args:
            name: Name of this path component
        """
        self.name = name
        self.children: Dict[str, PathNode] = {}
        self.count = 0
        self.paths: List[str] = []
        self.depth = 0  # Depth in the tree
        
    def add_child(self, name: str) -> 'PathNode':
        """
        Add a child node if it doesn't exist.
        
        Args:
            name: Name of the child node
            
        Returns:
            The new or existing child node
        """
        if name not in self.children:
            child = PathNode(name)
            child.depth = self.depth + 1
            self.children[name] = child
        return self.children[name]
    
    def get_child(self, name: str) -> Optional['PathNode']:
        """
        Get a child node by name.
        
        Args:
            name: Name of the child node
            
        Returns:
            The child node, or None if not found
        """
        return self.children.get(name)
    
    def get_children_count(self) -> int:
        """
        Get the number of child nodes.
        
        Returns:
            Number of children
        """
        return len(self.children)
    
    def __repr__(self) -> str:
        """String representation of the node."""
        return f"PathNode({self.name}:{self.count})"


class PathTree:
    """
    Tree structure for analyzing path relationships.
    
    Builds a tree from a list of paths, where each node represents
    a path component. The tree can be analyzed to find common
    directories and optimal split points.
    """
    
    def __init__(self):
        """Initialize a new path tree with an empty root node."""
        self.root = PathNode("")
        self.paths_count = 0
    
    def add_path(self, path: Union[str, Path]) -> None:
        """
        Add a path to the tree.
        
        Args:
            path: Path to add
        """
        # Normalize the path
        path_str = self._normalize_path(str(path))
        
        # Split into components
        parts = self._split_path(path_str)
        
        # Traverse/build the tree
        current = self.root
        for part in parts:
            current = current.add_child(part)
            current.count += 1
        
        # Record the full path at the leaf
        current.paths.append(path_str)
        self.paths_count += 1
    
    def add_paths(self, paths: List[Union[str, Path]]) -> None:
        """
        Add multiple paths to the tree.
        
        Args:
            paths: List of paths to add
        """
        for path in paths:
            self.add_path(path)
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path for consistent handling.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized path string
        """
        # Convert backslashes to forward slashes
        norm_path = path.replace('\\', '/')
        
        # Remove trailing slash if present
        if norm_path.endswith('/'):
            norm_path = norm_path[:-1]
            
        return norm_path
    
    def _split_path(self, path: str) -> List[str]:
        """
        Split a path into components.
        
        Args:
            path: Path to split
            
        Returns:
            List of path components
        """
        # Split by slashes
        parts = path.split('/')
        
        # Filter out empty parts
        return [p for p in parts if p]
    
    def _reconstruct_path(self, parts: List[str], separator: str = '/') -> str:
        """
        Reconstruct a path from components.
        
        Args:
            parts: List of path components
            separator: Path separator to use
            
        Returns:
            Reconstructed path string
        """
        path = separator.join(parts)
        
        # Add drive separator for Windows paths
        if sys.platform == 'win32' and len(parts) > 0 and parts[0].endswith(':'):
            path = parts[0] + separator + separator.join(parts[1:])
            
        return path
    
    def find_common_base_directory(self, threshold: float = 0.75) -> Tuple[Optional[str], float]:
        """
        Find the common base directory in the tree.
        
        The common base directory is the deepest directory that contains
        at least threshold*100% of all paths in the tree.
        
        Args:
            threshold: Minimum fraction of paths that must share the directory
            
        Returns:
            Tuple of (common base directory, fraction of paths covered)
        """
        if self.paths_count == 0:
            return None, 0.0
            
        # If there's only one path, return its parent directory
        if self.paths_count == 1:
            path = next(self._get_all_paths())
            parent = os.path.dirname(path)
            return parent, 1.0
            
        # Start at the root and traverse down
        current = self.root
        path_parts = []
        
        min_count = self.paths_count * threshold
        
        while True:
            # Check if this node has enough paths
            if current.count < min_count:
                break
                
            # Check if there's a single child with enough paths
            max_child = None
            max_count = 0
            
            for name, child in current.children.items():
                if child.count > max_count:
                    max_count = child.count
                    max_child = child
            
            # If there's a clear winner, continue down that path
            if max_child and max_child.count >= min_count:
                path_parts.append(max_child.name)
                current = max_child
            else:
                # No clear path down, stop here
                break
        
        # Convert path parts back to a path
        if not path_parts:
            # No common base found
            return None, 0.0
        
        # Calculate fraction of paths covered
        fraction = current.count / self.paths_count
        
        # Build the path string
        common_base = self._reconstruct_path(path_parts)
        
        # Convert to OS-specific separators
        if sys.platform == 'win32':
            common_base = common_base.replace('/', '\\')
            
        return common_base, fraction
    
    def find_optimal_split_points(self, min_threshold: float = 0.3, depth_weight: float = 0.1) -> List[Tuple[str, float, int]]:
        """
        Find optimal split points in the tree.
        
        Split points are directories where paths naturally cluster,
        with a score based on the fraction of paths and depth.
        
        Args:
            min_threshold: Minimum fraction of paths for a split point
            depth_weight: Weight to give to depth in scoring
            
        Returns:
            List of (path, score, count) tuples, sorted by score
        """
        if self.paths_count == 0:
            return []
            
        split_points = []
        min_count = self.paths_count * min_threshold
        
        # Recursive helper to find split points
        def find_splits(node, current_path):
            # Skip leaf nodes and nodes with too few paths
            if not node.children or node.count < min_count:
                return
                
            # Calculate score based on path coverage and depth
            score = (node.count / self.paths_count) + (node.depth * depth_weight)
            
            # Add this node as a potential split point
            if node.depth > 0:  # Skip root
                path_str = self._reconstruct_path(current_path)
                if sys.platform == 'win32':
                    path_str = path_str.replace('/', '\\')
                split_points.append((path_str, score, node.count))
            
            # Continue recursion to children
            for name, child in node.children.items():
                find_splits(child, current_path + [name])
        
        # Start recursion at root with empty path
        find_splits(self.root, [])
        
        # Sort by score descending
        return sorted(split_points, key=lambda x: x[1], reverse=True)
    
    def _get_all_paths(self):
        """Generator that yields all paths in the tree."""
        # Recursive helper to find all leaf nodes
        def collect_paths(node):
            if node.paths:
                for path in node.paths:
                    yield path
            
            for child in node.children.values():
                yield from collect_paths(child)
        
        yield from collect_paths(self.root)


def find_common_base_directory(paths: List[Union[str, Path]], threshold: float = 0.75) -> Optional[Path]:
    """
    Find the common base directory for a list of paths.
    
    Args:
        paths: List of paths to analyze
        threshold: Minimum fraction of paths that must share the directory
        
    Returns:
        Common base directory as a Path object, or None if not found
    """
    # Build path tree
    tree = PathTree()
    tree.add_paths(paths)
    
    # Find common base
    common_base, fraction = tree.find_common_base_directory(threshold)
    
    if common_base:
        logger.debug(f"Found common base directory: {common_base} (covers {fraction:.1%} of paths)")
        return Path(common_base)
    
    return None


def detect_path_patterns(path_str: str, all_paths: Optional[List[str]] = None) -> Optional[Tuple[str, Path, Path]]:
    """
    Detect patterns in a path string.
    
    If all_paths is provided, builds a path tree to find common base directories.
    
    Args:
        path_str: Path string to analyze
        all_paths: All paths to consider for pattern detection
        
    Returns:
        Tuple of (pattern_type, base_path, rel_path) if a pattern is found,
        or None if no pattern is detected
    """
    # Build path tree if all_paths is provided
    if all_paths:
        tree = PathTree()
        tree.add_paths(all_paths)
        
        # Find common base
        common_base, fraction = tree.find_common_base_directory()
        
        if common_base:
            try:
                # Calculate relative path
                path_obj = Path(path_str)
                base_obj = Path(common_base)
                
                # Handle drive letters on Windows
                if sys.platform == 'win32':
                    path_norm = str(path_obj).replace('\\', '/')
                    base_norm = str(base_obj).replace('\\', '/')
                    
                    # Check if path starts with base
                    if path_norm.startswith(base_norm):
                        rel_part = path_norm[len(base_norm):].lstrip('/')
                        rel_path = Path(rel_part)
                        return ('common_base', base_obj, rel_path)
                else:
                    # Use relative_to for non-Windows paths
                    try:
                        rel_path = path_obj.relative_to(base_obj)
                        return ('common_base', base_obj, rel_path)
                    except ValueError:
                        pass
            except Exception as e:
                logger.debug(f"Error calculating relative path: {e}")
    
    # No pattern detected
    return None