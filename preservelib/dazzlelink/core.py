"""
Core functionality for dazzlelink integration.

This module provides the core functions for integrating with the dazzlelink library,
implementing creation, discovery, and restoration of dazzlelinks.
"""

import os
import sys
import logging
import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Tuple, Any

# Set up module-level logger
logger = logging.getLogger(__name__)

# Flag to track if dazzlelink is available
HAVE_DAZZLELINK = False

# Try to import dazzlelink
try:
    import dazzlelink
    from dazzlelink import (
        DazzleLinkData, DazzleLinkConfig, DazzleLink,
        recreate_link, find_dazzlelinks, 
        collect_timestamp_info, apply_timestamp_strategy
    )
    HAVE_DAZZLELINK = True
except ImportError:
    logger.debug("Dazzlelink module not available, functionality will be limited")


def create_dazzlelink(
    source_path: Union[str, Path],
    dest_path: Union[str, Path],
    dazzlelink_dir: Optional[Union[str, Path]] = None
) -> Optional[Path]:
    """
    Create a dazzlelink from a source file to a destination file.
    
    Args:
        source_path: Original source path
        dest_path: Destination file path
        dazzlelink_dir: Directory for dazzlelinks (optional)
        
    Returns:
        Path to the created dazzlelink, or None if creation failed
    """
    if not HAVE_DAZZLELINK:
        logger.warning("Dazzlelink module not available, cannot create dazzlelink")
        return None
    
    try:
        # Determine link path
        link_path = None
        if dazzlelink_dir:
            # Create relative path in dazzlelink_dir
            dazzle_dir = Path(dazzlelink_dir)
            dazzle_dir.mkdir(parents=True, exist_ok=True)
            link_path = dazzle_dir / Path(dest_path).name
        else:
            # Create link alongside destination
            link_path = Path(str(dest_path) + '.dazzlelink')
        
        # Create the dazzlelink
        config = DazzleLinkConfig()
        dl = DazzleLink(config)
        
        # Use require_symlink=False to directly create a dazzlelink from a file
        dazzlelink_path = dl.serialize_link(
            link_path=str(source_path),
            output_path=str(link_path),
            require_symlink=False
        )
        
        logger.debug(f"Created dazzlelink: {link_path} -> {source_path}")
        return Path(dazzlelink_path)
        
    except Exception as e:
        logger.error(f"Error creating dazzlelink: {e}")
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
    if not HAVE_DAZZLELINK:
        logger.warning("Dazzlelink module not available, cannot find dazzlelinks")
        return []
    
    try:
        return find_dazzlelinks(
            [str(directory)], 
            recursive=recursive, 
            pattern=pattern
        )
    except Exception as e:
        logger.error(f"Error finding dazzlelinks: {e}")
        return []


def restore_from_dazzlelink(
    dazzlelink_path: Union[str, Path],
    target_location: Optional[Union[str, Path]] = None,
    timestamp_strategy: str = 'current',
    update_dazzlelink: bool = False,
    use_live_target: bool = False
) -> Optional[Path]:
    """
    Restore a file from a dazzlelink.
    
    Args:
        dazzlelink_path: Path to the dazzlelink file
        target_location: Override location for the recreated file
        timestamp_strategy: Strategy for setting timestamps
        update_dazzlelink: Whether to update dazzlelink metadata
        use_live_target: Whether to check live target for timestamps
        
    Returns:
        Path to the restored file, or None if restoration failed
    """
    if not HAVE_DAZZLELINK:
        logger.warning("Dazzlelink module not available, cannot restore from dazzlelink")
        return None
    
    try:
        return Path(recreate_link(
            dazzlelink_path=str(dazzlelink_path),
            target_location=str(target_location) if target_location else None,
            timestamp_strategy=timestamp_strategy,
            update_dazzlelink=update_dazzlelink,
            use_live_target=use_live_target
        ))
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
    if not HAVE_DAZZLELINK:
        logger.warning("Dazzlelink module not available, cannot convert dazzlelinks to manifest")
        return {
            "files": {},
            "operations": [],
            "metadata": {}
        }
    
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
            dl_data = DazzleLinkData.from_file(str(dl_path))
            
            # Get paths
            original_path = dl_data.get_original_path()
            target_path = dl_data.get_target_path()
            
            if not original_path or not target_path:
                logger.warning(f"Missing path information in dazzlelink: {dl_path}")
                continue
            
            # Generate a unique file ID
            file_id = f"dazzlelink_{i}_{Path(original_path).name}"
            
            # Create file entry
            file_info = {
                "source_path": original_path,
                "destination_path": target_path,
                "added_at": dl_data.get_creation_date(),
                "history": [{
                    "timestamp": dl_data.get_creation_date(),
                    "operation_id": 0
                }]
            }
            
            # Add timestamps
            link_timestamps = dl_data.get_link_timestamps()
            if link_timestamps:
                file_info["timestamps"] = link_timestamps
            
            # Add target timestamps
            target_timestamps = dl_data.get_target_timestamps()
            if target_timestamps:
                file_info["target_timestamps"] = target_timestamps
            
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
    if not HAVE_DAZZLELINK:
        logger.warning("Dazzlelink module not available, cannot convert manifest to dazzlelinks")
        return []
    
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
            
            # Create dazzlelink data
            dl_data = DazzleLinkData()
            
            # Set paths
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
            
            if "target_timestamps" in file_info:
                timestamps = file_info["target_timestamps"]
                dl_data.set_target_timestamps(
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
