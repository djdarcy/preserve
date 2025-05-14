"""
Utility functions for the preserve command-line tool.

This module provides utility functions for the preserve CLI, including
formatting, colorization, progress reporting, and path operations.
"""

import os
import sys
import time
import json
import logging
import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable, TextIO

# Constants for terminal colors
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m'
}

# Set up module-level logger
logger = logging.getLogger(__name__)

# Flag to indicate if color is enabled
color_enabled = True

def disable_color():
    """Disable colored output."""
    global color_enabled
    color_enabled = False

def enable_color():
    """Enable colored output."""
    global color_enabled
    color_enabled = True

def colorize(text: str, color: str) -> str:
    """
    Add color to text for terminal output.
    
    Args:
        text: The text to colorize
        color: The color to apply (must be a key in COLORS dict)
        
    Returns:
        Colorized string if color is enabled, otherwise the original string
    """
    if not color_enabled or color not in COLORS:
        return text
    
    return f"{COLORS[color]}{text}{COLORS['RESET']}"

def parse_time_spec(time_spec: str) -> float:
    """
    Parse a time specification into a timestamp.
    
    Supports:
    - ISO format dates (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    - Relative times (Nd, Nh, Nm, Ns where N is a number)
    
    Args:
        time_spec: Time specification string
        
    Returns:
        Timestamp as seconds since epoch
    """
    # Check for relative time format
    relative_pattern = re.compile(r'^(\d+)([dhms])$')
    match = relative_pattern.match(time_spec)
    
    if match:
        value, unit = match.groups()
        value = int(value)
        now = time.time()
        
        if unit == 'd':
            # Days
            return now - (value * 86400)
        elif unit == 'h':
            # Hours
            return now - (value * 3600)
        elif unit == 'm':
            # Minutes
            return now - (value * 60)
        elif unit == 's':
            # Seconds
            return now - value
    
    # Check for ISO format date
    try:
        # Try full ISO format with time
        dt = datetime.datetime.fromisoformat(time_spec)
        return dt.timestamp()
    except ValueError:
        try:
            # Try just date
            dt = datetime.datetime.strptime(time_spec, '%Y-%m-%d')
            return dt.timestamp()
        except ValueError:
            raise ValueError(f"Invalid time specification: {time_spec}")

def format_path(path: Union[str, Path], relative_to: Optional[Union[str, Path]] = None) -> str:
    """
    Format a path for display, optionally making it relative to another path.
    
    Args:
        path: The path to format
        relative_to: Path to make the path relative to (optional)
        
    Returns:
        Formatted path string
    """
    path_obj = Path(path)
    
    if relative_to:
        relative_to_path = Path(relative_to)
        try:
            return str(path_obj.relative_to(relative_to_path))
        except ValueError:
            # Can't make relative, use absolute path
            return str(path_obj)
    
    return str(path_obj)

def format_size(size_bytes: int) -> str:
    """
    Format a size in bytes to a human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def format_timestamp(timestamp: float) -> str:
    """
    Format a timestamp as a human-readable string.
    
    Args:
        timestamp: The timestamp to format
        
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return "Unknown"
    
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(timestamp)

def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def print_progress(current: int, total: int, prefix: str = '', suffix: str = '', 
                  bar_length: int = 50, file: Any = sys.stdout):
    """
    Print a progress bar.
    
    Args:
        current: Current progress value
        total: Total value for 100% progress
        prefix: String to print before the progress bar
        suffix: String to print after the progress bar
        bar_length: Length of the progress bar in characters
        file: File to print to (default: sys.stdout)
    """
    if total == 0:
        percentage = 100
    else:
        percentage = int(100 * (current / total))
    
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    # Use carriage return to overwrite the line
    file.write(f'\r{prefix} |{bar}| {percentage}% {suffix}')
    file.flush()
    
    # Print a newline when we're done
    if current == total:
        file.write('\n')

class ProgressTracker:
    """
    Track progress of a multi-file operation.
    
    This class can be used to track both file count and byte count progress
    and display progress bars or summaries.
    """
    
    def __init__(self, total_files: int = 0, total_bytes: int = 0, show_progress: bool = True):
        """
        Initialize a progress tracker.
        
        Args:
            total_files: Total number of files to process
            total_bytes: Total number of bytes to process
            show_progress: Whether to show progress bars
        """
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.processed_files = 0
        self.processed_bytes = 0
        self.successful_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.start_time = time.time()
        self.show_progress = show_progress
        self.last_update_time = 0
        self.update_interval = 0.1  # Seconds between progress updates
    
    def start(self):
        """Start or reset the progress tracker."""
        self.processed_files = 0
        self.processed_bytes = 0
        self.successful_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.start_time = time.time()
        self.last_update_time = 0
    
    def update(self, file_count: int = 0, byte_count: int = 0, success: bool = True, 
             skipped: bool = False, force_display: bool = False):
        """
        Update progress.
        
        Args:
            file_count: Number of additional files processed
            byte_count: Number of additional bytes processed
            success: Whether the files were processed successfully
            skipped: Whether the files were skipped
            force_display: Whether to force display update even if interval hasn't elapsed
        """
        self.processed_files += file_count
        self.processed_bytes += byte_count
        
        if success and not skipped:
            self.successful_files += file_count
        elif skipped:
            self.skipped_files += file_count
        else:
            self.failed_files += file_count
        
        # Limit updates to avoid excessive display refreshing
        current_time = time.time()
        if force_display or (current_time - self.last_update_time >= self.update_interval):
            self.last_update_time = current_time
            self.display_progress()
    
    def display_progress(self):
        """Display the current progress."""
        if not self.show_progress:
            return
        
        elapsed = time.time() - self.start_time
        
        # Calculate speed
        if elapsed > 0:
            files_per_second = self.processed_files / elapsed
            bytes_per_second = self.processed_bytes / elapsed
        else:
            files_per_second = 0
            bytes_per_second = 0
        
        # Calculate ETA
        if self.total_files > 0 and files_per_second > 0:
            eta_seconds = (self.total_files - self.processed_files) / files_per_second
            eta = format_duration(eta_seconds)
        else:
            eta = "Unknown"
        
        # File progress
        file_prefix = f"Files: {self.processed_files}/{self.total_files}"
        file_suffix = f"ETA: {eta}"
        print_progress(self.processed_files, self.total_files, prefix=file_prefix, suffix=file_suffix)
        
        # For byte progress, only show if we know the total
        if self.total_bytes > 0:
            bytes_prefix = f"Bytes: {format_size(self.processed_bytes)}/{format_size(self.total_bytes)}"
            bytes_suffix = f"Speed: {format_size(bytes_per_second)}/s"
            print_progress(self.processed_bytes, self.total_bytes, prefix=bytes_prefix, suffix=bytes_suffix)
    
    def summarize(self) -> Dict[str, Any]:
        """
        Summarize the progress.
        
        Returns:
            Dictionary with progress summary
        """
        elapsed = time.time() - self.start_time
        
        # Calculate speed
        if elapsed > 0:
            files_per_second = self.processed_files / elapsed
            bytes_per_second = self.processed_bytes / elapsed
        else:
            files_per_second = 0
            bytes_per_second = 0
        
        return {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'skipped_files': self.skipped_files,
            'total_bytes': self.total_bytes,
            'processed_bytes': self.processed_bytes,
            'elapsed_time': elapsed,
            'elapsed_formatted': format_duration(elapsed),
            'files_per_second': files_per_second,
            'bytes_per_second': bytes_per_second,
            'bytes_per_second_formatted': format_size(bytes_per_second) + '/s'
        }
    
    def display_summary(self, title: str = 'Operation Summary'):
        """
        Display a summary of the progress.
        
        Args:
            title: Title for the summary
        """
        summary = self.summarize()
        
        print(f"\n{colorize(title, 'BOLD')}:")
        print(f"  Total files: {summary['total_files']}")
        print(f"  Processed:   {summary['processed_files']}")
        print(f"  Successful:  {colorize(str(summary['successful_files']), 'GREEN')}")
        print(f"  Failed:      {colorize(str(summary['failed_files']), 'RED')}")
        print(f"  Skipped:     {colorize(str(summary['skipped_files']), 'YELLOW')}")
        print(f"  Total bytes: {format_size(summary['total_bytes'])}")
        print(f"  Elapsed:     {summary['elapsed_formatted']}")
        print(f"  Speed:       {summary['bytes_per_second_formatted']}")

def save_json(data: Any, file_path: Union[str, Path], pretty: bool = True) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save to
        pretty: Whether to format the JSON for human readability
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create parent directory if it doesn't exist
        path_obj = Path(file_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
        
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

def load_json(file_path: Union[str, Path]) -> Optional[Any]:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to load from
        
    Returns:
        Loaded data, or None if loading failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None

def confirm_operation(prompt: str, default: bool = False) -> bool:
    """
    Ask the user to confirm an operation.
    
    Args:
        prompt: The prompt to display
        default: Default choice if user presses Enter
        
    Returns:
        True if user confirmed, False otherwise
    """
    yes_choices = ['y', 'yes', 'true', '1']
    no_choices = ['n', 'no', 'false', '0']
    
    if default:
        yes_choices.append('')
        prompt += " [Y/n] "
    else:
        no_choices.append('')
        prompt += " [y/N] "
    
    while True:
        try:
            response = input(prompt).lower()
            if response in yes_choices:
                return True
            elif response in no_choices:
                return False
            else:
                print("Please answer with 'y' or 'n'.")
        except (KeyboardInterrupt, EOFError):
            print()
            return False

def plural(count: int, singular: str, plural: str) -> str:
    """
    Return singular or plural form based on count.
    
    Args:
        count: Count determining singular or plural
        singular: Singular form
        plural: Plural form
        
    Returns:
        Singular or plural form based on count
    """
    return singular if count == 1 else plural

def safe_delete(path: Union[str, Path]) -> bool:
    """
    Safely delete a file or directory.
    
    Args:
        path: Path to delete
        
    Returns:
        True if successful, False otherwise
    """
    path_obj = Path(path)
    
    try:
        if path_obj.is_dir():
            import shutil
            shutil.rmtree(path_obj)
        else:
            path_obj.unlink()
        
        return True
    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return False

def get_terminal_size() -> Dict[str, int]:
    """
    Get the terminal size.
    
    Returns:
        Dictionary with 'columns' and 'lines' keys
    """
    try:
        columns, lines = os.get_terminal_size()
        return {'columns': columns, 'lines': lines}
    except (AttributeError, OSError):
        # Default values if we can't determine the terminal size
        return {'columns': 80, 'lines': 24}

def find_command(command: str) -> Optional[str]:
    """
    Find the full path to a command in PATH.
    
    Args:
        command: Command name to find
        
    Returns:
        Full path to the command, or None if not found
    """
    # If we're on Windows and no extension was provided, we need to check for .exe, .cmd, etc.
    if os.name == 'nt' and not command.lower().endswith(('.exe', '.bat', '.cmd')):
        exts = os.environ.get('PATHEXT', '').split(os.pathsep)
        possible_cmds = [command + ext for ext in exts]
    else:
        possible_cmds = [command]
    
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        path_dir = path_dir.strip('"')
        for cmd in possible_cmds:
            cmd_path = os.path.join(path_dir, cmd)
            if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
                return cmd_path
    
    return None

def truncate_path(path: Union[str, Path], max_length: int = 40) -> str:
    """
    Truncate a path to a maximum length, preserving the filename.
    
    Args:
        path: Path to truncate
        max_length: Maximum length
        
    Returns:
        Truncated path
    """
    path_str = str(path)
    
    if len(path_str) <= max_length:
        return path_str
    
    # Get the filename and directory
    path_obj = Path(path)
    filename = path_obj.name
    directory = path_str[:-len(filename)]
    
    # If the filename itself is too long, truncate it
    if len(filename) > max_length - 4:  # Allow space for ".../"
        return ".../" + filename[:max_length - 4]
    
    # Calculate how much of the directory we can keep
    avail_len = max_length - len(filename) - 4  # Allow space for ".../", "/"
    if avail_len <= 0:
        return ".../" + filename
    
    return ".../" + directory[-avail_len:] + filename

def join_paths(*paths: Union[str, Path]) -> Path:
    """
    Join paths in a cross-platform way.
    
    Args:
        *paths: Path components to join
        
    Returns:
        Joined path
    """
    result = Path(paths[0])
    for path in paths[1:]:
        result = result / path
    return result

def is_within_directory(path: Union[str, Path], directory: Union[str, Path]) -> bool:
    """
    Check if a path is within a directory.
    
    Args:
        path: Path to check
        directory: Directory to check against
        
    Returns:
        True if path is within directory, False otherwise
    """
    path_obj = Path(path).resolve()
    directory_obj = Path(directory).resolve()
    
    try:
        path_obj.relative_to(directory_obj)
        return True
    except ValueError:
        return False
