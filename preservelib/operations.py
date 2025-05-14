"""
High-level operations for preserve.py.

This module provides the core operations for copying, moving, verifying,
and restoring files with path preservation and verification.
"""

import os
import sys
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Tuple

# Import from filetoolkit if available, otherwise use local imports
try:
    from filetoolkit import paths, operations, verification
except ImportError:
    # Local imports for development/testing
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    try:
        from filetoolkit import paths, operations, verification
    except ImportError:
        # Fallbacks for testing
        paths = None
        operations = None
        verification = None

from .manifest import PreserveManifest, calculate_file_hash, verify_file_hash
from .metadata import collect_file_metadata, apply_file_metadata

# Set up module-level logger
logger = logging.getLogger(__name__)

class OperationResult:
    """
    Result of a preserve operation.
    
    Contains information about succeeded and failed files, as well as
    verification results and the operation manifest.
    """
    
    def __init__(self, operation_type: str, command_line: Optional[str] = None):
        """
        Initialize a new operation result.
        
        Args:
            operation_type: Type of operation (COPY, MOVE, VERIFY, RESTORE)
            command_line: Original command line that triggered the operation (optional)
        """
        self.operation_type = operation_type
        self.command_line = command_line
        self.succeeded = []  # List of successful file paths
        self.failed = []     # List of failed file paths
        self.skipped = []    # List of skipped file paths
        self.verified = []   # List of verified file paths
        self.unverified = [] # List of unverified file paths
        self.manifest = None # Operation manifest
        self.start_time = None # Operation start time
        self.end_time = None   # Operation end time
        self.total_bytes = 0   # Total bytes processed
        self.error_messages = {}  # Map of file paths to error messages
    
    def add_success(self, source_path: str, dest_path: str, size: int = 0) -> None:
        """
        Add a successful file operation.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            size: File size in bytes
        """
        self.succeeded.append((source_path, dest_path))
        self.total_bytes += size
    
    def add_failure(self, source_path: str, dest_path: str, error: str) -> None:
        """
        Add a failed file operation.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            error: Error message
        """
        self.failed.append((source_path, dest_path))
        self.error_messages[source_path] = error
    
    def add_skip(self, source_path: str, dest_path: str, reason: str) -> None:
        """
        Add a skipped file operation.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            reason: Reason for skipping
        """
        self.skipped.append((source_path, dest_path))
        self.error_messages[source_path] = reason
    
    def add_verification(self, path: str, verified: bool, details: Optional[Any] = None) -> None:
        """
        Add a verification result.
        
        Args:
            path: File path
            verified: Whether verification succeeded
            details: Additional verification details
        """
        if verified:
            self.verified.append((path, details))
        else:
            self.unverified.append((path, details))
    
    def set_manifest(self, manifest: PreserveManifest) -> None:
        """
        Set the operation manifest.
        
        Args:
            manifest: Operation manifest
        """
        self.manifest = manifest
    
    def set_times(self, start_time, end_time) -> None:
        """
        Set operation start and end times.
        
        Args:
            start_time: Operation start time
            end_time: Operation end time
        """
        self.start_time = start_time
        self.end_time = end_time
    
    def success_count(self) -> int:
        """Get the number of successful operations."""
        return len(self.succeeded)
    
    def failure_count(self) -> int:
        """Get the number of failed operations."""
        return len(self.failed)
    
    def skip_count(self) -> int:
        """Get the number of skipped operations."""
        return len(self.skipped)
    
    def verified_count(self) -> int:
        """Get the number of verified files."""
        return len(self.verified)
    
    def unverified_count(self) -> int:
        """Get the number of unverified files."""
        return len(self.unverified)
    
    def total_count(self) -> int:
        """Get the total number of files processed."""
        return self.success_count() + self.failure_count() + self.skip_count()
    
    def is_success(self) -> bool:
        """
        Check if the operation was completely successful.
        
        Returns:
            True if all files succeeded and were verified, False otherwise
        """
        return (self.failure_count() == 0 and 
                self.unverified_count() == 0 and 
                self.success_count() > 0)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the operation.
        
        Returns:
            Dictionary with operation summary
        """
        return {
            'operation_type': self.operation_type,
            'command_line': self.command_line,
            'success_count': self.success_count(),
            'failure_count': self.failure_count(),
            'skip_count': self.skip_count(),
            'verified_count': self.verified_count(),
            'unverified_count': self.unverified_count(),
            'total_count': self.total_count(),
            'total_bytes': self.total_bytes,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'success': self.is_success()
        }


def copy_operation(
    source_files: List[Union[str, Path]],
    dest_base: Union[str, Path],
    manifest_path: Optional[Union[str, Path]] = None,
    options: Optional[Dict[str, Any]] = None,
    command_line: Optional[str] = None
) -> OperationResult:
    """
    Copy files to a destination with path preservation.
    
    Args:
        source_files: List of source files
        dest_base: Destination base directory
        manifest_path: Path to save the manifest (optional)
        options: Additional options (optional)
        command_line: Original command line (optional)
        
    Returns:
        Operation result
    """
    # Initialize default options
    default_options = {
        'path_style': 'relative',
        'include_base': False,
        'source_base': None,
        'overwrite': False,
        'preserve_attrs': True,
        'verify': True,
        'hash_algorithm': 'SHA256',
        'create_dazzlelinks': False,
        'dazzlelink_dir': None,
        'dry_run': False
    }
    
    # Merge with provided options
    if options:
        default_options.update(options)
    
    options = default_options
    
    # Initialize operation result
    result = OperationResult('COPY', command_line)
    
    # Create manifest
    manifest = PreserveManifest()
    operation_id = manifest.add_operation(
        operation_type='COPY',
        source_path=','.join(str(s) for s in source_files),
        destination_path=str(dest_base),
        options=options,
        command_line=command_line
    )
    
    # Ensure destination directory exists
    dest_base_path = Path(dest_base)
    dest_base_path.mkdir(parents=True, exist_ok=True)
    
    # Process each source file
    for source_file in source_files:
        source_path = Path(source_file)
        
        # Skip if source doesn't exist or isn't a file
        if not source_path.exists():
            result.add_skip(str(source_path), "", "Source file does not exist")
            continue
        
        if not source_path.is_file():
            result.add_skip(str(source_path), "", "Source is not a file")
            continue
        
        try:
            # Determine destination path
            source_base = options['source_base'] if options['source_base'] else Path(source_path).parent
            
            if options['path_style'] == 'relative':
                # Relative to source_base
                try:
                    if options['include_base']:
                        # Include the base directory name
                        rel_path = source_path.relative_to(Path(source_base).parent)
                        dest_path = dest_base_path / rel_path
                    else:
                        # Just the path relative to source_base
                        rel_path = source_path.relative_to(source_base)
                        dest_path = dest_base_path / rel_path
                except ValueError:
                    # Not relative to source_base, use absolute style
                    logger.warning(f"Path {source_path} not relative to {source_base}, using absolute style")
                    if sys.platform == 'win32':
                        # Windows: use drive letter as directory
                        drive, path = os.path.splitdrive(str(source_path))
                        drive = drive.rstrip(':')  # Remove colon
                        dest_path = dest_base_path / drive / path.lstrip('\\/')
                    else:
                        # Unix: use root-relative path
                        dest_path = dest_base_path / str(source_path).lstrip('/')
            
            elif options['path_style'] == 'absolute':
                # Preserve absolute path
                if sys.platform == 'win32':
                    # Windows: use drive letter as directory
                    drive, path = os.path.splitdrive(str(source_path))
                    drive = drive.rstrip(':')  # Remove colon
                    dest_path = dest_base_path / drive / path.lstrip('\\/')
                else:
                    # Unix: use root-relative path
                    dest_path = dest_base_path / str(source_path).lstrip('/')
            
            elif options['path_style'] == 'flat':
                # Flat structure: just use filename
                dest_path = dest_base_path / source_path.name
            
            else:
                # Unknown style, default to relative
                logger.warning(f"Unknown path style: {options['path_style']}, using relative")
                rel_path = source_path.relative_to(source_base)
                dest_path = dest_base_path / rel_path
            
            # Create parent directories
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if destination exists
            if dest_path.exists() and not options['overwrite']:
                result.add_skip(str(source_path), str(dest_path), "Destination exists and overwrite not enabled")
                continue
            
            # In dry run mode, just log what would be done
            if options['dry_run']:
                result.add_success(str(source_path), str(dest_path), source_path.stat().st_size)
                logger.info(f"[DRY RUN] Would copy {source_path} to {dest_path}")
                continue
            
            # Collect metadata before copying
            metadata = None
            if options['preserve_attrs']:
                metadata = collect_file_metadata(source_path)
            
            # Copy the file
            shutil.copy2(source_path, dest_path)
            
            # Apply metadata
            if options['preserve_attrs'] and metadata:
                apply_file_metadata(dest_path, metadata)
            
            # Calculate hash if verification is enabled
            file_hashes = {}
            if options['verify']:
                file_hashes = calculate_file_hash(
                    dest_path, 
                    [options['hash_algorithm']]
                )
            
            # Add to manifest
            file_id = manifest.add_file(
                source_path=str(source_path),
                destination_path=str(dest_path),
                file_info={'size': source_path.stat().st_size},
                operation_id=operation_id
            )
            
            # Add hash to manifest
            for algorithm, hash_value in file_hashes.items():
                manifest.add_file_hash(file_id, algorithm, hash_value)
            
            # Create dazzlelink if enabled
            if options['create_dazzlelinks']:
                _create_dazzlelink(
                    source_path, 
                    dest_path, 
                    options['dazzlelink_dir']
                )
            
            # Add success to result
            result.add_success(str(source_path), str(dest_path), source_path.stat().st_size)
            
            # Verify the copy if enabled
            if options['verify']:
                source_hash = calculate_file_hash(
                    source_path,
                    [options['hash_algorithm']]
                )
                
                verified, details = verify_file_hash(dest_path, source_hash)
                result.add_verification(str(dest_path), verified, details)
                
                if not verified:
                    logger.warning(f"Verification failed for {dest_path}")
            
        except Exception as e:
            # Log error and add failure to result
            logger.error(f"Error copying {source_path} to {dest_path}: {e}")
            result.add_failure(str(source_path), str(dest_path), str(e))
    
    # Save manifest if path provided
    if manifest_path and not options['dry_run']:
        manifest_path = Path(manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest.save(manifest_path)
    
    # Set manifest in result
    result.set_manifest(manifest)
    
    return result


def move_operation(
    source_files: List[Union[str, Path]],
    dest_base: Union[str, Path],
    manifest_path: Optional[Union[str, Path]] = None,
    options: Optional[Dict[str, Any]] = None,
    command_line: Optional[str] = None
) -> OperationResult:
    """
    Move files to a destination with path preservation.
    
    Files are first copied, then verified if enabled, and finally
    removed from the source location.
    
    Args:
        source_files: List of source files
        dest_base: Destination base directory
        manifest_path: Path to save the manifest (optional)
        options: Additional options (optional)
        command_line: Original command line (optional)
        
    Returns:
        Operation result
    """
    # Initialize default options
    default_options = {
        'path_style': 'relative',
        'include_base': False,
        'source_base': None,
        'overwrite': False,
        'preserve_attrs': True,
        'verify': True,
        'hash_algorithm': 'SHA256',
        'create_dazzlelinks': False,
        'dazzlelink_dir': None,
        'dry_run': False,
        'force': False  # Force removal even if verification fails
    }
    
    # Merge with provided options
    if options:
        default_options.update(options)
    
    options = default_options
    
    # Initialize operation result
    result = OperationResult('MOVE', command_line)
    
    # Create manifest
    manifest = PreserveManifest()
    operation_id = manifest.add_operation(
        operation_type='MOVE',
        source_path=','.join(str(s) for s in source_files),
        destination_path=str(dest_base),
        options=options,
        command_line=command_line
    )
    
    # First, copy the files
    # Set verify to True to ensure files are copied correctly
    copy_options = options.copy()
    copy_options['verify'] = True
    
    copy_result = copy_operation(
        source_files=source_files,
        dest_base=dest_base,
        manifest_path=None,  # Don't save manifest yet
        options=copy_options,
        command_line=command_line
    )
    
    # Update result with copy results
    result.succeeded = copy_result.succeeded
    result.failed = copy_result.failed
    result.skipped = copy_result.skipped
    result.verified = copy_result.verified
    result.unverified = copy_result.unverified
    result.error_messages = copy_result.error_messages
    result.total_bytes = copy_result.total_bytes
    
    # Now remove source files if they were successfully copied and verified
    if not options['dry_run']:
        for source_path, dest_path in copy_result.succeeded:
            # Skip if verification failed and force is not enabled
            if not options['force']:
                verified = any(path == dest_path for path, _ in copy_result.verified)
                if not verified:
                    continue
            
            try:
                # Remove the source file
                os.unlink(source_path)
                logger.debug(f"Removed source file: {source_path}")
            except Exception as e:
                logger.error(f"Error removing source file {source_path}: {e}")
                result.error_messages[source_path] = f"Error removing source file: {e}"
    
    # Save manifest if path provided
    if manifest_path and not options['dry_run']:
        # Copy manifest from copy operation
        result.manifest = copy_result.manifest
        
        # Update operation type
        for op in result.manifest.manifest['operations']:
            if op['type'] == 'COPY':
                op['type'] = 'MOVE'
        
        # Save manifest
        manifest_path = Path(manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        result.manifest.save(manifest_path)
    
    return result


def verify_operation(
    source_files: Optional[List[Union[str, Path]]] = None,
    dest_files: Optional[List[Union[str, Path]]] = None,
    manifest_path: Optional[Union[str, Path]] = None,
    options: Optional[Dict[str, Any]] = None,
    command_line: Optional[str] = None
) -> OperationResult:
    """
    Verify files against original sources or manifest.
    
    Args:
        source_files: List of source files (optional)
        dest_files: List of destination files (optional)
        manifest_path: Path to manifest file (optional)
        options: Additional options (optional)
        command_line: Original command line (optional)
        
    Returns:
        Operation result
    """
    # Initialize default options
    default_options = {
        'hash_algorithm': 'SHA256',
        'report_path': None,
    }
    
    # Merge with provided options
    if options:
        default_options.update(options)
    
    options = default_options
    
    # Initialize operation result
    result = OperationResult('VERIFY', command_line)
    
    # Load manifest if provided
    manifest = None
    if manifest_path:
        try:
            manifest = PreserveManifest(manifest_path)
        except Exception as e:
            logger.error(f"Error loading manifest {manifest_path}: {e}")
            result.add_failure("", "", f"Error loading manifest: {e}")
            return result
    
    # If manifest provided but no files, verify all files in manifest
    if manifest and not source_files and not dest_files:
        for file_id, file_info in manifest.get_all_files().items():
            source_path = file_info.get('source_path')
            dest_path = file_info.get('destination_path')
            
            if not source_path or not dest_path:
                continue
            
            # Check if destination exists
            dest_path_obj = Path(dest_path)
            if not dest_path_obj.exists():
                result.add_failure(dest_path, "", "Destination file does not exist")
                continue
            
            # Check if source exists
            source_path_obj = Path(source_path)
            if not source_path_obj.exists():
                result.add_skip(source_path, dest_path, "Source file does not exist")
                continue
            
            # Verify file
            try:
                # Get hash from manifest or calculate from source
                if 'hashes' in file_info and options['hash_algorithm'] in file_info['hashes']:
                    # Use hash from manifest
                    expected_hash = {
                        options['hash_algorithm']: file_info['hashes'][options['hash_algorithm']]
                    }
                else:
                    # Calculate hash from source
                    expected_hash = calculate_file_hash(
                        source_path_obj,
                        [options['hash_algorithm']]
                    )
                
                # Verify destination against expected hash
                verified, details = verify_file_hash(dest_path_obj, expected_hash)
                result.add_verification(dest_path, verified, details)
                
                if verified:
                    result.add_success(source_path, dest_path, dest_path_obj.stat().st_size)
                else:
                    result.add_failure(source_path, dest_path, "Verification failed")
                    
            except Exception as e:
                logger.error(f"Error verifying {dest_path}: {e}")
                result.add_failure(source_path, dest_path, str(e))
    
    # If source and destination files provided, verify them
    elif source_files and dest_files:
        # Map source files to destination files
        if len(source_files) != len(dest_files):
            logger.error("Number of source files doesn't match number of destination files")
            result.add_failure("", "", "Number of source files doesn't match number of destination files")
            return result
        
        for i, (source_path, dest_path) in enumerate(zip(source_files, dest_files)):
            source_path_obj = Path(source_path)
            dest_path_obj = Path(dest_path)
            
            # Check if files exist
            if not source_path_obj.exists():
                result.add_skip(str(source_path_obj), str(dest_path_obj), "Source file does not exist")
                continue
                
            if not dest_path_obj.exists():
                result.add_failure(str(source_path_obj), str(dest_path_obj), "Destination file does not exist")
                continue
            
            # Verify file
            try:
                # Calculate hash from source
                expected_hash = calculate_file_hash(
                    source_path_obj,
                    [options['hash_algorithm']]
                )
                
                # Verify destination against expected hash
                verified, details = verify_file_hash(dest_path_obj, expected_hash)
                result.add_verification(str(dest_path_obj), verified, details)
                
                if verified:
                    result.add_success(str(source_path_obj), str(dest_path_obj), dest_path_obj.stat().st_size)
                else:
                    result.add_failure(str(source_path_obj), str(dest_path_obj), "Verification failed")
                    
            except Exception as e:
                logger.error(f"Error verifying {dest_path_obj}: {e}")
                result.add_failure(str(source_path_obj), str(dest_path_obj), str(e))
    
    # Generate verification report if requested
    if options['report_path'] and not result.is_success():
        try:
            _generate_verification_report(result, options['report_path'])
        except Exception as e:
            logger.error(f"Error generating verification report: {e}")
    
    return result


def restore_operation(
    source_directory: Union[str, Path],
    manifest_path: Optional[Union[str, Path]] = None,
    options: Optional[Dict[str, Any]] = None,
    command_line: Optional[str] = None
) -> OperationResult:
    """
    Restore files to their original locations.
    
    Args:
        source_directory: Directory containing files to restore
        manifest_path: Path to manifest file (optional)
        options: Additional options (optional)
        command_line: Original command line (optional)
        
    Returns:
        Operation result
    """
    # Initialize default options
    default_options = {
        'overwrite': False,
        'preserve_attrs': True,
        'verify': True,
        'hash_algorithm': 'SHA256',
        'dry_run': False,
        'force': False  # Force restoration even if verification fails
    }
    
    # Merge with provided options
    if options:
        default_options.update(options)
    
    options = default_options
    
    # Initialize operation result
    result = OperationResult('RESTORE', command_line)
    
    # Find manifest if not provided
    if not manifest_path:
        source_dir_path = Path(source_directory)
        potential_manifests = [
            source_dir_path / '.preserve' / 'manifest.json',
            source_dir_path / '.preserve' / 'preserve_manifest.json',
            source_dir_path / 'preserve_manifest.json'
        ]
        
        for path in potential_manifests:
            if path.exists():
                manifest_path = path
                break
        
        if not manifest_path:
            logger.error(f"No manifest file found in {source_directory}")
            result.add_failure("", "", "No manifest file found")
            return result
    
    # Load manifest
    try:
        manifest = PreserveManifest(manifest_path)
    except Exception as e:
        logger.error(f"Error loading manifest {manifest_path}: {e}")
        result.add_failure("", "", f"Error loading manifest: {e}")
        return result
    
    # Create new operation in manifest
    operation_id = manifest.add_operation(
        operation_type='RESTORE',
        source_path=str(source_directory),
        options=options,
        command_line=command_line
    )
    
    # Process each file in manifest
    from .restore import restore_file_to_original
    
    for file_id, file_info in manifest.get_all_files().items():
        source_orig_path = file_info.get('source_path')
        dest_orig_path = file_info.get('destination_path')
        
        if not source_orig_path or not dest_orig_path:
            continue
        
        # During restore, the destination is now the source
        current_path = Path(dest_orig_path)
        original_path = Path(source_orig_path)
        
        # Check if current path exists
        if not current_path.exists():
            result.add_skip(str(current_path), str(original_path), "Source file does not exist")
            continue
        
        # Check if original path's parent directory exists
        if not original_path.parent.exists():
            try:
                # Create parent directory
                original_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                result.add_failure(str(current_path), str(original_path), f"Error creating parent directory: {e}")
                continue
        
        # Check if original path exists and overwrite is not enabled
        if original_path.exists() and not options['overwrite']:
            result.add_skip(str(current_path), str(original_path), "Destination exists and overwrite not enabled")
            continue
        
        # In dry run mode, just log what would be done
        if options['dry_run']:
            result.add_success(str(current_path), str(original_path), current_path.stat().st_size)
            logger.info(f"[DRY RUN] Would restore {current_path} to {original_path}")
            continue
        
        # Restore file
        try:
            success = restore_file_to_original(
                current_path=current_path,
                original_path=original_path,
                metadata=file_info.get('metadata'),
                preserve_attrs=options['preserve_attrs'],
                overwrite=options['overwrite']
            )
            
            if success:
                result.add_success(str(current_path), str(original_path), current_path.stat().st_size)
                
                # Verify restoration if enabled
                if options['verify'] and 'hashes' in file_info and options['hash_algorithm'] in file_info['hashes']:
                    expected_hash = {
                        options['hash_algorithm']: file_info['hashes'][options['hash_algorithm']]
                    }
                    
                    verified, details = verify_file_hash(original_path, expected_hash)
                    result.add_verification(str(original_path), verified, details)
                    
                    if not verified:
                        logger.warning(f"Verification failed for {original_path}")
            else:
                result.add_failure(str(current_path), str(original_path), "Restoration failed")
                
        except Exception as e:
            logger.error(f"Error restoring {current_path} to {original_path}: {e}")
            result.add_failure(str(current_path), str(original_path), str(e))
    
    # Update manifest
    if not options['dry_run']:
        try:
            manifest.save(manifest_path)
        except Exception as e:
            logger.error(f"Error updating manifest: {e}")
    
    # Set manifest in result
    result.set_manifest(manifest)
    
    return result


def _create_dazzlelink(
    source_path: Union[str, Path],
    dest_path: Union[str, Path],
    dazzlelink_dir: Optional[Union[str, Path]] = None
) -> bool:
    """
    Create a dazzlelink from destination to source.
    
    Args:
        source_path: Original source path
        dest_path: Destination path
        dazzlelink_dir: Directory for dazzlelinks (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if dazzlelink module is available
        try:
            import dazzlelink
        except ImportError:
            logger.warning("Dazzlelink module not available, skipping dazzlelink creation")
            return False
        
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
        
        # Create the link
        dazzlelink.core.create_link(str(source_path), str(link_path))
        logger.debug(f"Created dazzlelink: {link_path} -> {source_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating dazzlelink: {e}")
        return False


def _generate_verification_report(
    result: OperationResult,
    report_path: Union[str, Path]
) -> bool:
    """
    Generate a verification report.
    
    Args:
        result: Operation result
        report_path: Path to save the report
        
    Returns:
        True if successful, False otherwise
    """
    try:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Verification Report\n")
            f.write(f"===================\n\n")
            f.write(f"Operation: {result.operation_type}\n")
            if result.command_line:
                f.write(f"Command: {result.command_line}\n")
            f.write(f"Date: {datetime.datetime.now().isoformat()}\n\n")
            
            f.write(f"Summary\n")
            f.write(f"-------\n")
            f.write(f"Total files: {result.total_count()}\n")
            f.write(f"Succeeded: {result.success_count()}\n")
            f.write(f"Failed: {result.failure_count()}\n")
            f.write(f"Skipped: {result.skip_count()}\n")
            f.write(f"Verified: {result.verified_count()}\n")
            f.write(f"Unverified: {result.unverified_count()}\n\n")
            
            if result.unverified:
                f.write(f"Unverified Files\n")
                f.write(f"---------------\n")
                for path, details in result.unverified:
                    f.write(f"File: {path}\n")
                    for algorithm, (match, expected, actual) in details.items():
                        f.write(f"  {algorithm}:\n")
                        f.write(f"    Expected: {expected}\n")
                        f.write(f"    Actual: {actual}\n")
                    f.write("\n")
            
            if result.failed:
                f.write(f"Failed Files\n")
                f.write(f"-----------\n")
                for source, dest in result.failed:
                    f.write(f"Source: {source}\n")
                    f.write(f"Destination: {dest}\n")
                    if source in result.error_messages:
                        f.write(f"Error: {result.error_messages[source]}\n")
                    f.write("\n")
        
        logger.info(f"Verification report saved to {report_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating verification report: {e}")
        return False
