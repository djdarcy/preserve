#!/usr/bin/env python3
"""
preserve.py - A tool for preserving files with path normalization and verification

This tool copies or moves files between locations while preserving their paths
in a configurable way, maintaining file attributes, and providing verification.
It supports bidirectional operations (restore) and can integrate with dazzlelink.

Usage:
    preserve OPERATION [OPTIONS] [SOURCES...] --dst DESTINATION
    
Operations:
    COPY               Copy files to destination with path preservation
    MOVE               Copy files then remove originals after verification
    VERIFY             Verify files against sources or stored hashes
    RESTORE            Restore files to their original locations
    CONFIG             View or modify configuration settings
    
Examples:
    # Copy files matching a glob pattern with relative paths
    preserve COPY --glob "*.txt" --srchPath "c:/data" --rel --dst "e:/backup"
    
    # Copy files with a specific structure, including hashes
    preserve COPY --glob "*.jpg" --srchPath "d:/photos" --hash SHA256 --dst "e:/archive"
    
    # Move files with absolute path preservation
    preserve MOVE --glob "*.docx" --srchPath "c:/old" --abs --dst "d:/new"
    
    # Verify files in destination against sources
    preserve VERIFY --dst "e:/backup"
    
    # Restore files to original locations
    preserve RESTORE --src "e:/backup" --force
    
    # Load a list of files to copy from a text file
    preserve COPY --loadIncludes "files_to_copy.txt" --dst "e:/backup"
"""

import os
import sys
import argparse
import logging
import json
import datetime
import time
import platform
from pathlib import Path
import importlib
from typing import List, Dict, Any, Optional, Union, Tuple

# print("--- preserve.py ---")
# print(f"Current working directory: {os.getcwd()}")
# print("sys.path:")
# for p_idx, p_val in enumerate(sys.path):
#     print(f"  [{p_idx}] = {p_val}")
# print("--- end of sys.path debug ---")

# Import from preserve package
from .help import examples
from .config import PreserveConfig
from . import utils

# Import preservelib package
import preservelib
from preservelib import operations, manifest, metadata, restore
#from preservelib.config import get_config

# Check for dazzlelink integration
try:
    from preservelib import dazzlelink
    HAVE_DAZZLELINK = dazzlelink.is_available()
except ImportError:
    HAVE_DAZZLELINK = False

# Import filetoolkit package
import filetoolkit
from filetoolkit import paths, operations as file_ops, verification

# Version information
__version__ = "0.1.0"

def setup_logging(args):
    """Set up logging based on verbosity level"""
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get logger for this module
    logger = logging.getLogger('preserve')
    
    # Add file handler if log file specified
    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    return logger

def create_parser():
    """Create argument parser with all CLI options"""
    parser = argparse.ArgumentParser(
        description='Preserve files with path normalization and verification',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # General options
    parser.add_argument('--version', '-V', action='version', 
                        version=f'preserve {__version__}')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true', 
                        help='Suppress all non-error output')
    parser.add_argument('--log', help='Write log to specified file')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    # Create subparsers for operations
    subparsers = parser.add_subparsers(dest='operation', help='Operation to perform')
    
    # === COPY operation ===
    copy_parser = subparsers.add_parser('COPY', help='Copy files to destination with path preservation')
    _add_source_args(copy_parser)
    _add_destination_args(copy_parser)
    _add_path_args(copy_parser)
    _add_verification_args(copy_parser)
    _add_dazzlelink_args(copy_parser)
    copy_parser.add_argument('--dry-run', action='store_true', 
                            help='Show what would be done without making changes')
    copy_parser.add_argument('--overwrite', action='store_true', 
                            help='Overwrite existing files in destination')
    copy_parser.add_argument('--no-preserve-attrs', action='store_true', 
                            help='Do not preserve file attributes')
    
    # === MOVE operation ===
    move_parser = subparsers.add_parser('MOVE', help='Copy files then remove originals after verification')
    _add_source_args(move_parser)
    _add_destination_args(move_parser)
    _add_path_args(move_parser)
    _add_verification_args(move_parser)
    _add_dazzlelink_args(move_parser)
    move_parser.add_argument('--dry-run', action='store_true', 
                            help='Show what would be done without making changes')
    move_parser.add_argument('--overwrite', action='store_true', 
                            help='Overwrite existing files in destination')
    move_parser.add_argument('--force', action='store_true', 
                            help='Force removal of source files even if verification fails')
    
    # === VERIFY operation ===
    verify_parser = subparsers.add_parser('VERIFY', help='Verify files against sources or stored hashes')
    verify_parser.add_argument('--src', help='Source location to verify against (if not specified, uses manifest)')
    verify_parser.add_argument('--dst', required=True, help='Destination location to verify')
    verify_parser.add_argument('--hash', action='append', choices=['MD5', 'SHA1', 'SHA256', 'SHA512'], 
                              help='Hash algorithm(s) to use for verification (can specify multiple)')
    verify_parser.add_argument('--manifest', help='Manifest file to use for verification')
    verify_parser.add_argument('--report', help='Write verification report to specified file')
    
    # === RESTORE operation ===
    restore_parser = subparsers.add_parser('RESTORE', help='Restore files to their original locations')
    restore_parser.add_argument('--src', required=True, help='Source location containing preserved files')
    restore_parser.add_argument('--manifest', help='Manifest file to use for restoration')
    restore_parser.add_argument('--dry-run', action='store_true', 
                               help='Show what would be done without making changes')
    restore_parser.add_argument('--overwrite', action='store_true', 
                               help='Overwrite existing files during restoration')
    restore_parser.add_argument('--force', action='store_true', 
                               help='Force restoration even if verification fails')
    restore_parser.add_argument('--hash', action='append', choices=['MD5', 'SHA1', 'SHA256', 'SHA512'], 
                               help='Hash algorithm(s) to use for verification (can specify multiple)')
    
    # === CONFIG operation ===
    config_parser = subparsers.add_parser('CONFIG', help='View or modify configuration settings')
    config_subparsers = config_parser.add_subparsers(dest='config_operation', help='Configuration operation')
    
    # View config
    view_config_parser = config_subparsers.add_parser('VIEW', help='View current configuration')
    view_config_parser.add_argument('--section', help='Configuration section to view')
    
    # Set config
    set_config_parser = config_subparsers.add_parser('SET', help='Set configuration option')
    set_config_parser.add_argument('key', help='Configuration key (e.g., "paths.default_style")')
    set_config_parser.add_argument('value', help='Configuration value')
    
    # Reset config
    reset_config_parser = config_subparsers.add_parser('RESET', help='Reset configuration to defaults')
    reset_config_parser.add_argument('--section', help='Configuration section to reset (omit for all)')
    
    return parser

def _add_source_args(parser):
    """Add source-related arguments to a parser"""
    source_group = parser.add_argument_group('Source options')
    
    # Ways to specify sources
    sources_spec = source_group.add_mutually_exclusive_group()
    sources_spec.add_argument('sources', nargs='*', help='Source files or directories to process', default=[])
    sources_spec.add_argument('--srchPath', action='append', help='Directories to search within (can specify multiple)')
    
    # Pattern matching
    pattern_group = source_group.add_mutually_exclusive_group()
    pattern_group.add_argument('--glob', action='append', help='Glob pattern(s) to match files (can specify multiple)')
    pattern_group.add_argument('--regex', action='append', help='Regular expression(s) to match files (can specify multiple)')
    
    # Include/exclude options
    source_group.add_argument('--include', action='append', help='Explicitly include file or directory (can specify multiple)')
    source_group.add_argument('--exclude', action='append', help='Explicitly exclude file or directory (can specify multiple)')
    source_group.add_argument('--loadIncludes', help='Load includes from file (one per line)')
    source_group.add_argument('--loadExcludes', help='Load excludes from file (one per line)')
    
    # Recursion and filtering
    source_group.add_argument('--recursive', '-r', action='store_true', help='Recurse into subdirectories')
    source_group.add_argument('--max-depth', type=int, help='Maximum recursion depth')
    source_group.add_argument('--follow-symlinks', action='store_true', help='Follow symbolic links during recursion')
    source_group.add_argument('--newer-than', help='Only include files newer than this date or time period (e.g., "7d", "2023-01-01")')

def _add_destination_args(parser):
    """Add destination-related arguments to a parser"""
    dest_group = parser.add_argument_group('Destination options')
    dest_group.add_argument('--dst', required=True, help='Destination directory')
    dest_group.add_argument('--preserve-dir', action='store_true', 
                          help='Create .preserve directory for manifests and metadata')
    dest_group.add_argument('--manifest', help='Custom manifest filename (default: preserve_manifest.json)')
    dest_group.add_argument('--no-manifest', action='store_true', help='Do not create a manifest file')

def _add_path_args(parser):
    """Add path normalization arguments to a parser"""
    path_group = parser.add_argument_group('Path normalization options')
    
    # Path styles
    style_group = path_group.add_mutually_exclusive_group()
    style_group.add_argument('--rel', action='store_true', help='Use relative paths in destination')
    style_group.add_argument('--abs', action='store_true', help='Use absolute paths (with drive letter as directory) in destination')
    style_group.add_argument('--flat', action='store_true', help='Flatten directory structure (files directly in destination)')
    
    # Base path options
    path_group.add_argument('--includeBase', action='store_true', 
                           help='Include base path of --srchPath in destination path')

def _add_verification_args(parser):
    """Add verification-related arguments to a parser"""
    verify_group = parser.add_argument_group('Verification options')
    verify_group.add_argument('--hash', action='append', choices=['MD5', 'SHA1', 'SHA256', 'SHA512'], 
                             help='Hash algorithm(s) to use for verification (can specify multiple)')
    verify_group.add_argument('--verify', action='store_true', help='Verify files after operation')
    verify_group.add_argument('--no-verify', action='store_true', help='Skip verification after operation')
    verify_group.add_argument('--checksum-file', help='Write checksums to file')

def _add_dazzlelink_args(parser):
    """Add dazzlelink-related arguments to a parser"""
    dazzle_group = parser.add_argument_group('Dazzlelink options')
    dazzle_group.add_argument('--dazzlelink', action='store_true', help='Create dazzlelinks to original files')
    dazzle_group.add_argument('--dazzlelink-dir', help='Directory for dazzlelinks (default: .preserve/dazzlelinks)')
    dazzle_group.add_argument('--dazzlelink-with-files', action='store_true', 
                             help='Store dazzlelinks alongside copied files')

def find_files_from_args(args):
    """Find files based on command-line arguments"""
    source_files = []
    
    # Direct source files
    if args.sources:
        for src in args.sources:
            src_path = Path(src)
            if src_path.exists():
                if src_path.is_file():
                    source_files.append(src_path)
                elif src_path.is_dir() and args.recursive:
                    # Recursively add all files in directory
                    for root, _, files in os.walk(src_path):
                        for file in files:
                            source_files.append(Path(root) / file)
                else:
                    # Not recursive, just add files in top-level directory
                    for item in src_path.glob('*'):
                        if item.is_file():
                            source_files.append(item)
    
    # Search paths with glob/regex patterns
    if args.srchPath:
        search_paths = [Path(p) for p in args.srchPath]
        
        if args.glob:
            # Use glob patterns
            for search_path in search_paths:
                for pattern in args.glob:
                    if args.recursive:
                        # Recursive search
                        for file in search_path.glob('**/' + pattern):
                            if file.is_file():
                                source_files.append(file)
                    else:
                        # Non-recursive search
                        for file in search_path.glob(pattern):
                            if file.is_file():
                                source_files.append(file)
                                
        elif args.regex:
            # Use regex patterns
            import re
            patterns = [re.compile(p) for p in args.regex]
            
            for search_path in search_paths:
                if args.recursive:
                    # Recursive search
                    for root, _, files in os.walk(search_path):
                        for file in files:
                            file_path = Path(root) / file
                            if any(p.search(str(file_path)) for p in patterns):
                                source_files.append(file_path)
                else:
                    # Non-recursive search
                    for file in search_path.iterdir():
                        if file.is_file() and any(p.search(str(file)) for p in patterns):
                            source_files.append(file)
    
    # Handle includes
    if args.include:
        for include in args.include:
            inc_path = Path(include)
            if inc_path.exists():
                if inc_path.is_file():
                    source_files.append(inc_path)
                elif inc_path.is_dir() and args.recursive:
                    # Recursively add all files in directory
                    for root, _, files in os.walk(inc_path):
                        for file in files:
                            source_files.append(Path(root) / file)
    
    # Handle loadIncludes
    if args.loadIncludes:
        try:
            with open(args.loadIncludes, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        inc_path = Path(line)
                        if inc_path.exists() and inc_path.is_file():
                            source_files.append(inc_path)
        except Exception as e:
            logging.error(f"Error loading includes from {args.loadIncludes}: {e}")
    
    # Handle excludes and loadExcludes
    exclude_paths = set()
    
    if args.exclude:
        for exclude in args.exclude:
            excl_path = Path(exclude)
            if excl_path.exists():
                if excl_path.is_file():
                    exclude_paths.add(excl_path)
                elif excl_path.is_dir():
                    # Add directory and all contents
                    exclude_paths.add(excl_path)
                    if args.recursive:
                        for root, _, files in os.walk(excl_path):
                            for file in files:
                                exclude_paths.add(Path(root) / file)
    
    if args.loadExcludes:
        try:
            with open(args.loadExcludes, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        excl_path = Path(line)
                        if excl_path.exists():
                            exclude_paths.add(excl_path)
        except Exception as e:
            logging.error(f"Error loading excludes from {args.loadExcludes}: {e}")
    
    # Apply newer-than filter if specified
    if hasattr(args, 'newer_than') and args.newer_than:
        try:
            cutoff_time = utils.parse_time_spec(args.newer_than)
            source_files = [f for f in source_files if f.stat().st_mtime > cutoff_time]
        except Exception as e:
            logging.error(f"Error applying newer-than filter: {e}")
    
    # Remove excluded files
    source_files = [f for f in source_files if f not in exclude_paths]
    
    # Remove duplicates while preserving order
    unique_files = []
    seen = set()
    for file in source_files:
        file_str = str(file)
        if file_str not in seen:
            seen.add(file_str)
            unique_files.append(file)
    
    return unique_files

def get_hash_algorithms(args):
    """Get hash algorithms from command-line arguments"""
    if args.hash:
        return args.hash
    else:
        return ['SHA256']  # Default

def get_path_style(args):
    """Get path style from command-line arguments"""
    if args.rel:
        return 'relative'
    elif args.abs:
        return 'absolute'
    elif args.flat:
        return 'flat'
    else:
        return 'relative'  # Default

def get_preserve_dir(args, dest_path):
    """Get preserve directory path"""
    if args.preserve_dir:
        preserve_dir = Path(dest_path) / '.preserve'
        preserve_dir.mkdir(parents=True, exist_ok=True)
        return preserve_dir
    return None

def get_manifest_path(args, preserve_dir):
    """Get manifest file path"""
    if args.no_manifest:
        return None
    
    if args.manifest:
        return Path(args.manifest)
    
    if preserve_dir:
        return preserve_dir / 'preserve_manifest.json'
    
    return Path(args.dst) / 'preserve_manifest.json'

def get_dazzlelink_dir(args, preserve_dir):
    """Get dazzlelink directory path"""
    if not args.dazzlelink:
        return None
    
    if args.dazzlelink_with_files:
        return None  # Store alongside files
    
    if args.dazzlelink_dir:
        dl_dir = Path(args.dazzlelink_dir)
        dl_dir.mkdir(parents=True, exist_ok=True)
        return dl_dir
    
    if preserve_dir:
        dl_dir = preserve_dir / 'dazzlelinks'
        dl_dir.mkdir(parents=True, exist_ok=True)
        return dl_dir
    
    return None

def handle_copy_operation(args, logger):
    """Handle COPY operation"""
    logger.info("Starting COPY operation")
    
    # Find source files
    source_files = find_files_from_args(args)
    if not source_files:
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
    
    if options['verify']:
        print(f"  Verified: {result.verified_count()}")
        print(f"  Unverified: {result.unverified_count()}")
    
    print(f"  Total bytes: {result.total_bytes}")
    
    # Return success if no failures and (no verification or all verified)
    return 0 if (result.failure_count() == 0 and 
                (not options['verify'] or result.unverified_count() == 0)) else 1

def handle_move_operation(args, logger):
    """Handle MOVE operation"""
    logger.info("Starting MOVE operation")
    
    # Find source files
    source_files = find_files_from_args(args)
    if not source_files:
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

def handle_verify_operation(args, logger):
    """Handle VERIFY operation"""
    logger.info("Starting VERIFY operation")
    
    # Get destination path
    dest_path = Path(args.dst)
    if not dest_path.exists():
        logger.error(f"Destination directory does not exist: {dest_path}")
        return 1
    
    # Get source path if provided
    source_path = Path(args.src) if args.src else None
    
    # Get hash algorithms
    hash_algorithms = get_hash_algorithms(args)
    
    # Get manifest path
    manifest_path = Path(args.manifest) if args.manifest else None
    
    if not manifest_path and not source_path:
        # Try to find manifest in common locations
        potential_manifests = [
            dest_path / '.preserve' / 'manifest.json',
            dest_path / '.preserve' / 'preserve_manifest.json',
            dest_path / 'preserve_manifest.json'
        ]
        
        for path in potential_manifests:
            if path.exists():
                manifest_path = path
                break
    
    if not manifest_path and not source_path:
        logger.error("No source or manifest provided for verification")
        return 1
    
    # Prepare operation options
    options = {
        'hash_algorithm': hash_algorithms[0],
        'report_path': args.report if hasattr(args, 'report') else None
    }
    
    # Collect source and destination files
    source_files = []
    dest_files = []
    
    if source_path:
        # Use source and destination for verification
        if source_path.is_dir() and dest_path.is_dir():
            # Compare directories
            for root, _, files in os.walk(source_path):
                for file in files:
                    src_file = Path(root) / file
                    rel_path = src_file.relative_to(source_path)
                    dst_file = dest_path / rel_path
                    
                    if dst_file.exists():
                        source_files.append(src_file)
                        dest_files.append(dst_file)
        else:
            # Compare individual files
            source_files.append(source_path)
            dest_files.append(dest_path)
    
    # Create command line for logging
    command_line = f"preserve VERIFY {' '.join(sys.argv[2:])}"
    
    # Perform verification
    result = operations.verify_operation(
        source_files=source_files if source_files else None,
        dest_files=dest_files if dest_files else None,
        manifest_path=manifest_path,
        options=options,
        command_line=command_line
    )
    
    # Print summary
    print("\nVERIFY Operation Summary:")
    print(f"  Verified: {result.verified_count()}")
    print(f"  Unverified: {result.unverified_count()}")
    print(f"  Failed: {result.failure_count()}")
    
    if options['report_path']:
        print(f"  Report written to: {options['report_path']}")
    
    # Return success if all files verified
    return 0 if result.unverified_count() == 0 and result.failure_count() == 0 else 1

def handle_restore_operation(args, logger):
    """Handle RESTORE operation"""
    logger.info("Starting RESTORE operation")
    
    # Get source path
    source_path = Path(args.src)
    if not source_path.exists():
        logger.error(f"Source directory does not exist: {source_path}")
        return 1
    
    # Get manifest path
    manifest_path = Path(args.manifest) if args.manifest else None
    
    if not manifest_path:
        # Try to find manifest in common locations
        potential_manifests = [
            source_path / '.preserve' / 'manifest.json',
            source_path / '.preserve' / 'preserve_manifest.json',
            source_path / 'preserve_manifest.json'
        ]
        
        for path in potential_manifests:
            if path.exists():
                manifest_path = path
                break
    
    # Try to load manifest
    man = None
    if manifest_path and manifest_path.exists():
        try:
            man = manifest.PreserveManifest(manifest_path)
            logger.info(f"Loaded manifest from {manifest_path}")
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            return 1
    
    if not man:
        logger.error("No manifest found for restoration")
        return 1
    
    # Get hash algorithms
    hash_algorithms = get_hash_algorithms(args)
    
    # Prepare operation options
    options = {
        'overwrite': args.overwrite if hasattr(args, 'overwrite') else False,
        'preserve_attrs': True,
        'verify': True,
        'hash_algorithm': hash_algorithms[0],
        'dry_run': args.dry_run if hasattr(args, 'dry_run') else False,
        'force': args.force if hasattr(args, 'force') else False
    }
    
    # Create command line for logging
    command_line = f"preserve RESTORE {' '.join(sys.argv[2:])}"
    
    # Perform restoration
    result = operations.restore_operation(
        source_directory=source_path,
        manifest_path=manifest_path,
        options=options,
        command_line=command_line
    )
    
    # Print summary
    print("\nRESTORE Operation Summary:")
    print(f"  Total files: {result.total_count()}")
    print(f"  Succeeded: {result.success_count()}")
    print(f"  Failed: {result.failure_count()}")
    print(f"  Skipped: {result.skip_count()}")
    
    if options['verify']:
        print(f"  Verified: {result.verified_count()}")
        print(f"  Unverified: {result.unverified_count()}")
    
    # Return success if no failures and (no verification or all verified)
    return 0 if (result.failure_count() == 0 and 
                (not options['verify'] or result.unverified_count() == 0)) else 1

def handle_config_operation(args, logger):
    """Handle CONFIG operation"""
    # Load configuration
    cfg = PreserveConfig()
    
    if not args.config_operation:
        logger.error("No config operation specified")
        return 1
    
    if args.config_operation == 'VIEW':
        # View configuration
        config_dict = cfg.to_dict()
        
        if args.section:
            # View specific section
            if args.section in config_dict:
                print(f"Configuration section '{args.section}':")
                for key, value in config_dict[args.section].items():
                    print(f"  {key}: {value}")
            else:
                logger.error(f"Configuration section '{args.section}' not found")
                return 1
        else:
            # View all configuration
            print("Current configuration:")
            for section, section_data in config_dict.items():
                print(f"\n[{section}]")
                for key, value in section_data.items():
                    print(f"  {key}: {value}")
        
        return 0
        
    elif args.config_operation == 'SET':
        # Set configuration value
        key_parts = args.key.split('.')
        if len(key_parts) != 2:
            logger.error("Configuration key must be in the format 'section.option'")
            return 1
        
        section, option = key_parts
        value = args.value
        
        # Convert value to appropriate type
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.isdigit():
            value = int(value)
        
        # Set value
        cfg.set(args.key, value)
        
        # Save configuration
        if cfg.save_global_config():
            print(f"Set {args.key} = {value} in global configuration")
            return 0
        else:
            logger.error("Failed to save configuration")
            return 1
            
    elif args.config_operation == 'RESET':
        # Reset configuration
        if args.section:
            # Reset specific section
            if cfg.reset_section(args.section):
                print(f"Reset configuration section '{args.section}' to defaults")
                
                # Save configuration
                if cfg.save_global_config():
                    return 0
                else:
                    logger.error("Failed to save configuration")
                    return 1
            else:
                logger.error(f"Configuration section '{args.section}' not found")
                return 1
        else:
            # Reset all configuration
            cfg.reset_to_defaults()
            
            # Save configuration
            if cfg.save_global_config():
                print("Reset configuration to defaults")
                return 0
            else:
                logger.error("Failed to save configuration")
                return 1
    
    else:
        logger.error(f"Unknown config operation: {args.config_operation}")
        return 1

def display_help_with_examples(parser, args):
    """Display help with examples for a specific operation"""
    if hasattr(args, 'operation') and args.operation:
        operation = args.operation
        parser.print_help()
        print("\n" + examples.get_operation_examples(operation))
    else:
        parser.print_help()
        print("\nFor more examples, use --help with a specific operation")

def main():
    """Main entry point for the program"""
    # Parse command line arguments
    parser = create_parser()
    
    # Handle --help specially to provide examples
    if len(sys.argv) == 1 or '--help' in sys.argv or '-h' in sys.argv:
        args = parser.parse_args([]) if len(sys.argv) == 1 else parser.parse_args()
        display_help_with_examples(parser, args)
        return 0
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args)
    
    # Disable colors if requested
    if args.no_color:
        utils.disable_color()
    
    # Log platform information
    logger.debug(f"Platform: {platform.platform()}")
    logger.debug(f"Python version: {platform.python_version()}")
    
    # Log dazzlelink availability
    if HAVE_DAZZLELINK:
        logger.debug("Dazzlelink integration is available")
    else:
        logger.debug("Dazzlelink integration is not available")
    
    # Log invocation
    logger.info(f"preserve {__version__} invoked with: {' '.join(sys.argv)}")
    
    # Check for required operation
    if not args.operation:
        parser.print_help()
        return 1
    
    # Handle operations
    try:
        if args.operation == 'COPY':
            return handle_copy_operation(args, logger)
        elif args.operation == 'MOVE':
            return handle_move_operation(args, logger)
        elif args.operation == 'VERIFY':
            return handle_verify_operation(args, logger)
        elif args.operation == 'RESTORE':
            return handle_restore_operation(args, logger)
        elif args.operation == 'CONFIG':
            return handle_config_operation(args, logger)
        else:
            logger.error(f"Unknown operation: {args.operation}")
            return 1
    except Exception as e:
        logger.exception(f"Error during {args.operation} operation")
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
