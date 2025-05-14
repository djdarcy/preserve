"""
Examples of using preserve.py for common file operations.

This module provides examples and recipes for common use cases
to help users effectively use the preserve tool.
"""

# Common examples for COPY operation
COPY_EXAMPLES = r"""
# Copy all text files from a directory with relative paths
preserve.py COPY --glob "*.txt" --srchPath "c:/data" --rel --dst "e:/backup"

# Copy files with absolute path preservation (drive letter as directory)
preserve.py COPY --glob "*.docx" --srchPath "c:/docs" --abs --dst "e:/archive"

# Copy specific files preserving relative paths
preserve.py COPY file1.txt file2.txt --rel --dst "e:/backup"

# Copy all PDF files and calculate SHA256 hashes for verification
preserve.py COPY --glob "*.pdf" --srchPath "d:/documents" --hash SHA256 --dst "e:/backup"

# Copy from multiple source paths
preserve.py COPY --srchPath "c:/data1" --srchPath "d:/data2" --glob "*.csv" --dst "e:/backup"

# Copy matching a regular expression instead of a glob pattern
preserve.py COPY --regex ".*\.jpe?g$" --srchPath "c:/photos" --dst "e:/images"

# Load a list of files to copy from a text file
preserve.py COPY --loadIncludes "files_to_copy.txt" --dst "e:/backup"

# Create Dazzlelinks to original files (useful for tracking origins)
preserve.py COPY --glob "*.mp4" --srchPath "d:/videos" --dazzlelink --dst "e:/media"

# Copy with a flat structure (all files directly in destination)
preserve.py COPY --glob "*.log" --srchPath "c:/logs" --flat --dst "e:/logs"

# Copy preserving only files modified in the last 7 days
preserve.py COPY --glob "*" --srchPath "c:/project" --newer-than 7d --dst "e:/backup"
"""

# Common examples for MOVE operation
MOVE_EXAMPLES = r"""
# Move all text files from a directory with relative paths
preserve.py MOVE --glob "*.txt" --srchPath "c:/old_data" --rel --dst "e:/new_data"

# Move files with absolute path preservation
preserve.py MOVE --glob "*.docx" --srchPath "c:/old_docs" --abs --dst "e:/archive"

# Move files preserving attributes and verifying with SHA256
preserve.py MOVE --glob "*.pdf" --srchPath "d:/old_docs" --hash SHA256 --dst "e:/new_docs"

# Move files but only remove source after verification
preserve.py MOVE --glob "*.csv" --srchPath "c:/data" --verify --dst "e:/backup"

# Move specific files from a list
preserve.py MOVE --loadIncludes "files_to_move.txt" --dst "e:/backup"

# Move files without preserving path structure (flat destination)
preserve.py MOVE --glob "*.jpg" --srchPath "c:/photos" --flat --dst "e:/images"
"""

# Common examples for VERIFY operation
VERIFY_EXAMPLES = r"""
# Verify files in a destination against stored hashes
preserve.py VERIFY --dst "e:/backup"

# Verify against source files with specific hash algorithm
preserve.py VERIFY --src "c:/original" --dst "e:/backup" --hash SHA256

# Verify using a specific manifest file
preserve.py VERIFY --dst "e:/backup" --manifest "path/to/manifest.json"

# Generate a verification report
preserve.py VERIFY --dst "e:/backup" --report "verification_report.txt"

# Verify only files matching a pattern
preserve.py VERIFY --dst "e:/backup" --glob "*.docx"
"""

# Common examples for RESTORE operation
RESTORE_EXAMPLES = r"""
# Restore files to their original locations
preserve.py RESTORE --src "e:/backup"

# Restore with verification and overwrite existing files
preserve.py RESTORE --src "e:/backup" --hash SHA256 --overwrite

# Dry run to see what would be restored without making changes
preserve.py RESTORE --src "e:/backup" --dry-run

# Restore from a specific manifest file
preserve.py RESTORE --src "e:/backup" --manifest "path/to/manifest.json"

# Force restoration even if verification fails
preserve.py RESTORE --src "e:/backup" --force
"""

# Configuration examples
CONFIG_EXAMPLES = r"""
# View all configuration settings
preserve.py CONFIG VIEW

# View specific configuration section
preserve.py CONFIG VIEW --section paths

# Set a configuration value
preserve.py CONFIG SET "paths.default_style" "relative"

# Reset configuration to defaults
preserve.py CONFIG RESET
"""

# Full examples of common workflows
WORKFLOW_EXAMPLES = r"""
# Backup workflow: copy files with verification and metadata
preserve.py COPY --glob "*.docx" --srchPath "c:/work" --hash SHA256 --preserve-dir --dst "e:/backup"

# Archive workflow: move files to organized structure with dazzlelinks
preserve.py MOVE --glob "*" --srchPath "c:/completed_projects" --dazzlelink --abs --dst "e:/archive"

# Verification workflow: check backed up files against originals
preserve.py VERIFY --src "c:/original" --dst "e:/backup" --hash SHA256 --report "backup_verification.txt"

# Disaster recovery: restore from backup to original locations
preserve.py RESTORE --src "e:/backup" --overwrite

# Incremental backup: copy only modified files
preserve.py COPY --glob "*" --srchPath "c:/data" --newer-than 7d --dst "e:/incremental_backup"
"""

def get_operation_examples(operation: str) -> str:
    """
    Get examples for a specific operation.
    
    Args:
        operation: Operation name (COPY, MOVE, VERIFY, RESTORE, CONFIG)
        
    Returns:
        Examples string for the specified operation
    """
    operation = operation.upper()
    
    if operation == 'COPY':
        return COPY_EXAMPLES
    elif operation == 'MOVE':
        return MOVE_EXAMPLES
    elif operation == 'VERIFY':
        return VERIFY_EXAMPLES
    elif operation == 'RESTORE':
        return RESTORE_EXAMPLES
    elif operation == 'CONFIG':
        return CONFIG_EXAMPLES
    elif operation == 'WORKFLOW':
        return WORKFLOW_EXAMPLES
    else:
        return "No examples available for this operation."

def get_all_examples() -> str:
    """
    Get all examples.
    
    Returns:
        String with all examples
    """
    return (
        "COPY Examples:\n" + COPY_EXAMPLES + "\n\n" +
        "MOVE Examples:\n" + MOVE_EXAMPLES + "\n\n" +
        "VERIFY Examples:\n" + VERIFY_EXAMPLES + "\n\n" +
        "RESTORE Examples:\n" + RESTORE_EXAMPLES + "\n\n" +
        "CONFIG Examples:\n" + CONFIG_EXAMPLES + "\n\n" +
        "Workflow Examples:\n" + WORKFLOW_EXAMPLES
    )

# Path explanations
PATH_HELP = r"""
Path Styles in preserve.py:

1. Relative Paths (--rel)
   Original: c:/data/docs/report.docx
   Destination with --srchPath "c:/data": e:/backup/docs/report.docx
   Destination with --includeBase: e:/backup/data/docs/report.docx

2. Absolute Paths (--abs)
   Original: c:/data/docs/report.docx
   Destination: e:/backup/c/data/docs/report.docx
   Note: Drive letter becomes a directory

3. Flat Structure (--flat)
   Original: c:/data/docs/report.docx, c:/data/images/logo.png
   Destination: e:/backup/report.docx, e:/backup/logo.png
   Note: All files are placed directly in the destination directory
"""

# Verification explanations
VERIFICATION_HELP = r"""
Verification in preserve.py:

1. Hash Algorithms
   --hash MD5       (Fast but less secure)
   --hash SHA1      (Faster than SHA256, reasonably secure)
   --hash SHA256    (Good balance of security and speed)
   --hash SHA512    (Most secure, but slower)
   
   You can specify multiple hash algorithms:
   --hash MD5 --hash SHA256

2. Verification Options
   --verify         Verify files after operation
   --no-verify      Skip verification (faster but less safe)
   --checksum-file  Write checksums to a file for later verification
"""

# Dazzlelink explanations
DAZZLELINK_HELP = r"""
Dazzlelink Integration in preserve.py:

Dazzlelinks are special files that preserve information about the original source
of a file. They're useful for tracking origins and enabling easy restoration.

1. Creating Dazzlelinks
   --dazzlelink              Create dazzlelinks to original files
   --dazzlelink-dir DIR      Store dazzlelinks in a specific directory
   --dazzlelink-with-files   Store dazzlelinks alongside copied files

2. Using Dazzlelinks
   Dazzlelinks contain metadata about the original file, including:
   - Original path
   - Timestamps
   - Attributes
   - Size

3. Benefits
   - Easy tracking of file origins
   - Simplified restoration process
   - Enhanced metadata preservation
"""

def get_help_topic(topic: str) -> str:
    """
    Get help text for a specific topic.
    
    Args:
        topic: Topic name (PATH, VERIFICATION, DAZZLELINK)
        
    Returns:
        Help text for the specified topic
    """
    topic = topic.upper()
    
    if topic == 'PATH':
        return PATH_HELP
    elif topic == 'VERIFICATION':
        return VERIFICATION_HELP
    elif topic == 'DAZZLELINK':
        return DAZZLELINK_HELP
    else:
        return "No help available for this topic."
