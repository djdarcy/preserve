#!/usr/bin/env python3
"""
preserve.py - Main entry point for the preserve file preservation tool.

This module serves as the orchestrator for the preserve application, coordinating
between the CLI, handlers, and core functionality.
"""

import os
import sys
import logging
import platform
from pathlib import Path

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

# Import from preserve package
from . import utils
from .cli import create_parser
from .handlers import (
    handle_copy_operation,
    handle_move_operation,
    handle_verify_operation,
    handle_restore_operation,
    handle_config_operation
)

# Import from preservelib for backward compatibility with tests
from preservelib import operations
from preservelib.manifest import find_available_manifests

# Export utilities for backward compatibility with tests
from .utils import (
    find_files_from_args,
    get_hash_algorithms,
    get_path_style,
    get_preserve_dir,
    get_manifest_path,
    get_dazzlelink_dir,
    _show_directory_help_message
)

# Version information
__version__ = "0.3.0"
__doc__ = """
preserve v0.3.0 - Cross-platform file preservation with verification and restoration

Examples:
    # Copy all files from a directory (most common usage)
    preserve COPY "C:/source/dir" --recursive --dst "D:/backup" --includeBase
    preserve COPY "C:/source/dir" -r --rel --dst "D:/backup"  # With relative paths

    # Copy files matching a glob pattern
    preserve COPY --glob "*.txt" --srchPath "C:/data" --rel --dst "E:/backup"

    # Move files with absolute path preservation
    preserve MOVE --glob "*.docx" --srchPath "C:/old" --abs --dst "D:/new"

    # Verify files in destination against sources
    preserve VERIFY --dst "E:/backup"

    # Restore files to original locations
    preserve RESTORE --src "E:/backup" --force

Note: For detailed help on each operation, use: preserve COPY --help
"""


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


def main():
    """Main entry point for the program"""
    # Parse command line arguments
    parser = create_parser()

    # Handle --help specially to provide examples
    if len(sys.argv) == 1 or '--help' in sys.argv or '-h' in sys.argv:
        args = parser.parse_args([]) if len(sys.argv) == 1 else parser.parse_args()
        parser.print_help()
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

    # Check for dazzlelink availability
    if utils.HAVE_DAZZLELINK:
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