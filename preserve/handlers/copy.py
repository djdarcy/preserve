"""
COPY operation handler for preserve tool.

This module implements the COPY command which copies files to a destination
while preserving their paths and creating verification manifests.

TODO: Future refactoring opportunities:
- Extract common path validation logic shared with MOVE
- Consider creating a PathValidator class for Windows path issues
- The find_longest_common_path_prefix could be moved to pathutils
- Operation result printing could be extracted to a common formatter
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


def handle_copy_operation(args, logger):
    """Handle COPY operation"""
    logger.info("Starting COPY operation")

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

    # Early debug info for path style
    path_style = get_path_style(args)
    if path_style == 'relative':
        logger.info("")
        logger.info("Using RELATIVE path style for COPY operation")
        if args.srchPath:
            logger.info(f"  Source base directory: {args.srchPath[0]}")
        else:
            logger.info("  No explicit source base directory provided")
            logger.info("  Will attempt to find a common base directory for all files")

            # Find the longest common path prefix for files in --rel mode
            if args.loadIncludes:
                try:
                    # Define a function to find the longest common prefix of paths
                    def find_longest_common_path_prefix(paths):
                        """Find the longest common directory prefix of a list of paths."""
                        if not paths:
                            return None

                        # Convert all paths to Path objects and normalize separators
                        normalized_paths = []
                        for p in paths:
                            try:
                                # Convert string to Path
                                path_obj = Path(p.strip())
                                # Convert to string with forward slashes for consistency
                                norm_path = str(path_obj).replace('\\', '/')
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

                    # Read the file list
                    with open(args.loadIncludes, 'r') as f:
                        file_lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]

                    # Find the common prefix
                    common_prefix = find_longest_common_path_prefix(file_lines)
                    if common_prefix:
                        logger.info(f"  Found common path prefix: {common_prefix}")
                        logger.info(f"  Will use this as base directory for relative paths")
                        # Store in global options to be used later
                        args.common_prefix = common_prefix
                    else:
                        logger.info(f"  No common path prefix found among input files")
                        logger.info(f"  Will use nearest common parent directories when possible")
                except Exception as e:
                    logger.debug(f"Error analyzing include file: {e}")

        include_base = args.includeBase if hasattr(args, 'includeBase') else False
        logger.info(f"  Include base directory name: {include_base}")
        logger.info("")  # Add blank line for better readability

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
                    _show_directory_help_message(args, logger, src, operation="COPY", is_warning=True)

    if not source_files:
        # Check if the user provided a directory without --recursive flag
        if args.sources:
            for src in args.sources:
                src_path = Path(src)
                if src_path.exists() and src_path.is_dir() and not args.recursive:
                    _show_directory_help_message(args, logger, src, operation="COPY", is_warning=False)
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
        'dry_run': args.dry_run if hasattr(args, 'dry_run') else False
    }

    # Create command line for logging
    command_line = f"preserve COPY {' '.join(sys.argv[2:])}"

    # Perform copy operation
    result = operations.copy_operation(
        source_files=source_files,
        dest_base=dest_path,
        manifest_path=manifest_path,
        options=options,
        command_line=command_line
    )

    # Print summary
    print("\nCOPY Operation Summary:")
    print(f"  Total files: {result.total_count()}")
    print(f"  Succeeded: {result.success_count()}")
    print(f"  Failed: {result.failure_count()}")
    print(f"  Skipped: {result.skip_count()}")

    # Print detailed skipped file info if there are skipped files
    if result.skip_count() > 0:
        print("\nSkipped Files (all):")
        for i, (source, dest) in enumerate(result.skipped):
            reason = result.error_messages.get(source, "Unknown reason")
            print(f"  {i+1}. {source} -> {dest}")
            print(f"     Reason: {reason}")

    if options['verify']:
        print(f"  Verified: {result.verified_count()}")
        print(f"  Unverified: {result.unverified_count()}")

    print(f"  Total bytes: {result.total_bytes}")

    # Return success if no failures and (no verification or all verified)
    return 0 if (result.failure_count() == 0 and
                (not options['verify'] or result.unverified_count() == 0)) else 1