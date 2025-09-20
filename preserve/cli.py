"""
Command-line interface and argument parser for preserve tool.

This module contains all CLI-related functionality including
argument parsing, help text, and command structure definition.
"""

import argparse
from preserve import __version__, __doc__


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
                                                '  Generate verification report:    preserve VERIFY --dst /backup --report verify.txt')
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
                                          epilog='Examples:\n'
                                                '  Restore latest preservation:     preserve RESTORE --src /backup/data\n'
                                                '  List available restore points:   preserve RESTORE --src /backup/data --list\n'
                                                '  Restore specific manifest:       preserve RESTORE --src /backup/data --number 2\n'
                                                '  Restore to different location:   preserve RESTORE --src /backup --dst /new/location\n'
                                                '  Verify before restoring:         preserve RESTORE --src /backup --verify\n'
                                                '  Dry run to see changes:          preserve RESTORE --src /backup --dry-run')
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
                                         epilog='Examples:\n'
                                               '  View all configuration:          preserve CONFIG VIEW\n'
                                               '  View specific section:           preserve CONFIG VIEW --section general\n'
                                               '  Set a value:                     preserve CONFIG SET general.verbose true\n'
                                               '  Reset to defaults:               preserve CONFIG RESET\n'
                                               '  Reset specific section:          preserve CONFIG RESET --section paths')
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
    parser.add_argument('sources', nargs='*', metavar='SOURCE',
                       help='Source files or directories to process')
    parser.add_argument('--loadIncludes', '--load-includes',
                       help='Load list of sources from text file (one per line)')
    parser.add_argument('--glob',
                       help='Glob pattern to match files (e.g., "*.txt", "**/*.py")')
    parser.add_argument('--srchPath', '--search-path',
                       help='Base path to search for files when using --glob')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Include files from subdirectories')
    parser.add_argument('--includeBase', '--include-base', action='store_true',
                       help='Include the source directory name in destination path')


def _add_destination_args(parser):
    """Add destination-related arguments to a parser"""
    parser.add_argument('--dst', required=True,
                       help='Destination directory for preserved files')


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
    else:
        parser.print_help()