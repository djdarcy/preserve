"""
Unified verification module for preserve operations.

This module provides consistent verification functionality for VERIFY, RESTORE,
and future three-way comparison operations. Designed to be modular and suitable
for PyPI release as part of preservelib.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from filetoolkit.verification import calculate_file_hash, verify_file_hash
from .manifest import PreserveManifest, find_available_manifests

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of file verification."""
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class FileVerificationResult:
    """Result of verifying a single file."""
    file_path: Path
    status: VerificationStatus
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    hash_algorithm: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_verified(self) -> bool:
        """Check if file was successfully verified."""
        return self.status == VerificationStatus.VERIFIED

    @property
    def is_failed(self) -> bool:
        """Check if file verification failed."""
        return self.status == VerificationStatus.FAILED


@dataclass
class VerificationResult:
    """Standardized result object for verification operations."""
    verified: List[FileVerificationResult] = field(default_factory=list)
    failed: List[FileVerificationResult] = field(default_factory=list)
    skipped: List[FileVerificationResult] = field(default_factory=list)
    errors: List[FileVerificationResult] = field(default_factory=list)
    not_found: List[FileVerificationResult] = field(default_factory=list)

    def add_result(self, result: FileVerificationResult) -> None:
        """Add a file verification result to the appropriate list."""
        if result.status == VerificationStatus.VERIFIED:
            self.verified.append(result)
        elif result.status == VerificationStatus.FAILED:
            self.failed.append(result)
        elif result.status == VerificationStatus.SKIPPED:
            self.skipped.append(result)
        elif result.status == VerificationStatus.ERROR:
            self.errors.append(result)
        elif result.status == VerificationStatus.NOT_FOUND:
            self.not_found.append(result)

    @property
    def total_files(self) -> int:
        """Total number of files processed."""
        return len(self.verified) + len(self.failed) + len(self.skipped) + len(self.errors) + len(self.not_found)

    @property
    def success_rate(self) -> float:
        """Calculate verification success rate."""
        if self.total_files == 0:
            return 0.0
        return len(self.verified) / self.total_files

    @property
    def is_successful(self) -> bool:
        """Check if all verifications were successful."""
        return len(self.failed) == 0 and len(self.errors) == 0 and len(self.not_found) == 0

    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics."""
        return {
            "verified": len(self.verified),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "errors": len(self.errors),
            "not_found": len(self.not_found),
            "total": self.total_files
        }


# Removed - now using find_available_manifests from manifest.py


def select_manifest(
    directory: Path,
    manifest_number: Optional[int] = None,
    manifest_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Select a manifest file based on various criteria.

    Args:
        directory: Directory to search for manifests
        manifest_number: Specific manifest number to select
        manifest_path: Explicit manifest path to use

    Returns:
        Path to selected manifest or None if not found
    """
    # If explicit path provided, use it
    if manifest_path and manifest_path.exists():
        return manifest_path

    # Find available manifests
    manifests = find_available_manifests(directory)

    if not manifests:
        # Try .preserve subdirectory as fallback
        preserve_dir = directory / '.preserve'
        if preserve_dir.exists():
            manifests = find_available_manifests(preserve_dir)

    if not manifests:
        logger.warning(f"No manifest files found in {directory}")
        return None

    # Select by number if specified
    if manifest_number is not None:
        for num, path, desc in manifests:
            if num == manifest_number:
                logger.info(f"Selected manifest #{num}: {path.name}")
                return path
        logger.warning(f"Manifest #{manifest_number} not found")
        return None

    # Default to latest (highest number)
    latest = manifests[-1]
    logger.info(f"Using latest manifest: {latest[1].name}")
    return latest[1]


def verify_file_against_manifest(
    file_path: Path,
    manifest_entry: Dict,
    base_path: Path,
    hash_algorithms: List[str] = None
) -> FileVerificationResult:
    """
    Verify a single file against its manifest entry.

    Args:
        file_path: Path to file to verify
        manifest_entry: Manifest entry containing expected hashes
        base_path: Base path for resolving relative paths
        hash_algorithms: Hash algorithms to use (default from manifest)

    Returns:
        FileVerificationResult object
    """
    # Resolve file path
    if not file_path.is_absolute():
        file_path = base_path / file_path

    # Check if file exists
    if not file_path.exists():
        return FileVerificationResult(
            file_path=file_path,
            status=VerificationStatus.NOT_FOUND,
            error_message=f"File not found: {file_path}"
        )

    # Get expected hashes from manifest
    expected_hashes = manifest_entry.get('hashes', {})
    if not expected_hashes:
        # Try old format
        if 'hash' in manifest_entry and 'hash_algorithm' in manifest_entry:
            expected_hashes = {manifest_entry['hash_algorithm']: manifest_entry['hash']}

    if not expected_hashes:
        return FileVerificationResult(
            file_path=file_path,
            status=VerificationStatus.SKIPPED,
            error_message="No hash information in manifest"
        )

    # Verify each hash
    for algorithm, expected_hash in expected_hashes.items():
        if hash_algorithms and algorithm not in hash_algorithms:
            continue

        try:
            actual_hash = calculate_file_hash(str(file_path), algorithm)

            if actual_hash.lower() == expected_hash.lower():
                return FileVerificationResult(
                    file_path=file_path,
                    status=VerificationStatus.VERIFIED,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    hash_algorithm=algorithm
                )
            else:
                return FileVerificationResult(
                    file_path=file_path,
                    status=VerificationStatus.FAILED,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    hash_algorithm=algorithm,
                    error_message=f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
                )

        except Exception as e:
            return FileVerificationResult(
                file_path=file_path,
                status=VerificationStatus.ERROR,
                hash_algorithm=algorithm,
                error_message=f"Error calculating hash: {str(e)}"
            )

    return FileVerificationResult(
        file_path=file_path,
        status=VerificationStatus.SKIPPED,
        error_message="No matching hash algorithm found"
    )


def verify_files_against_manifest(
    manifest: PreserveManifest,
    destination: Path,
    hash_algorithms: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None
) -> VerificationResult:
    """
    Verify files against a manifest.

    Args:
        manifest: Preserve manifest object
        destination: Destination directory containing files
        hash_algorithms: Hash algorithms to use (None = use all from manifest)
        progress_callback: Optional callback for progress reporting

    Returns:
        VerificationResult object with all verification results
    """
    result = VerificationResult()

    # Get files from manifest
    files = manifest.get_files()
    total_files = len(files)

    for index, (relative_path, file_info) in enumerate(files.items()):
        # Report progress if callback provided
        if progress_callback:
            progress_callback(index, total_files, relative_path)

        # Build full path
        file_path = destination / relative_path

        # Verify file
        file_result = verify_file_against_manifest(
            file_path=file_path,
            manifest_entry=file_info,
            base_path=destination,
            hash_algorithms=hash_algorithms
        )

        result.add_result(file_result)

        # Log result
        if file_result.is_verified:
            logger.debug(f"Verified: {relative_path}")
        elif file_result.is_failed:
            logger.warning(f"Verification failed: {relative_path} - {file_result.error_message}")
        else:
            logger.debug(f"{file_result.status.value}: {relative_path}")

    # Final progress callback
    if progress_callback:
        progress_callback(total_files, total_files, "Complete")

    return result


def find_and_verify_manifest(
    destination: Path,
    manifest_number: Optional[int] = None,
    manifest_path: Optional[Path] = None,
    hash_algorithms: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[Optional[PreserveManifest], VerificationResult]:
    """
    Find a manifest and verify files against it.

    This is the main entry point for VERIFY operations.

    Args:
        destination: Destination directory to verify
        manifest_number: Specific manifest number to use
        manifest_path: Explicit manifest path
        hash_algorithms: Hash algorithms to use
        progress_callback: Progress reporting callback

    Returns:
        Tuple of (manifest, verification_result)
    """
    # Select manifest
    selected_manifest = select_manifest(
        directory=destination,
        manifest_number=manifest_number,
        manifest_path=manifest_path
    )

    if not selected_manifest:
        return None, VerificationResult()

    # Load manifest
    try:
        manifest = PreserveManifest(selected_manifest)
        logger.info(f"Loaded manifest from {selected_manifest}")
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        return None, VerificationResult()

    # Verify files
    result = verify_files_against_manifest(
        manifest=manifest,
        destination=destination,
        hash_algorithms=hash_algorithms,
        progress_callback=progress_callback
    )

    return manifest, result


# Three-way verification for Issue #11 (future implementation)
@dataclass
class ThreeWayVerificationResult(VerificationResult):
    """Extended result for three-way comparison between source, preserved, and manifest."""
    source_modified: List[FileVerificationResult] = field(default_factory=list)
    preserved_corrupted: List[FileVerificationResult] = field(default_factory=list)
    all_match: List[FileVerificationResult] = field(default_factory=list)

    def categorize_difference(
        self,
        source_hash: Optional[str],
        preserved_hash: Optional[str],
        manifest_hash: str,
        file_path: Path
    ) -> FileVerificationResult:
        """
        Categorize the difference between three hashes.

        Returns a FileVerificationResult with appropriate status and details.
        """
        # All three match
        if source_hash == preserved_hash == manifest_hash:
            result = FileVerificationResult(
                file_path=file_path,
                status=VerificationStatus.VERIFIED,
                expected_hash=manifest_hash,
                actual_hash=preserved_hash
            )
            self.all_match.append(result)
            return result

        # Source modified since preservation
        if preserved_hash == manifest_hash and source_hash != manifest_hash:
            result = FileVerificationResult(
                file_path=file_path,
                status=VerificationStatus.FAILED,
                expected_hash=manifest_hash,
                actual_hash=source_hash,
                error_message="Source file modified since preservation"
            )
            self.source_modified.append(result)
            return result

        # Preserved copy corrupted
        if source_hash == manifest_hash and preserved_hash != manifest_hash:
            result = FileVerificationResult(
                file_path=file_path,
                status=VerificationStatus.FAILED,
                expected_hash=manifest_hash,
                actual_hash=preserved_hash,
                error_message="Preserved file corrupted"
            )
            self.preserved_corrupted.append(result)
            return result

        # Both different (complex situation)
        result = FileVerificationResult(
            file_path=file_path,
            status=VerificationStatus.ERROR,
            expected_hash=manifest_hash,
            error_message=f"Complex difference: source={source_hash}, preserved={preserved_hash}, manifest={manifest_hash}"
        )
        self.errors.append(result)
        return result


def verify_three_way(
    source_path: Path,
    preserved_path: Path,
    manifest: PreserveManifest,
    hash_algorithms: Optional[List[str]] = None,
    progress_callback: Optional[callable] = None
) -> ThreeWayVerificationResult:
    """
    Perform three-way verification between source, preserved, and manifest.

    This function will be fully implemented for Issue #11.

    Args:
        source_path: Original source directory
        preserved_path: Preserved/backup directory
        manifest: Manifest with expected hashes
        hash_algorithms: Hash algorithms to use
        progress_callback: Progress reporting callback

    Returns:
        ThreeWayVerificationResult with categorized differences
    """
    result = ThreeWayVerificationResult()

    # TODO: Implementation for Issue #11
    logger.info("Three-way verification not yet implemented")

    return result