"""
File verification utilities for hashing and comparing files.

This module provides functions for calculating file hashes using various algorithms
and verifying file integrity through hash comparison.
"""

import os
import sys
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any, Set, Callable

# Set up module-level logger
logger = logging.getLogger(__name__)


def calculate_file_hash(
    file_path: Union[str, Path],
    algorithms: List[str] = None,
    buffer_size: int = 65536,
    preserve_case: bool = True
) -> Dict[str, str]:
    """
    Calculate hash values for a file using one or more algorithms.

    This is the core implementation used by both filetoolkit and preservelib.

    Args:
        file_path: Path to the file
        algorithms: List of hash algorithms to use (default: ['SHA256'])
        buffer_size: Size of the buffer for reading the file in chunks
        preserve_case: If True, preserve the case of algorithm names in output

    Returns:
        Dictionary mapping algorithm names to hash values
    """
    if algorithms is None:
        algorithms = ['SHA256']

    path_obj = Path(file_path)
    if not path_obj.exists() or not path_obj.is_file():
        logger.warning(f"Cannot calculate hash for non-existent file: {path_obj}")
        return {}

    result = {}
    hash_objects = {}

    # Initialize hash objects - store with original case for preserve_case option
    for algorithm in algorithms:
        alg_normalized = algorithm.upper()
        if alg_normalized == 'MD5':
            hash_objects[algorithm] = hashlib.md5()
        elif alg_normalized == 'SHA1':
            hash_objects[algorithm] = hashlib.sha1()
        elif alg_normalized == 'SHA256':
            hash_objects[algorithm] = hashlib.sha256()
        elif alg_normalized == 'SHA512':
            hash_objects[algorithm] = hashlib.sha512()
        else:
            logger.warning(f"Unsupported hash algorithm: {algorithm}")
            continue

    if not hash_objects:
        return {}

    try:
        # Read file in chunks and update all hash objects
        with open(path_obj, 'rb') as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                for hash_obj in hash_objects.values():
                    hash_obj.update(data)

        # Get hash values - use original algorithm name casing if preserve_case
        for algorithm, hash_obj in hash_objects.items():
            key = algorithm if preserve_case else algorithm.upper()
            result[key] = hash_obj.hexdigest()

        logger.debug(f"Successfully calculated hashes for {path_obj}")

    except Exception as e:
        logger.error(f"Error calculating hash for {path_obj}: {e}")

    return result


def verify_file_hash(
    file_path: Union[str, Path], 
    expected_hashes: Dict[str, str]
) -> Tuple[bool, Dict[str, Tuple[bool, str, str]]]:
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


def verify_files_with_manifest(
    files: Dict[str, str], 
    algorithm: str = 'SHA256'
) -> Dict[str, Tuple[bool, Optional[str], Optional[str]]]:
    """
    Verify a set of files against provided hashes.
    
    Args:
        files: Dictionary mapping file paths to expected hashes
        algorithm: Hash algorithm to use
            
    Returns:
        Dictionary mapping file paths to tuples of (success, expected_hash, actual_hash)
    """
    results = {}
    
    for file_path, expected_hash in files.items():
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            results[file_path] = (False, expected_hash, None)
            logger.warning(f"File does not exist: {file_path}")
            continue
        
        if not path_obj.is_file():
            results[file_path] = (False, expected_hash, None)
            logger.warning(f"Path is not a file: {file_path}")
            continue
        
        # Calculate hash
        actual_hashes = calculate_file_hash(path_obj, [algorithm])
        
        if algorithm not in actual_hashes:
            results[file_path] = (False, expected_hash, None)
            logger.warning(f"Failed to calculate {algorithm} hash for {file_path}")
            continue
        
        actual_hash = actual_hashes[algorithm]
        match = expected_hash.lower() == actual_hash.lower()
        results[file_path] = (match, expected_hash, actual_hash)
        
        if not match:
            logger.warning(f"Hash mismatch for {file_path}")
            logger.warning(f"  Expected: {expected_hash}")
            logger.warning(f"  Actual:   {actual_hash}")
    
    return results


def calculate_directory_hashes(
    directory: Union[str, Path], 
    pattern: str = '*',
    recursive: bool = True,
    algorithm: str = 'SHA256'
) -> Dict[str, str]:
    """
    Calculate hashes for all files in a directory.
    
    Args:
        directory: Directory path
        pattern: Glob pattern to match files
        recursive: Whether to recurse into subdirectories
        algorithm: Hash algorithm to use
            
    Returns:
        Dictionary mapping file paths to hash values
    """
    dir_path = Path(directory)
    results = {}
    
    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"Directory does not exist or is not a directory: {directory}")
        return results
    
    # Collect files
    files = []
    if recursive:
        for path in dir_path.rglob(pattern):
            if path.is_file():
                files.append(path)
    else:
        for path in dir_path.glob(pattern):
            if path.is_file():
                files.append(path)
    
    # Calculate hashes
    total_files = len(files)
    logger.info(f"Calculating {algorithm} hashes for {total_files} files in {directory}")
    
    for i, file_path in enumerate(files, 1):
        if i % 100 == 0 or i == total_files:
            logger.info(f"Progress: {i}/{total_files} files processed")
        
        hashes = calculate_file_hash(file_path, [algorithm])
        if algorithm in hashes:
            # Store relative path as key
            rel_path = file_path.relative_to(dir_path)
            results[str(rel_path)] = hashes[algorithm]
    
    return results


def save_hashes_to_file(
    hashes: Dict[str, str], 
    output_file: Union[str, Path],
    include_header: bool = True
) -> bool:
    """
    Save a dictionary of file hashes to a text file.
    
    Args:
        hashes: Dictionary mapping file paths to hash values
        output_file: Path to the output file
        include_header: Whether to include a header with timestamp
            
    Returns:
        True if successful, False otherwise
    """
    out_path = Path(output_file)
    
    try:
        # Create parent directories if needed
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, 'w', encoding='utf-8') as f:
            if include_header:
                f.write(f"# File hashes generated on {time.ctime()}\n")
                f.write(f"# Format: HASH PATH\n\n")
            
            for file_path, hash_value in sorted(hashes.items()):
                f.write(f"{hash_value} {file_path}\n")
        
        logger.info(f"Saved {len(hashes)} hashes to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving hashes to {output_file}: {e}")
        return False


def load_hashes_from_file(
    hash_file: Union[str, Path]
) -> Dict[str, str]:
    """
    Load file hashes from a text file.
    
    Args:
        hash_file: Path to the hash file
            
    Returns:
        Dictionary mapping file paths to hash values
    """
    file_path = Path(hash_file)
    results = {}
    
    if not file_path.exists():
        logger.error(f"Hash file does not exist: {hash_file}")
        return results
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse hash and path
                parts = line.split(' ', 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid hash file line: {line}")
                    continue
                
                hash_value, path = parts
                results[path] = hash_value
        
        logger.info(f"Loaded {len(results)} hashes from {hash_file}")
        return results
        
    except Exception as e:
        logger.error(f"Error loading hashes from {hash_file}: {e}")
        return {}


def compare_directories(
    dir1: Union[str, Path], 
    dir2: Union[str, Path],
    algorithm: str = 'SHA256',
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Compare the contents of two directories by hashing files.
    
    Args:
        dir1: First directory
        dir2: Second directory
        algorithm: Hash algorithm to use
        recursive: Whether to recurse into subdirectories
            
    Returns:
        Dictionary with comparison results
    """
    dir1_path = Path(dir1)
    dir2_path = Path(dir2)
    
    if not dir1_path.exists() or not dir1_path.is_dir():
        logger.error(f"Directory does not exist or is not a directory: {dir1}")
        return {'error': f"Directory does not exist or is not a directory: {dir1}"}
    
    if not dir2_path.exists() or not dir2_path.is_dir():
        logger.error(f"Directory does not exist or is not a directory: {dir2}")
        return {'error': f"Directory does not exist or is not a directory: {dir2}"}
    
    # Calculate hashes for both directories
    logger.info(f"Calculating hashes for directory: {dir1}")
    dir1_hashes = calculate_directory_hashes(dir1_path, recursive=recursive, algorithm=algorithm)
    
    logger.info(f"Calculating hashes for directory: {dir2}")
    dir2_hashes = calculate_directory_hashes(dir2_path, recursive=recursive, algorithm=algorithm)
    
    # Compare results
    only_in_dir1 = set(dir1_hashes.keys()) - set(dir2_hashes.keys())
    only_in_dir2 = set(dir2_hashes.keys()) - set(dir1_hashes.keys())
    
    common = set(dir1_hashes.keys()) & set(dir2_hashes.keys())
    matching = {path for path in common if dir1_hashes[path] == dir2_hashes[path]}
    differing = common - matching
    
    results = {
        'matching': list(matching),
        'differing': list(differing),
        'only_in_dir1': list(only_in_dir1),
        'only_in_dir2': list(only_in_dir2),
    }
    
    # Log summary
    logger.info(f"Comparison results:")
    logger.info(f"  Files in both directories with matching hashes: {len(matching)}")
    logger.info(f"  Files in both directories with different hashes: {len(differing)}")
    logger.info(f"  Files only in {dir1}: {len(only_in_dir1)}")
    logger.info(f"  Files only in {dir2}: {len(only_in_dir2)}")
    
    return results


def verify_copied_files(
    source_files: Dict[str, Path],
    dest_files: Dict[str, Path],
    algorithm: str = 'SHA256'
) -> Dict[str, Tuple[bool, Optional[str], Optional[str]]]:
    """
    Verify that files were copied correctly by comparing hashes.
    
    Args:
        source_files: Dictionary mapping source keys to source paths
        dest_files: Dictionary mapping source keys to destination paths
        algorithm: Hash algorithm to use
            
    Returns:
        Dictionary mapping source keys to tuples of (success, source_hash, dest_hash)
    """
    results = {}
    
    for key in source_files:
        source_path = source_files[key]
        
        # Skip if source doesn't exist in destination
        if key not in dest_files:
            logger.warning(f"Source key {key} not found in destination files")
            results[key] = (False, None, None)
            continue
            
        dest_path = dest_files[key]
        
        # Calculate source hash
        source_hashes = calculate_file_hash(source_path, [algorithm])
        if algorithm not in source_hashes:
            logger.warning(f"Failed to calculate hash for source file: {source_path}")
            results[key] = (False, None, None)
            continue
            
        source_hash = source_hashes[algorithm]
        
        # Calculate destination hash
        dest_hashes = calculate_file_hash(dest_path, [algorithm])
        if algorithm not in dest_hashes:
            logger.warning(f"Failed to calculate hash for destination file: {dest_path}")
            results[key] = (False, source_hash, None)
            continue
            
        dest_hash = dest_hashes[algorithm]
        
        # Compare hashes
        match = source_hash.lower() == dest_hash.lower()
        results[key] = (match, source_hash, dest_hash)
        
        if not match:
            logger.warning(f"Hash mismatch for file {key}")
            logger.warning(f"  Source:      {source_path}")
            logger.warning(f"  Source hash: {source_hash}")
            logger.warning(f"  Dest:        {dest_path}")
            logger.warning(f"  Dest hash:   {dest_hash}")
    
    return results