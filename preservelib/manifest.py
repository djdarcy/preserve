"""
Manifest management for preserve.py.

This module handles creation, updating, and reading of operation manifests,
which track file operations, metadata, and provide support for reversibility.
"""

import os
import sys
import json
import hashlib
import datetime
import platform
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple

# Set up module-level logger
logger = logging.getLogger(__name__)

class PreserveManifest:
    """
    Manifest for tracking file operations and metadata.
    
    The manifest stores information about:
    - Source and destination paths for each file
    - File metadata (timestamps, permissions, etc.)
    - Hash values for verification
    - Operation history for reproducibility
    """
    
    def __init__(self, manifest_path: Optional[Union[str, Path]] = None):
        """
        Initialize a new or existing manifest.
        
        Args:
            manifest_path: Path to an existing manifest file to load (optional)
        """
        # Default manifest structure
        self.manifest = {
            "manifest_version": 1,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "platform": self._get_platform_info(),
            "operations": [],
            "files": {},
            "metadata": {}
        }
        
        # Load existing manifest if provided
        if manifest_path:
            self.load(manifest_path)
    
    def _get_platform_info(self) -> Dict[str, str]:
        """
        Get information about the current platform.
        
        Returns:
            Dictionary with platform information
        """
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    
    def load(self, path: Union[str, Path]) -> bool:
        """
        Load a manifest from a file.
        
        Args:
            path: Path to the manifest file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(path)
            
            if not path.exists():
                logger.warning(f"Manifest file does not exist: {path}")
                return False
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate manifest version
            if "manifest_version" not in data or data["manifest_version"] != 1:
                logger.warning(f"Unsupported manifest version: {data.get('manifest_version')}")
                return False
            
            # Update manifest with loaded data
            self.manifest = data
            logger.debug(f"Loaded manifest from {path}")
            return True
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in manifest file: {path}")
            return False
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            return False
    
    def save(self, path: Union[str, Path]) -> bool:
        """
        Save the manifest to a file.
        
        Args:
            path: Path to save the manifest
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(path)
            
            # Create parent directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update updated_at timestamp
            self.manifest["updated_at"] = datetime.datetime.now().isoformat()
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2)
            
            logger.debug(f"Saved manifest to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving manifest: {e}")
            return False
    
    def add_operation(self, operation_type: str, source_path: Optional[str] = None, 
                     destination_path: Optional[str] = None, options: Optional[Dict[str, Any]] = None,
                     command_line: Optional[str] = None) -> int:
        """
        Add an operation to the manifest.
        
        Args:
            operation_type: Type of operation (COPY, MOVE, VERIFY, RESTORE)
            source_path: Source path for the operation (optional)
            destination_path: Destination path for the operation (optional)
            options: Additional operation options (optional)
            command_line: Original command line that triggered the operation (optional)
            
        Returns:
            The operation ID (index in the operations list)
        """
        operation = {
            "id": len(self.manifest["operations"]),
            "type": operation_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "options": options or {}
        }
        
        if source_path:
            operation["source_path"] = source_path
        
        if destination_path:
            operation["destination_path"] = destination_path
        
        if command_line:
            operation["command_line"] = command_line
        
        self.manifest["operations"].append(operation)
        return operation["id"]
    
    def add_file(self, source_path: str, destination_path: str, 
                file_info: Optional[Dict[str, Any]] = None, operation_id: Optional[int] = None,
                file_id: Optional[str] = None) -> str:
        """
        Add a file entry to the manifest.
        
        Args:
            source_path: Original path of the file
            destination_path: Destination path of the file
            file_info: Additional file metadata (optional)
            operation_id: ID of the operation that processed this file (optional)
            file_id: Custom file ID (optional, defaults to destination path)
            
        Returns:
            The file ID used to reference this file in the manifest
        """
        # Use destination path as default file ID
        if not file_id:
            file_id = destination_path
        
        # Create or update file entry
        if file_id not in self.manifest["files"]:
            self.manifest["files"][file_id] = {
                "source_path": source_path,
                "destination_path": destination_path,
                "added_at": datetime.datetime.now().isoformat(),
                "history": []
            }
        else:
            # Update existing entry with new paths
            self.manifest["files"][file_id]["source_path"] = source_path
            self.manifest["files"][file_id]["destination_path"] = destination_path
            self.manifest["files"][file_id]["updated_at"] = datetime.datetime.now().isoformat()
        
        # Add file info if provided
        if file_info:
            for key, value in file_info.items():
                self.manifest["files"][file_id][key] = value
        
        # Add to operation history if operation ID provided
        if operation_id is not None:
            history_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "operation_id": operation_id
            }
            self.manifest["files"][file_id]["history"].append(history_entry)
        
        return file_id
    
    def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a file.
        
        Args:
            file_id: The file ID to update
            metadata: The metadata to update
            
        Returns:
            True if successful, False if file not found
        """
        if file_id not in self.manifest["files"]:
            logger.warning(f"File not found in manifest: {file_id}")
            return False
        
        # Update metadata
        for key, value in metadata.items():
            self.manifest["files"][file_id][key] = value
        
        # Add updated timestamp
        self.manifest["files"][file_id]["updated_at"] = datetime.datetime.now().isoformat()
        
        return True
    
    def add_file_hash(self, file_id: str, algorithm: str, hash_value: str) -> bool:
        """
        Add a hash value for a file.
        
        Args:
            file_id: The file ID
            algorithm: Hash algorithm (MD5, SHA1, SHA256, SHA512)
            hash_value: The computed hash value
            
        Returns:
            True if successful, False if file not found
        """
        if file_id not in self.manifest["files"]:
            logger.warning(f"File not found in manifest: {file_id}")
            return False
        
        # Ensure hashes dictionary exists
        if "hashes" not in self.manifest["files"][file_id]:
            self.manifest["files"][file_id]["hashes"] = {}
        
        # Add or update hash value
        self.manifest["files"][file_id]["hashes"][algorithm] = hash_value
        
        return True
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            file_id: The file ID
            
        Returns:
            File information or None if not found
        """
        return self.manifest["files"].get(file_id)
    
    def get_file_by_destination(self, destination_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a file by its destination path.
        
        Args:
            destination_path: The destination path to look for
            
        Returns:
            File information or None if not found
        """
        for file_id, file_info in self.manifest["files"].items():
            if file_info.get("destination_path") == destination_path:
                return file_info
        return None
    
    def get_file_by_source(self, source_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a file by its source path.
        
        Args:
            source_path: The source path to look for
            
        Returns:
            File information or None if not found
        """
        for file_id, file_info in self.manifest["files"].items():
            if file_info.get("source_path") == source_path:
                return file_info
        return None
    
    def get_all_files(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all files in the manifest.
        
        Returns:
            Dictionary of file_id -> file_info
        """
        return self.manifest["files"]
    
    def get_operation(self, operation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get information about an operation.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Operation information or None if not found
        """
        if 0 <= operation_id < len(self.manifest["operations"]):
            return self.manifest["operations"][operation_id]
        return None
    
    def get_last_operation(self) -> Optional[Dict[str, Any]]:
        """
        Get the last operation in the manifest.
        
        Returns:
            Last operation or None if no operations
        """
        if self.manifest["operations"]:
            return self.manifest["operations"][-1]
        return None
    
    def get_all_operations(self) -> List[Dict[str, Any]]:
        """
        Get all operations in the manifest.
        
        Returns:
            List of operations
        """
        return self.manifest["operations"]
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value in the manifest.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.manifest["metadata"][key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value from the manifest.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.manifest["metadata"].get(key, default)
    
    def get_all_metadata(self) -> Dict[str, Any]:
        """
        Get all metadata from the manifest.
        
        Returns:
            Metadata dictionary
        """
        return self.manifest["metadata"]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get the manifest as a dictionary.
        
        Returns:
            The manifest dictionary
        """
        return self.manifest.copy()
    
    def get_files_for_operation(self, operation_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get all files processed by a specific operation.
        
        Args:
            operation_id: The operation ID
            
        Returns:
            Dictionary of file_id -> file_info for files in the operation
        """
        result = {}
        
        for file_id, file_info in self.manifest["files"].items():
            if "history" in file_info:
                for entry in file_info["history"]:
                    if entry.get("operation_id") == operation_id:
                        result[file_id] = file_info
                        break
        
        return result
    
    def get_files_by_state(self, state: str) -> Dict[str, Dict[str, Any]]:
        """
        Get files by their current state.
        
        Args:
            state: File state (e.g., "copied", "verified", "missing")
            
        Returns:
            Dictionary of file_id -> file_info for files in the specified state
        """
        result = {}
        
        for file_id, file_info in self.manifest["files"].items():
            if file_info.get("state") == state:
                result[file_id] = file_info
        
        return result
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the manifest structure.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["manifest_version", "created_at", "operations", "files"]
        for key in required_keys:
            if key not in self.manifest:
                errors.append(f"Missing required key: {key}")
        
        # Check manifest version
        if self.manifest.get("manifest_version") != 1:
            errors.append(f"Unsupported manifest version: {self.manifest.get('manifest_version')}")
        
        # Validate operations
        for i, operation in enumerate(self.manifest.get("operations", [])):
            if "type" not in operation:
                errors.append(f"Operation {i} is missing required 'type' field")
            if "timestamp" not in operation:
                errors.append(f"Operation {i} is missing required 'timestamp' field")
        
        # Validate files
        for file_id, file_info in self.manifest.get("files", {}).items():
            if "source_path" not in file_info:
                errors.append(f"File {file_id} is missing required 'source_path' field")
            if "destination_path" not in file_info:
                errors.append(f"File {file_id} is missing required 'destination_path' field")
        
        return len(errors) == 0, errors


def calculate_file_hash(file_path: Union[str, Path], algorithms: List[str] = None) -> Dict[str, str]:
    """
    Calculate hash values for a file using multiple algorithms.
    
    Args:
        file_path: Path to the file
        algorithms: List of hash algorithms to use (default: ["SHA256"])
        
    Returns:
        Dictionary mapping algorithm names to hash values
    """
    if algorithms is None:
        algorithms = ["SHA256"]
    
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        logger.warning(f"Cannot calculate hash for non-existent file: {path}")
        return {}
    
    result = {}
    hash_objects = {}
    
    # Initialize hash objects
    for algorithm in algorithms:
        alg = algorithm.lower()
        if alg == "md5":
            hash_objects[algorithm] = hashlib.md5()
        elif alg == "sha1":
            hash_objects[algorithm] = hashlib.sha1()
        elif alg == "sha256":
            hash_objects[algorithm] = hashlib.sha256()
        elif alg == "sha512":
            hash_objects[algorithm] = hashlib.sha512()
        else:
            logger.warning(f"Unsupported hash algorithm: {algorithm}")
            continue
    
    try:
        # Read file in chunks and update all hash objects
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                for hash_obj in hash_objects.values():
                    hash_obj.update(chunk)
        
        # Get hash values
        for algorithm, hash_obj in hash_objects.items():
            result[algorithm] = hash_obj.hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating hash for {path}: {e}")
    
    return result


def verify_file_hash(file_path: Union[str, Path], expected_hashes: Dict[str, str]) -> Tuple[bool, Dict[str, Tuple[bool, str, str]]]:
    """
    Verify a file against expected hash values.
    
    Args:
        file_path: Path to the file
        expected_hashes: Dictionary mapping algorithm names to expected hash values
        
    Returns:
        Tuple of (overall_success, details) where details is a dictionary mapping
        algorithm names to tuples of (success, expected_hash, actual_hash)
    """
    if not expected_hashes:
        logger.warning(f"No expected hashes provided for {file_path}")
        return False, {}
    
    # Calculate actual hashes
    actual_hashes = calculate_file_hash(file_path, list(expected_hashes.keys()))
    
    if not actual_hashes:
        logger.warning(f"Failed to calculate hashes for {file_path}")
        return False, {}
    
    # Compare hashes
    results = {}
    all_match = True
    
    for algorithm, expected in expected_hashes.items():
        if algorithm not in actual_hashes:
            results[algorithm] = (False, expected, None)
            all_match = False
        else:
            actual = actual_hashes[algorithm]
            match = expected.lower() == actual.lower()
            results[algorithm] = (match, expected, actual)
            if not match:
                all_match = False
    
    return all_match, results


def create_manifest_for_path(path: Union[str, Path], dest_dir: Union[str, Path], 
                           recursive: bool = True, operation_type: str = "COPY",
                           command_line: Optional[str] = None,
                           options: Optional[Dict[str, Any]] = None) -> PreserveManifest:
    """
    Create a manifest for files in a directory.
    
    Args:
        path: Source path (file or directory)
        dest_dir: Destination directory
        recursive: Whether to recurse into subdirectories
        operation_type: Type of operation (COPY, MOVE, etc.)
        command_line: Original command line (optional)
        options: Additional options (optional)
        
    Returns:
        Manifest object with file entries
    """
    manifest = PreserveManifest()
    
    # Add operation
    op_id = manifest.add_operation(
        operation_type=operation_type,
        source_path=str(path),
        destination_path=str(dest_dir),
        options=options,
        command_line=command_line
    )
    
    # Process files
    source_path = Path(path)
    dest_path = Path(dest_dir)
    
    if source_path.is_file():
        # Single file
        dest_file = dest_path / source_path.name
        file_id = manifest.add_file(
            source_path=str(source_path),
            destination_path=str(dest_file),
            operation_id=op_id
        )
    elif source_path.is_dir():
        # Directory
        _process_directory_for_manifest(
            manifest=manifest,
            source_dir=source_path,
            dest_dir=dest_path,
            recursive=recursive,
            operation_id=op_id
        )
    else:
        logger.warning(f"Source path does not exist: {source_path}")
    
    return manifest


def _process_directory_for_manifest(manifest: PreserveManifest, source_dir: Path, dest_dir: Path,
                                  recursive: bool, operation_id: int) -> None:
    """
    Process a directory for manifest creation.
    
    Args:
        manifest: Manifest to update
        source_dir: Source directory
        dest_dir: Destination directory
        recursive: Whether to recurse into subdirectories
        operation_id: Operation ID to associate with files
    """
    # Process files in directory
    for item in source_dir.iterdir():
        if item.is_file():
            # Add file to manifest
            dest_file = dest_dir / item.relative_to(source_dir)
            manifest.add_file(
                source_path=str(item),
                destination_path=str(dest_file),
                operation_id=operation_id
            )
        elif item.is_dir() and recursive:
            # Create destination subdirectory
            dest_subdir = dest_dir / item.relative_to(source_dir)
            
            # Recurse into subdirectory
            _process_directory_for_manifest(
                manifest=manifest,
                source_dir=item,
                dest_dir=dest_subdir,
                recursive=recursive,
                operation_id=operation_id
            )


def read_manifest(path: Union[str, Path]) -> Optional[PreserveManifest]:
    """
    Read a manifest from a file.
    
    Args:
        path: Path to the manifest file
        
    Returns:
        Manifest object, or None if the file does not exist or is invalid
    """
    try:
        manifest = PreserveManifest(path)
        valid, errors = manifest.validate()
        
        if not valid:
            logger.warning(f"Invalid manifest: {path}")
            for error in errors:
                logger.warning(f"  {error}")
            return None
        
        return manifest
    except Exception as e:
        logger.error(f"Error reading manifest: {e}")
        return None
