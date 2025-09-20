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
    # Copy all files from a directory (most common usage)
    preserve COPY "C:/source/dir" --recursive --dst "D:/backup" --includeBase
    preserve COPY "C:/source/dir" -r --rel --dst "D:/backup"  # With relative paths

    # Copy files matching a glob pattern
    preserve COPY --glob "*.txt" --srchPath "C:/data" --rel --dst "E:/backup"

    # Copy with hash verification
    preserve COPY --glob "*.jpg" --srchPath "D:/photos" --hash SHA256 --dst "E:/archive"

    # Move files with absolute path preservation
    preserve MOVE --glob "*.docx" --srchPath "C:/old" --abs --dst "D:/new"

    # Load a list of files to copy from a text file
    preserve COPY --loadIncludes "files_to_copy.txt" --dst "E:/backup"

    # Verify files in destination against sources
    preserve VERIFY --dst "E:/backup"

    # Restore files to original locations
    preserve RESTORE --src "E:/backup" --force

Note: For detailed help on each operation, use: preserve COPY --help
"""

import os
import sys
import argparse
import logging
import json
import datetime
import time
import platform
import re
from pathlib import Path
import importlib
from typing import List, Dict, Any, Optional, Union, Tuple

# Try to import colorama for colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)  # Initialize colorama for Windows support
    HAVE_COLOR = True
except ImportError:
    HAVE_COLOR = False
    # Define dummy color constants if colorama not available
    class Fore:
        RED = ''
        YELLOW = ''
        GREEN = ''
        CYAN = ''
        RESET = ''
    class Style:
        BRIGHT = ''
        RESET_ALL = ''

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
from .handlers import handle_verify_operation

# Import preservelib package
import preservelib
from preservelib import operations, metadata, restore, verification
from preservelib.manifest import PreserveManifest, find_available_manifests
#from preservelib.config import get_config

# Check for dazzlelink integration
try:
    import dazzlelink
    from preservelib import dazzlelink as preserve_dazzlelink
    HAVE_DAZZLELINK = preserve_dazzlelink.is_available()
except ImportError:
    # First try the bundled version if the pip-installed one is not available
    try:
        # Look for the bundled dazzlelink package
        import sys
        from pathlib import Path
        bundled_path = Path(__file__).parent.parent / 'dazzlelink'
        if bundled_path.exists() and str(bundled_path) not in sys.path:
            sys.path.insert(0, str(bundled_path))
        import dazzlelink
        from preservelib import dazzlelink as preserve_dazzlelink
        HAVE_DAZZLELINK = preserve_dazzlelink.is_available()
    except ImportError:
        HAVE_DAZZLELINK = False

# Import filetoolkit package
import filetoolkit
from filetoolkit import paths, operations as file_ops, verification

# Version information
__version__ = "0.3.0"

def setup_logging(args):
    """Set up logging based on verbosity level"""
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING

    # Get the root logger
    root_logger = logging.getLogger()

    # Remove all existing handlers from the root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure console handler for root logger
    console_handler = logging.StreamHandler()

    # Use simpler format for normal output, detailed format for verbose
    if args.verbose:
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    else:
        # Simple format with colors for normal output
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                # Disable colors if --no-color flag is set
                use_color = HAVE_COLOR and not getattr(args, 'no_color', False)

                if record.levelno == logging.INFO:
                    # INFO messages - no prefix, no color (clean output)
                    return record.getMessage()
                elif record.levelno == logging.WARNING:
                    if use_color:
                        return f"{Fore.YELLOW}{record.getMessage()}{Style.RESET_ALL}"
                    else:
                        return record.getMessage()
                elif record.levelno == logging.ERROR:
                    if use_color:
                        return f"{Fore.RED}{record.getMessage()}{Style.RESET_ALL}"
                    else:
                        return record.getMessage()
                elif record.levelno == logging.DEBUG:
                    if use_color:
                        return f"{Fore.CYAN}DEBUG: {record.getMessage()}{Style.RESET_ALL}"
                    else:
                        return f"DEBUG: {record.getMessage()}"
                else:
                    return f"{record.levelname}: {record.getMessage()}"

        console_handler.setFormatter(ColoredFormatter())

    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(log_level)
    
    # Configure a separate file handler if log file specified
    file_handler = None
    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # Configure package-level loggers with propagation=True
    # This ensures all logs go through the root logger
    # We'll only set the appropriate levels on each package logger
    for module_name in ['preserve', 'preservelib', 'preservelib.operations', 'preservelib.dazzlelink']:
        module_logger = logging.getLogger(module_name)
        
        # Remove any existing handlers to avoid duplication
        for handler in module_logger.handlers[:]:
            module_logger.removeHandler(handler)
            
        # Set proper level but let propagation work
        module_logger.setLevel(log_level)
        module_logger.propagate = True  # Ensure propagation is enabled
    
    # Get logger for this module to return
    logger = logging.getLogger('preserve')
    
    return logger

def create_parser():
    """Create argument parser with all CLI options"""
    parser = argparse.ArgumentParser(
        prog='preserve',
        description='Preserve v0.3.0 - Cross-platform file preservation with verification and restoration',
        epilog='For detailed command help: preserve [COMMAND] --help\n\n' + __doc__,
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
    copy_parser = subparsers.add_parser('COPY',
                                       help='Copy files to destination with path preservation',
                                       description='''Copy files to destination with path preservation.

Common usage patterns:

1. Copy all files from a directory (most common):
   preserve COPY "C:\\source\\dir" --recursive --dst "D:\\backup" --includeBase

2. Copy with relative path structure:
   preserve COPY "C:\\source\\dir" -r --rel --dst "D:\\backup"

3. Copy with absolute path structure:
   preserve COPY "C:\\source\\dir" -r --abs --dst "D:\\backup"

4. Copy files flat (no subdirectories):
   preserve COPY "C:\\source\\dir" -r --flat --dst "D:\\backup"

Note: When copying directories, --recursive (-r) is required to include files in subdirectories.
      Most users also want --includeBase to preserve the source directory name.''',
                                       formatter_class=argparse.RawDescriptionHelpFormatter)
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
    move_parser = subparsers.add_parser('MOVE',
                                       help='Copy files then remove originals after verification',
                                       description='''Move files to destination (copy then delete originals after verification).

Common usage patterns:

1. Move all files from a directory (most common):
   preserve MOVE "C:\\source\\dir" --recursive --dst "D:\\new-location" --includeBase

2. Move with relative path structure:
   preserve MOVE "C:\\source\\dir" -r --rel --dst "D:\\new-location"

3. Move with absolute path structure:
   preserve MOVE "C:\\source\\dir" -r --abs --dst "D:\\new-location"

4. Move files flat (no subdirectories):
   preserve MOVE "C:\\source\\dir" -r --flat --dst "D:\\new-location"

Note: When moving directories, --recursive (-r) is required to include files in subdirectories.
      Most users also want --includeBase to preserve the source directory name.
      Files are only deleted from source after successful verification.''',
                                       formatter_class=argparse.RawDescriptionHelpFormatter)
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
    verify_parser = subparsers.add_parser('VERIFY',
                                          help='Check integrity of preserved files against their manifest hashes',
                                          description='Verify that preserved files have not been corrupted or modified since preservation. '
                                                     'Compares current file hashes against those recorded in the manifest. '
                                                     'Does NOT check original source files unless --src is specified.',
                                          epilog='Examples:\n'
                                                '  Verify latest preservation:      preserve VERIFY --dst /backup/data\n'
                                                '  Verify specific manifest:        preserve VERIFY --dst /backup/data -n 2\n'
                                                '  List available manifests:        preserve VERIFY --dst /backup/data --list\n'
                                                '  Compare against source:          preserve VERIFY --src /original --dst /backup\n'
                                                '  Generate verification report:    preserve VERIFY --dst /backup --report verify.txt',
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    verify_parser.add_argument('--src', help='Original source location to compare against (optional - compares preserved files vs source)')
    verify_parser.add_argument('--dst', help='Path to preserved files directory containing manifest(s)')
    verify_parser.add_argument('--hash', action='append', choices=['MD5', 'SHA1', 'SHA256', 'SHA512'],
                              help='Hash algorithm(s) to use (can specify multiple, default: SHA256)')
    verify_parser.add_argument('--manifest', '-m', help='Direct path to manifest file to use for verification')
    verify_parser.add_argument('--manifest-number', '--number', '-n', type=int, dest='manifest_number',
                              help='Select manifest by number (e.g., -n 2 for preserve_manifest_002.json)')
    verify_parser.add_argument('--list', action='store_true',
                              help='Show all available manifests with details and exit')
    verify_parser.add_argument('--check',
                              choices=['source', 'src', 'dest', 'dst', 'both', 'auto'],
                              help='What to verify: source, dest, both, or auto (default: dest if only --dst, both if --src provided)')
    verify_parser.add_argument('--auto', action='store_true',
                              help='Auto-detect source from manifest and verify what\'s available (shortcut for --check auto)')
    verify_parser.add_argument('--alt-src', action='append', metavar='PATH',
                              help='Additional source locations to check (can be specified multiple times)')
    verify_parser.add_argument('--report', help='Save detailed verification report to file')
    verify_parser.add_argument('--use-dazzlelinks', action='store_true',
                              help='Use dazzlelinks for verification if no manifest is found')
    verify_parser.add_argument('--no-dazzlelinks', action='store_true',
                              help='Do not use dazzlelinks for verification')
    
    # === RESTORE operation ===
    restore_parser = subparsers.add_parser('RESTORE',
                                          help='Restore preserved files to their original locations',
                                          description='Restore files from a preservation directory back to their original paths. '
                                                     'Supports multiple preservation operations with numbered manifests. '
                                                     'Use --verify for three-way verification before restoration.',
                                          epilog='Examples:\n'
                                                '  Restore latest operation:        preserve RESTORE --src /backup/data\n'
                                                '  List available restore points:   preserve RESTORE --src /backup/data --list\n'
                                                '  Restore specific operation:      preserve RESTORE --src /backup/data -n 2\n'
                                                '  Verify before restore:           preserve RESTORE --src /backup/data --verify\n'
                                                '  Force overwrite existing:        preserve RESTORE --src /backup/data --force',
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    restore_parser.add_argument('--src', required=True, help='Directory containing preserved files and manifest(s)')
    restore_parser.add_argument('--manifest', help='Explicit path to manifest file (overrides automatic selection)')
    restore_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be restored without making changes')
    restore_parser.add_argument('--overwrite', action='store_true',
                               help='Overwrite existing files at destination (use with caution)')
    restore_parser.add_argument('--force', action='store_true',
                               help='Force restoration even if verification fails (bypasses --verify checks)')
    restore_parser.add_argument('--hash', action='append', choices=['MD5', 'SHA1', 'SHA256', 'SHA512'],
                               help='Hash algorithm(s) for verification (can specify multiple, default: SHA256)')
    restore_parser.add_argument('--use-dazzlelinks', action='store_true',
                               help='Use dazzlelinks for restoration if no manifest is found')
    restore_parser.add_argument('--no-dazzlelinks', action='store_true',
                               help='Do not use dazzlelinks for restoration')
    restore_parser.add_argument('--list', action='store_true',
                               help='Show all available restore points with details and exit')
    restore_parser.add_argument('--number', '-n', type=int,
                               help='Restore from specific operation number (e.g., -n 2 for second operation)')
    restore_parser.add_argument('--verify', action='store_true',
                               help='Perform three-way verification (source vs preserved vs manifest) before restoration. '
                                    'Categorizes differences and prompts for confirmation if issues found.')
    
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
    dazzle_group.add_argument('--dazzlelink-mode', choices=['info', 'open', 'auto'], default='info',
                             help='Default execution mode for dazzlelinks (default: info)')

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
        return 'absolute'  # Default to absolute for better preservation

def get_preserve_dir(args, dest_path):
    """Get preserve directory path"""
    if args.preserve_dir:
        preserve_dir = Path(dest_path) / '.preserve'
        preserve_dir.mkdir(parents=True, exist_ok=True)
        return preserve_dir
    return None

def get_manifest_path(args, preserve_dir):
    """Get manifest file path with sequential numbering support.

    This function implements a smart naming system:
    - First operation: creates preserve_manifest.json (backward compatible)
    - Second operation: renames first to _001, creates _002
    - Subsequent: creates _003, _004, etc.
    - Supports user descriptions: preserve_manifest_001__description.json
    """
    if args.no_manifest:
        return None

    if args.manifest:
        return Path(args.manifest)

    # Determine destination directory
    dest = preserve_dir if preserve_dir else Path(args.dst)
    single_manifest = dest / 'preserve_manifest.json'

    # Check if single manifest exists
    if single_manifest.exists():
        # Check if we also have numbered manifests
        numbered = list(dest.glob('preserve_manifest_[0-9][0-9][0-9]*.json'))
        if not numbered:
            # This is the second operation - migrate the single manifest
            new_001 = dest / 'preserve_manifest_001.json'
            print(f"Migrating {single_manifest.name} to {new_001.name}")
            try:
                single_manifest.rename(new_001)
                logger = logging.getLogger(__name__)
                logger.info(f"Migrated existing manifest to {new_001.name}")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to migrate manifest: {e}")
                # Fall back to creating _002 anyway
            return dest / 'preserve_manifest_002.json'

    # Look for existing numbered manifests
    pattern = re.compile(r'preserve_manifest_(\d{3})(?:__.*)?\.json')
    existing_numbers = []

    for file in dest.glob('preserve_manifest_*.json'):
        match = pattern.match(file.name)
        if match:
            existing_numbers.append(int(match.group(1)))

    # If no manifests exist at all, create the simple one
    if not existing_numbers and not single_manifest.exists():
        return single_manifest

    # Find the next sequential number
    if existing_numbers:
        next_num = max(existing_numbers) + 1
        return dest / f'preserve_manifest_{next_num:03d}.json'

    # Edge case: single manifest exists but couldn't be migrated
    # and no numbered manifests exist
    return dest / 'preserve_manifest_002.json'

# Function moved to preservelib.manifest for better organization

def get_dazzlelink_dir(args, preserve_dir):
    """
    Get dazzlelink directory path based on user options.
    
    This function determines where to store dazzlelink files based on
    user arguments. It respects the path preservation style (--abs, --rel, --flat)
    and properly structures the dazzlelink directory to mirror the destination.
    
    Args:
        args: Command-line arguments
        preserve_dir: Preserve directory path
        
    Returns:
        Path object for dazzlelink directory or None if not applicable
    """
    if not args.dazzlelink:
        return None
    
    if args.dazzlelink_with_files:
        return None  # Store alongside files
    
    # Base destination path
    dest_base = Path(args.dst)
    
    if args.dazzlelink_dir:
        # User specified a custom dazzlelink directory
        # Make it relative to the destination path
        custom_dir = args.dazzlelink_dir
        
        # If it's an absolute path, use it directly
        if Path(custom_dir).is_absolute():
            dl_dir = Path(custom_dir)
        else:
            # Otherwise, make it relative to the destination
            dl_dir = dest_base / custom_dir
            
        dl_dir.mkdir(parents=True, exist_ok=True)
        return dl_dir
    
    if preserve_dir:
        # Default to .preserve/dazzlelinks in the destination directory
        dl_dir = preserve_dir / 'dazzlelinks'
        dl_dir.mkdir(parents=True, exist_ok=True)
        return dl_dir
    
    # If no preserve directory, create .dazzlelinks in the destination
    dl_dir = dest_base / '.dazzlelinks'
    dl_dir.mkdir(parents=True, exist_ok=True)
    return dl_dir

def _show_directory_help_message(args, logger, src, operation="COPY", is_warning=False):
    """Show helpful message when directory is used without --recursive flag.

    Args:
        args: Command arguments
        logger: Logger instance
        src: Source directory path
        operation: Operation type (COPY or MOVE)
        is_warning: If True, show as warning. If False, show as error.
    """
    # Use generic destination in examples to avoid exposing real paths
    example_dst = "D:\\backup" if "\\" in str(args.dst) else "/backup"

    log_func = logger.warning if is_warning else logger.error
    action = "copied" if operation == "COPY" else "moved"

    if is_warning:
        log_func("")
        log_func(f"WARNING: '{src}' contains subdirectories with files that will NOT be {action}.")
        log_func("         Use --recursive flag to include files from subdirectories.")
    else:
        log_func("No source files found")
        log_func("")
        log_func(f"ERROR: '{src}' is a directory but --recursive flag was not specified.")
        log_func("       The directory may be empty or contain only subdirectories.")

    log_func("")
    log_func(f"To {operation.lower()} all files from a directory, use one of these commands:")
    log_func(f'  preserve {operation} "{src}" --recursive --dst "{example_dst}"')
    log_func(f'  preserve {operation} "{src}" -r --dst "{example_dst}"')
    log_func("")
    log_func("Additional options you may want:")
    log_func("  --includeBase : Include the source directory name in the destination")
    log_func("  --rel         : Preserve relative directory structure")
    log_func("  --abs         : Preserve absolute directory structure")

    if not is_warning:
        log_func("  --flat        : Copy all files directly to destination (no subdirectories)")
        log_func("")
        log_func("Example with common options:")
        log_func(f'  preserve {operation} "{src}" --recursive --rel --includeBase --dst "{example_dst}"')
    else:
        log_func("")


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

# handle_verify_operation is now imported from verify_handler module

def handle_restore_operation(args, logger):
    """Handle RESTORE operation with support for multiple manifests"""
    logger.info("Starting RESTORE operation")
    logger.debug(f"[DEBUG] RESTORE called with args: {args}")

    # Get source path
    source_path = Path(args.src)
    if not source_path.exists():
        logger.error(f"Source directory does not exist: {source_path}")
        return 1

    # Warning about hardcoded paths in the code
    source_name = source_path.name
    if source_name != 'dst2' and 'dst2' in str(source_path):
        print(f"\nNOTE: You're running RESTORE on directory '{source_name}', but the code might have some ")
        print(f"references to 'dst2'. If you encounter issues, please report this.")

    # Handle --list option to show available manifests
    if hasattr(args, 'list') and args.list:
        manifests = find_available_manifests(source_path)
        if not manifests:
            print("No manifests found in source directory")
            return 1

        print("Available restore points:")
        for num, path, desc in manifests:
            try:
                # Load manifest to get metadata
                test_man = PreserveManifest(path)
                created = test_man.manifest.get('created_at', 'Unknown')
                file_count = len(test_man.manifest.get('files', {}))

                if num == 0:
                    print(f"  [Single] {path.name} ({created}, {file_count} files)")
                else:
                    desc_str = f" - {desc}" if desc else ""
                    print(f"  {num}. {path.name}{desc_str} ({created}, {file_count} files)")
            except Exception as e:
                logger.debug(f"Could not read manifest {path}: {e}")
                if num == 0:
                    print(f"  [Single] {path.name} (unreadable)")
                else:
                    print(f"  {num}. {path.name} (unreadable)")

        print("\nUse --number N or -n N to restore from a specific operation")
        print("Use --manifest FILENAME to specify a manifest file directly")
        return 0

    # Select manifest based on user options
    manifest_path = None

    if args.manifest:
        # User specified manifest directly
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            # Try relative to source directory
            test_path = source_path / args.manifest
            if test_path.exists():
                manifest_path = test_path
    elif hasattr(args, 'number') and args.number:
        # User specified by number
        manifests = find_available_manifests(source_path)
        for num, path, desc in manifests:
            if num == args.number:
                manifest_path = path
                logger.info(f"Selected manifest #{num}: {path.name}")
                break
        else:
            logger.error(f"No manifest found with number {args.number}")
            return 1
    else:
        # Default: use the latest (highest numbered) manifest
        manifests = find_available_manifests(source_path)
        if manifests:
            # Take the last one (highest number)
            manifest_path = manifests[-1][1]
            logger.info(f"Using latest manifest: {manifest_path.name}")
        else:
            # Fall back to old logic for compatibility
            potential_manifests = [
                source_path / '.preserve' / 'manifest.json',
                source_path / '.preserve' / 'preserve_manifest.json',
                source_path / 'preserve_manifest.json'
            ]

            for path in potential_manifests:
                if path.exists():
                    manifest_path = path
                    break
    
    # Check for manifest
    if manifest_path and manifest_path.exists():
        try:
            # Just verify the manifest exists and is valid
            test_man = PreserveManifest(manifest_path)
            logger.info(f"Found valid manifest at {manifest_path}")
        except Exception as e:
            logger.warning(f"Found manifest at {manifest_path}, but it is invalid: {e}")
            manifest_path = None
    
    # Determine dazzlelink usage
    use_dazzlelinks = True  # Default is to use dazzlelinks if no manifest
    if args.no_dazzlelinks:
        use_dazzlelinks = False
    elif args.use_dazzlelinks:
        use_dazzlelinks = True
    
    # If no manifest and dazzlelinks disabled, report error
    if not manifest_path and not use_dazzlelinks:
        logger.error("No manifest found and dazzlelink usage is disabled")
        logger.error("Use --use-dazzlelinks to enable restoration from dazzlelinks")
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
        'force': args.force if hasattr(args, 'force') else False,
        'use_dazzlelinks': use_dazzlelinks
    }
    
    logger.debug(f"[DEBUG] RESTORE options: {options}")
    
    # Create command line for logging
    command_line = f"preserve RESTORE {' '.join(sys.argv[2:])}"

    # Perform three-way verification if requested
    if hasattr(args, 'verify') and args.verify and manifest_path:
        logger.info("Performing three-way verification before restoration...")

        # Load the manifest
        try:
            manifest = PreserveManifest(manifest_path)

            # Get source directory from manifest's first file
            files = manifest.manifest.get('files', {})
            if files:
                # Try to determine source directory from manifest entries
                first_file_info = next(iter(files.values()))
                source_orig_path = first_file_info.get('source_path', '')
                if source_orig_path:
                    source_orig = Path(source_orig_path)
                    # Try to find common parent of source files
                    if source_orig.is_absolute():
                        # For absolute paths, we need to find the actual source
                        logger.info(f"Source path from manifest: {source_orig}")
                        # Check if parent directories exist
                        possible_source = source_orig.parent
                        while not possible_source.exists() and possible_source.parent != possible_source:
                            possible_source = possible_source.parent
                        if possible_source.exists():
                            source_base = possible_source
                        else:
                            # Can't find source, skip three-way verification
                            logger.warning("Cannot determine source directory for three-way verification")
                            source_base = None
                    else:
                        # For relative paths, assume current directory
                        source_base = Path.cwd()
                else:
                    source_base = None
            else:
                source_base = None

            if source_base:
                from preservelib.verification import verify_three_way

                verification_result = verify_three_way(
                    source_path=source_base,
                    preserved_path=source_path,
                    manifest=manifest,
                    hash_algorithms=[options['hash_algorithm']]
                )

                # Report verification results
                print("\nThree-way Verification Results:")
                print(f"  All match: {len(verification_result.all_match)}")
                print(f"  Source modified: {len(verification_result.source_modified)}")
                print(f"  Preserved corrupted: {len(verification_result.preserved_corrupted)}")
                print(f"  Errors: {len(verification_result.errors)}")
                print(f"  Not found: {len(verification_result.not_found)}")

                # Show details if there are issues
                if verification_result.source_modified:
                    print("\nFiles modified in source since preservation:")
                    for result in verification_result.source_modified[:5]:
                        print(f"  - {result.file_path}")
                    if len(verification_result.source_modified) > 5:
                        print(f"  ... and {len(verification_result.source_modified) - 5} more")

                if verification_result.preserved_corrupted:
                    print("\nCorrupted preserved files:")
                    for result in verification_result.preserved_corrupted[:5]:
                        print(f"  - {result.file_path}")
                    if len(verification_result.preserved_corrupted) > 5:
                        print(f"  ... and {len(verification_result.preserved_corrupted) - 5} more")

                # Ask for confirmation if issues found
                if not verification_result.is_successful and not options['force']:
                    print("\nVerification found issues. Continue with restoration anyway? (use --force to skip this prompt)")
                    response = input("Continue? [y/N]: ").strip().lower()
                    if response != 'y':
                        print("Restoration cancelled.")
                        return 1
            else:
                logger.warning("Cannot perform three-way verification: source directory unknown")
                print("\nWarning: Three-way verification skipped (source directory not found)")

        except Exception as e:
            logger.warning(f"Could not perform three-way verification: {e}")
            print(f"\nWarning: Three-way verification failed: {e}")

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
    
    # Print detailed skipped file info
    if result.skip_count() > 0:
        print("\nSkipped Files (first 10):")
        skip_count = 0
        for source, dest in result.skipped:
            reason = result.error_messages.get(source, "Unknown reason")
            # Check if source file exists and show more details
            source_exists = Path(source).exists()
            print(f"  {source} -> {dest}")
            print(f"    Reason: {reason}")
            print(f"    Source exists: {source_exists}")
            if not source_exists:
                # Check if we can find the file in a subdirectory of the source
                source_dir = Path(args.src)
                filename = Path(source).name
                matching_files = list(source_dir.glob(f"**/{filename}"))
                if matching_files:
                    print(f"    Found similar files:")
                    for i, match in enumerate(matching_files[:3]):
                        print(f"      {match}")
                    if len(matching_files) > 3:
                        print(f"      ... and {len(matching_files) - 3} more")
                else:
                    print(f"    No similar files found")
            print("")
            skip_count += 1
            if skip_count >= 10:
                if result.skip_count() > 10:
                    print(f"  ... and {result.skip_count() - 10} more")
                break
    
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
