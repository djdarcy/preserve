"""
MOVE operation handler for preserve tool.

This module implements the MOVE command which moves files to a destination
while preserving their paths and creating verification manifests. Files are
only deleted from source after successful verification.

TODO: Future refactoring opportunities:
- Extract common path validation logic shared with COPY
- Share Windows path validation with copy.py
- Consider creating common base class for copy/move operations
- The verification and deletion logic could be extracted for reuse
"""

import os
import sys
import logging
from pathlib import Path

from preservelib import operations
from preserve.utils import (
    find_files_from_args,
    get_hash_algorithms,
    get_path_style,
    get_preserve_dir,
    get_manifest_path,
    get_dazzlelink_dir,
    _show_directory_help_message,
    HAVE_DAZZLELINK
)

logger = logging.getLogger(__name__)


def handle_move_operation(args, logger):
    """Handle MOVE operation"""
    logger.info("Starting MOVE operation")

    # Check for common issue: trailing backslash in source path on Windows
    if args.sources and sys.platform == 'win32':
        for src in args.sources:
            # Check if the path looks like it might have eaten subsequent arguments
            # (happens when trailing \ escapes the closing quote)
            if '--' in src or src.count(' ') > 2:
                logger.error("")
                logger.error("ERROR: It appears the source path may have captured command-line arguments.")
                logger.error("       This usually happens when a path ends with a backslash (\\) before a quote.")
                logger.error("")
                logger.error("Problem: The trailing backslash escapes the closing quote.")
                logger.error("  Example: \"C:\\path\\to\\dir\\\" <- The \\ escapes the \"")
                logger.error("")
                logger.error("Solution: Remove the trailing backslash:")
                logger.error("  Correct: \"C:\\path\\to\\dir\"")
                logger.error("  Or use:  C:\\path\\to\\dir (without quotes if no spaces)")
                return 1
            elif src.endswith('\\'):
                logger.warning("")
                logger.warning(f"WARNING: Source path has a trailing backslash: '{src}'")
                logger.warning("         This can cause issues on Windows command line.")
                logger.warning("         Consider removing it: '{}'".format(src[:-1]))

    # Find source files
    source_files = find_files_from_args(args)

    # Check if user provided a directory without --recursive and it has subdirectories
    # Only show warning if we found SOME files (but are missing subdirectory files)
    if source_files and args.sources and not args.recursive:
        for src in args.sources:
            src_path = Path(src)
            if src_path.exists() and src_path.is_dir():
                # Check if there are subdirectories with files
                has_subdirs_with_files = False
                for root, dirs, files in os.walk(src_path):
                    if root != str(src_path) and files:
                        has_subdirs_with_files = True
                        break

                if has_subdirs_with_files:
                    _show_directory_help_message(args, logger, src, operation="MOVE", is_warning=True)

    if not source_files:
        # Check if the user provided a directory without --recursive flag
        if args.sources:
            for src in args.sources:
                src_path = Path(src)
                if src_path.exists() and src_path.is_dir() and not args.recursive:
                    _show_directory_help_message(args, logger, src, operation="MOVE", is_warning=False)
                    return 1

        logger.error("No source files found")
        return 1

    logger.info(f"Found {len(source_files)} source files")

    # Get destination path
    dest_path = Path(args.dst)
    if not dest_path.exists():
        dest_path.mkdir(parents=True, exist_ok=True)

    # Get preserve directory
    preserve_dir = get_preserve_dir(args, dest_path)

    # Get manifest path
    manifest_path = get_manifest_path(args, preserve_dir)

    # Get dazzlelink directory
    dazzlelink_dir = get_dazzlelink_dir(args, preserve_dir) if HAVE_DAZZLELINK else None

    # Get path style and source base
    path_style = get_path_style(args)
    include_base = args.includeBase if hasattr(args, 'includeBase') else False

    # Get hash algorithms
    hash_algorithms = get_hash_algorithms(args)

    # Prepare operation options
    options = {
        'path_style': path_style,
        'include_base': include_base,
        'source_base': args.srchPath[0] if args.srchPath else None,
        'overwrite': args.overwrite if hasattr(args, 'overwrite') else False,
        'preserve_attrs': not args.no_preserve_attrs if hasattr(args, 'no_preserve_attrs') else True,
        'verify': not args.no_verify if hasattr(args, 'no_verify') else True,
        'hash_algorithm': hash_algorithms[0],  # Use first algorithm for primary verification
        'create_dazzlelinks': args.dazzlelink if hasattr(args, 'dazzlelink') else False,
        'dazzlelink_dir': dazzlelink_dir,
        'dazzlelink_mode': args.dazzlelink_mode if hasattr(args, 'dazzlelink_mode') else 'info',
        'dry_run': args.dry_run if hasattr(args, 'dry_run') else False,
        'force': args.force if hasattr(args, 'force') else False
    }

    # Create command line for logging
    command_line = f"preserve MOVE {' '.join(sys.argv[2:])}"

    # Perform move operation
    result = operations.move_operation(
        source_files=source_files,
        dest_base=dest_path,
        manifest_path=manifest_path,
        options=options,
        command_line=command_line
    )

    # Print summary
    print("\nMOVE Operation Summary:")
    print(f"  Total files: {result.total_count()}")
    print(f"  Succeeded: {result.success_count()}")
    print(f"  Failed: {result.failure_count()}")
    print(f"  Skipped: {result.skip_count()}")

    if options['verify']:
        print(f"  Verified: {result.verified_count()}")
        print(f"  Unverified: {result.unverified_count()}")

    print(f"  Total bytes: {result.total_bytes}")

    # Return success if no failures and (no verification or all verified)
    return 0 if (result.failure_count() == 0 and
                (not options['verify'] or result.unverified_count() == 0)) else 1