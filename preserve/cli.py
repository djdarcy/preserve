"""
Command-line interface and argument parser for preserve tool.

This module contains all CLI-related functionality including
argument parsing, help text, and command structure definition.
"""

import argparse
from preserve import __version__
from preserve.version import get_base_version
from preserve.help import examples


def create_parser():
    """Create argument parser with all CLI options"""
    epilog_text = """Examples:
    # Copy entire directory with relative paths (most common usage)
    preserve COPY "C:/source/dir" --recursive --rel --includeBase --dst "D:/backup"

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

For more examples, use --help with a specific operation"""

    parser = argparse.ArgumentParser(
        prog='preserve',
        description=f'Preserve v{get_base_version()} - Cross-platform file preservation with verification and restoration',
        epilog=epilog_text,
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
                                       description='Copy files to destination with path preservation.',
                                       epilog='''Common usage patterns:

1. Copy entire directory with relative paths (most common):
   preserve COPY "C:\\source\\dir" --recursive --rel --includeBase --dst "D:\\backup"

2. Copy with absolute path structure:
   preserve COPY "C:\\source\\dir" --recursive --abs --includeBase --dst "D:\\backup"

3. Copy files flat (no subdirectories):
   preserve COPY "C:\\source\\dir" --recursive --flat --dst "D:\\backup"

4. Copy specific file types with pattern:
   preserve COPY --glob "*.jpg" --srchPath "C:\\photos" --recursive --rel --dst "D:\\backup"

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
                                       description='Move files to destination (copy then delete originals after verification).',
                                       epilog='''Common usage patterns:

1. Move entire directory with relative paths (most common):
   preserve MOVE "C:\\source\\dir" --recursive --rel --includeBase --dst "D:\\new-location"

2. Move with absolute path structure:
   preserve MOVE "C:\\source\\dir" --recursive --abs --includeBase --dst "D:\\new-location"

3. Move files flat (no subdirectories):
   preserve MOVE "C:\\source\\dir" --recursive --flat --dst "D:\\new-location"

4. Move specific file types with pattern:
   preserve MOVE --glob "*.docx" --srchPath "C:\\old" --recursive --rel --dst "D:\\new-location"

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
                                          epilog='''Examples:

1. Auto-verify everything (most common - finds source from manifest):
   preserve VERIFY --dst "D:/backup/data" --auto

2. Verify preserved files only (no source check):
   preserve VERIFY --dst "D:/backup/data"

3. Compare against specific source:
   preserve VERIFY --src "C:/original" --dst "D:/backup"

4. List available manifests:
   preserve VERIFY --dst "D:/backup/data" --list

5. Verify specific manifest:
   preserve VERIFY --dst "D:/backup/data" -n 2

6. Generate verification report:
   preserve VERIFY --dst "D:/backup" --report verify.txt''',
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    verify_parser.add_argument('--src',
                              help='Original source location to compare against (optional - compares preserved files vs source)')
    verify_parser.add_argument('--dst',
                              help='Path to preserved files directory containing manifest(s)')
    _add_verification_args(verify_parser)
    verify_parser.add_argument('--manifest', '-m',
                              help='Direct path to manifest file to use for verification')
    verify_parser.add_argument('--manifest-number', '--number', '-n', type=int,
                              help='Select manifest by number (e.g., -n 2 for preserve_manifest_002.json)')
    verify_parser.add_argument('--list', action='store_true',
                              help='Show all available manifests with details and exit')
    verify_parser.add_argument('--check', choices=['source', 'src', 'dest', 'dst', 'both', 'auto'],
                              help='What to verify: source, dest, both, or auto (default: dest if only --dst, both if --src provided)')
    verify_parser.add_argument('--auto', action='store_true',
                              help="Auto-detect source from manifest and verify what's available (shortcut for --check auto)")
    verify_parser.add_argument('--alt-src', action='append', metavar='PATH',
                              help='Additional source locations to check (can be specified multiple times)')
    verify_parser.add_argument('--report',
                              help='Save detailed verification report to file')
    _add_dazzlelink_args(verify_parser)

    # === RESTORE operation ===
    restore_parser = subparsers.add_parser('RESTORE',
                                          help='Restore preserved files back to their original locations',
                                          description='Restore preserved files back to their original locations based on the manifest.',
                                          epilog='''Examples:

1. Restore latest preservation:
   preserve RESTORE --src "D:/backup/data"

2. List available restore points:
   preserve RESTORE --src "D:/backup/data" --list

3. Restore specific manifest:
   preserve RESTORE --src "D:/backup/data" --number 2

4. Restore to different location:
   preserve RESTORE --src "D:/backup" --dst "C:/new/location"

5. Verify before restoring:
   preserve RESTORE --src "D:/backup" --verify

6. Dry run to see changes:
   preserve RESTORE --src "D:/backup" --dry-run''',
                                          formatter_class=argparse.RawDescriptionHelpFormatter)
    restore_parser.add_argument('--src',
                               help='Path to preserved files directory containing manifest')
    restore_parser.add_argument('--dst',
                               help='Optional destination path to restore to (defaults to original location)')
    restore_parser.add_argument('--manifest', '-m',
                               help='Direct path to manifest file to use for restoration')
    restore_parser.add_argument('--number', '-n', type=int,
                               help='Select manifest by number (e.g., -n 2 for preserve_manifest_002.json)')
    restore_parser.add_argument('--list', action='store_true',
                               help='Show all available restore points and exit')
    restore_parser.add_argument('--force', action='store_true',
                               help='Force overwrite existing files without prompting')
    restore_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be restored without making changes')
    restore_parser.add_argument('--verify', action='store_true',
                               help='Verify files before restoration (three-way comparison)')
    restore_parser.add_argument('--selective',
                               help='Only restore files matching pattern (e.g., "*.txt" or "path/to/*")')
    _add_dazzlelink_args(restore_parser)

    # === CONFIG operation ===
    config_parser = subparsers.add_parser('CONFIG',
                                         help='View or modify configuration settings',
                                         description='View or modify preserve configuration settings.',
                                         epilog='''Examples:

1. View all configuration:
   preserve CONFIG VIEW

2. View specific section:
   preserve CONFIG VIEW --section general

3. Set a value:
   preserve CONFIG SET general.verbose true

4. Reset to defaults:
   preserve CONFIG RESET

5. Reset specific section:
   preserve CONFIG RESET --section paths''',
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    config_subparsers = config_parser.add_subparsers(dest='config_operation', help='Configuration operation')

    # CONFIG VIEW
    view_parser = config_subparsers.add_parser('VIEW', help='View configuration')
    view_parser.add_argument('--section', help='View specific configuration section')

    # CONFIG SET
    set_parser = config_subparsers.add_parser('SET', help='Set configuration value')
    set_parser.add_argument('key', help='Configuration key (e.g., "general.verbose")')
    set_parser.add_argument('value', help='Value to set')

    # CONFIG RESET
    reset_parser = config_subparsers.add_parser('RESET', help='Reset configuration to defaults')
    reset_parser.add_argument('--section', help='Reset specific configuration section only')

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
    source_group.add_argument('--includeBase', action='store_true', help='Include source directory name in destination path')


def _add_destination_args(parser):
    """Add destination-related arguments to a parser"""
    dest_group = parser.add_argument_group('Destination options')
    dest_group.add_argument('--dst', required=True, help='Destination directory')
    dest_group.add_argument('--preserve-dir', action='store_true',
                           help='Create .preserve directory for manifests and metadata')
    dest_group.add_argument('--manifest', help='Custom manifest filename (default: preserve_manifest.json)')
    dest_group.add_argument('--no-manifest', action='store_true', help='Do not create a manifest file')


def _add_path_args(parser):
    """Add path preservation arguments to a parser"""
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--rel', action='store_true',
                      help='Preserve relative path structure (default if no path option specified)')
    group.add_argument('--abs', action='store_true',
                      help='Preserve absolute path structure')
    group.add_argument('--flat', action='store_true',
                      help='Flatten directory structure (no subdirectories)')
    parser.add_argument('--rel-base',
                       help='Base path for relative path calculation')


def _add_verification_args(parser):
    """Add verification-related arguments to a parser"""
    parser.add_argument('--hash', action='append',
                       choices=['MD5', 'SHA1', 'SHA256', 'SHA512'],
                       help='Hash algorithm(s) to use (can specify multiple, default: SHA256)')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip verification after operation')


def _add_dazzlelink_args(parser):
    """Add dazzlelink-related arguments to a parser"""
    parser.add_argument('--use-dazzlelinks', action='store_true',
                       help='Use dazzlelinks for verification if no manifest is found')
    parser.add_argument('--no-dazzlelinks', action='store_true',
                       help='Do not use dazzlelinks for verification')


def display_help_with_examples(parser, args):
    """Display help with examples for a specific operation"""
    if hasattr(args, 'operation') and args.operation:
        operation = args.operation
        parser.print_help()
        print("\n" + examples.get_operation_examples(operation))
    else:
        parser.print_help()
        print("\nFor more examples, use --help with a specific operation")