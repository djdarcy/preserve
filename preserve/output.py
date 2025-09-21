"""
Output formatting utilities for preserve operations.

This module provides consistent, color-coded output formatting across all operations
with support for multiple verbosity levels.
"""

import os
import sys
from enum import IntEnum
from typing import Optional, Dict, Any
import logging

# Try to import colorama for Windows color support
try:
    from colorama import init as colorama_init, Fore, Style
    COLORAMA_AVAILABLE = True
    # Initialize colorama for Windows
    colorama_init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color definitions (no-op)
    class Fore:
        GREEN = ''
        RED = ''
        YELLOW = ''
        BLUE = ''
        WHITE = ''
        CYAN = ''
        RESET = ''
    class Style:
        BRIGHT = ''
        DIM = ''
        RESET_ALL = ''

logger = logging.getLogger(__name__)


class VerbosityLevel(IntEnum):
    """Verbosity levels for output control."""
    QUIET = -1      # Suppress all but errors
    NORMAL = 0      # Default - summary only
    VERBOSE = 1     # Show important operations
    DETAILED = 2    # Show all operations
    DEBUG = 3       # Show debug information


class OutputFormatter:
    """Handles formatted output for preserve operations."""

    # Status symbols (with fallback for Windows without Unicode)
    SYMBOLS = {
        'success': '✓',
        'skip': '⊖',
        'warning': '⚠',
        'error': '✗',
        'info': 'ℹ',
        'progress': '→',
        # Fallback ASCII symbols
        'success_ascii': '[OK]',
        'skip_ascii': '[--]',
        'warning_ascii': '[!!]',
        'error_ascii': '[XX]',
        'info_ascii': '[i]',
        'progress_ascii': '=>',
    }

    def __init__(self, verbosity: int = 0, use_color: bool = True, use_unicode: bool = True):
        """
        Initialize the output formatter.

        Args:
            verbosity: Verbosity level (0-3)
            use_color: Whether to use colored output
            use_unicode: Whether to use Unicode symbols
        """
        self.verbosity = verbosity
        self.use_color = use_color and COLORAMA_AVAILABLE and not self._is_output_redirected()
        self.use_unicode = use_unicode and self._supports_unicode()

        # File counters for summary
        self.counters = {
            'total': 0,
            'success': 0,
            'skip': 0,
            'warning': 0,
            'error': 0
        }

        # Track if we've shown progress
        self.last_was_progress = False

    def _is_output_redirected(self) -> bool:
        """Check if output is being redirected/piped."""
        return not sys.stdout.isatty()

    def _supports_unicode(self) -> bool:
        """Check if the terminal supports Unicode."""
        # Check if output is redirected
        if self._is_output_redirected():
            return False

        # Check Windows console
        if sys.platform == 'win32':
            # Windows 10+ generally supports Unicode
            try:
                import locale
                return 'utf' in locale.getpreferredencoding().lower()
            except:
                return False

        # Unix-like systems usually support Unicode
        return True

    def _get_symbol(self, symbol_type: str) -> str:
        """Get the appropriate symbol based on Unicode support."""
        if self.use_unicode:
            return self.SYMBOLS.get(symbol_type, '')
        else:
            # Use ASCII fallback
            ascii_key = f"{symbol_type}_ascii"
            return self.SYMBOLS.get(ascii_key, self.SYMBOLS.get(symbol_type, ''))

    def _colorize(self, text: str, color: str = '') -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_color or not color:
            return text
        return f"{color}{text}{Style.RESET_ALL}"

    def format_restore_status(self, status: str, file_path: str,
                             reason: Optional[str] = None,
                             current: Optional[int] = None,
                             total: Optional[int] = None) -> Optional[str]:
        """
        Format a restore operation status message.

        Args:
            status: One of 'success', 'skip', 'warning', 'error'
            file_path: The file being processed
            reason: Optional reason for skip/error
            current: Current file number
            total: Total number of files

        Returns:
            Formatted string or None if should not be displayed at current verbosity
        """
        # Update counters
        self.counters['total'] = max(self.counters['total'], total or 0)
        if status in self.counters:
            self.counters[status] += 1

        # Determine what to show based on verbosity
        if self.verbosity <= VerbosityLevel.QUIET and status != 'error':
            return None

        if self.verbosity == VerbosityLevel.NORMAL:
            # Only show errors and warnings at normal verbosity
            if status not in ('error', 'warning'):
                return None

        # Build the message
        parts = []

        # Add progress counter if available
        if current and total and self.verbosity >= VerbosityLevel.DETAILED:
            parts.append(f"[{current}/{total}]")

        # Add status symbol and label
        symbol = self._get_symbol(status)
        if status == 'success':
            status_text = self._colorize(f"{symbol} Restored", Fore.GREEN)
        elif status == 'skip':
            status_text = self._colorize(f"{symbol} Skipped", Style.DIM)
        elif status == 'warning':
            status_text = self._colorize(f"{symbol} Warning", Fore.YELLOW)
        elif status == 'error':
            status_text = self._colorize(f"{symbol} Failed", Fore.RED)
        else:
            status_text = f"{symbol} {status.capitalize()}"

        parts.append(status_text)

        # Add file path
        if self.verbosity >= VerbosityLevel.DETAILED:
            # Show full path at higher verbosity
            parts.append(file_path)
        else:
            # Show just filename at lower verbosity
            parts.append(os.path.basename(file_path))

        # Add reason if provided
        if reason:
            if self.verbosity >= VerbosityLevel.VERBOSE:
                parts.append(f"({reason})")
            elif status == 'error':
                # Always show error reasons
                parts.append(f"- {reason}")

        # Clear progress line if needed
        if self.last_was_progress:
            # Clear the line
            message = '\r' + ' ' * 80 + '\r'
            self.last_was_progress = False
        else:
            message = ''

        message += ' '.join(parts)
        return message

    def format_progress(self, current: int, total: int, operation: str = "Processing") -> str:
        """
        Format a progress message.

        Args:
            current: Current item number
            total: Total items
            operation: Operation being performed

        Returns:
            Formatted progress string
        """
        if self.verbosity <= VerbosityLevel.QUIET:
            return None

        self.last_was_progress = True
        percent = (current * 100) // total if total > 0 else 0

        # Build progress bar
        bar_width = 30
        filled = (bar_width * current) // total if total > 0 else 0
        bar = '█' * filled + '░' * (bar_width - filled)

        if self.use_color:
            bar = self._colorize(bar, Fore.CYAN)

        # Use \r to overwrite the line
        return f"\r{operation}: [{bar}] {percent}% ({current}/{total})"

    def format_summary(self, operation: str = "Operation") -> str:
        """
        Format a summary of the operation.

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(f"\n{operation} Summary:")

        if self.counters['total'] > 0:
            lines.append(f"  Total files: {self.counters['total']}")

        if self.counters['success'] > 0:
            success_text = f"  {self._get_symbol('success')} Restored: {self.counters['success']} files"
            lines.append(self._colorize(success_text, Fore.GREEN))

        if self.counters['skip'] > 0:
            skip_text = f"  {self._get_symbol('skip')} Skipped: {self.counters['skip']} files"
            lines.append(self._colorize(skip_text, Style.DIM))

        if self.counters['warning'] > 0:
            warning_text = f"  {self._get_symbol('warning')} Warnings: {self.counters['warning']} files"
            lines.append(self._colorize(warning_text, Fore.YELLOW))

        if self.counters['error'] > 0:
            error_text = f"  {self._get_symbol('error')} Failed: {self.counters['error']} files"
            lines.append(self._colorize(error_text, Fore.RED))

        return '\n'.join(lines)

    def format_header(self, message: str) -> str:
        """Format a header message."""
        if self.verbosity <= VerbosityLevel.QUIET:
            return None
        return self._colorize(message, Style.BRIGHT)

    def format_error(self, message: str) -> str:
        """Format an error message (always shown)."""
        return self._colorize(f"{self._get_symbol('error')} Error: {message}", Fore.RED)

    def format_warning(self, message: str) -> str:
        """Format a warning message."""
        if self.verbosity <= VerbosityLevel.QUIET:
            return None
        return self._colorize(f"{self._get_symbol('warning')} Warning: {message}", Fore.YELLOW)

    def format_info(self, message: str) -> str:
        """Format an info message."""
        if self.verbosity < VerbosityLevel.VERBOSE:
            return None
        return f"{self._get_symbol('info')} {message}"

    def format_debug(self, message: str) -> str:
        """Format a debug message."""
        if self.verbosity < VerbosityLevel.DEBUG:
            return None
        return self._colorize(f"[DEBUG] {message}", Style.DIM)

    def should_show_individual_files(self) -> bool:
        """Check if individual file operations should be shown."""
        return self.verbosity >= VerbosityLevel.VERBOSE

    def reset_counters(self):
        """Reset all counters for a new operation."""
        self.counters = {
            'total': 0,
            'success': 0,
            'skip': 0,
            'warning': 0,
            'error': 0
        }
        self.last_was_progress = False


# Global formatter instance (can be configured by CLI)
_global_formatter = None

def get_formatter() -> OutputFormatter:
    """Get the global output formatter instance."""
    global _global_formatter
    if _global_formatter is None:
        _global_formatter = OutputFormatter()
    return _global_formatter

def set_formatter(formatter: OutputFormatter):
    """Set the global output formatter instance."""
    global _global_formatter
    _global_formatter = formatter

def configure_formatter(verbosity: int = 0, use_color: bool = True, use_unicode: bool = True):
    """Configure the global formatter with new settings."""
    global _global_formatter
    _global_formatter = OutputFormatter(verbosity, use_color, use_unicode)
    return _global_formatter