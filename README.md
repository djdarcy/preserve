# Preserve

[![Version](https://img.shields.io/github/v/release/djdarcy/preserve)](https://github.com/djdarcy/preserve/releases)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](https://www.gnu.org/licenses/gpl-3.0.html)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

A cross-platform file preservation tool with path normalization, verification, and restoration capabilities.

## Features

- **Path Preservation**: Copy or move files with multiple path preservation styles:
  - Relative paths that maintain directory structure (`--rel`)
  - Absolute paths with drive letter preservation (`--abs`)
  - Flat structure with all files in one directory (`--flat`)
- **Verification**: File integrity verification with multiple hash algorithms (MD5, SHA1, SHA256, SHA512)
- **Metadata**: Preserve file attributes (timestamps, permissions, etc.)
- **Manifests**: Detailed operation tracking with automatic versioning for multiple operations
- **Restoration**: Restore files to their original locations with verification
- **DazzleLink**: Optional integration with dazzlelink for enhanced metadata storage and file references
- **Cross-Platform**: Works on Windows, Linux, and macOS

## Installation

```bash
pip install preserve
```

For full functionality on Windows, install with the Windows extras:

```bash
pip install preserve[windows]
```

For [dazzlelink](https://github.com/djdarcy/dazzlelink) integration:

```bash
pip install preserve[dazzlelink]
```

## Usage

### Basic Usage

Copy files with relative path preservation (from a file list):

```bash
preserve COPY --loadIncludes "files-to-copy.txt" --dst "e:/backup" --rel --dazzlelink --includeBase
```

Or (search the source directory for files):,

```bash
preserve COPY --glob "*.txt" --srchPath "c:/data" --rel --dst "e:/backup"
```

Move files with absolute path preservation:

```bash
preserve MOVE --glob "*.docx" --srchPath "c:/old" --abs --dst "d:/new"
```

Verify files against their source:

```bash
preserve VERIFY --src "c:/original" --dst "e:/backup" --hash SHA256
```

Restore files to their original locations:

```bash
# Restore latest operation (default)
preserve RESTORE --src "e:/backup"

# List all available restore points
preserve RESTORE --src "e:/backup" --list

# Restore specific operation by number
preserve RESTORE --src "e:/backup" --number 1

# Force overwrite during restore
preserve RESTORE --src "e:/backup" --force
```

### Path Preservation Options

- `--rel`: Preserve relative paths
- `--abs`: Preserve absolute paths (with drive letter as directory)
- `--flat`: Flatten directory structure (all files in destination root)
- `--includeBase`: Include base directory name in destination path

### Other Options

- `--hash`: Specify hash algorithm(s) for verification (MD5, SHA1, SHA256, SHA512)
- `--verify`: Verify files after operation
- `--dazzlelink`: Create dazzlelinks to original files
- `--dry-run`: Show what would be done without making changes
- `--overwrite`: Overwrite existing files in destination

See `preserve --help` for full documentation and examples.

## Working with Multiple Operations

Preserve automatically manages manifests when you run multiple operations to the same destination:

### Sequential Operations Example

```bash
# First operation - copies dataset A
preserve COPY "C:/data/dataset-A" -r --includeBase --rel --dst "E:/backup"
# Creates: preserve_manifest.json

# Second operation - copies dataset B
preserve COPY "C:/data/dataset-B" -r --includeBase --rel --dst "E:/backup"
# Auto-migrates first manifest to preserve_manifest_001.json
# Creates: preserve_manifest_002.json

# Third operation - copies dataset C
preserve COPY "C:/data/dataset-C" -r --includeBase --rel --dst "E:/backup"
# Creates: preserve_manifest_003.json
```

### Managing Multiple Manifests

```bash
# List all available restore points
preserve RESTORE --src "E:/backup" --list
# Output:
#   1. preserve_manifest_001.json (2025-09-18 14:30:00, 150 files)
#   2. preserve_manifest_002.json (2025-09-18 14:55:00, 75 files)
#   3. preserve_manifest_003.json (2025-09-18 15:20:00, 200 files)

# Restore specific dataset (e.g., dataset B from operation 2)
preserve RESTORE --src "E:/backup" --number 2

# Restore latest operation (dataset C)
preserve RESTORE --src "E:/backup"

# Restore with short option
preserve RESTORE --src "E:/backup" -n 1  # Restores dataset A
```

### User-Friendly Manifest Naming

You can rename manifests to include descriptions:

```bash
# Rename manifests for clarity (Windows)
ren preserve_manifest_001.json preserve_manifest_001__dataset-A.json
ren preserve_manifest_002.json preserve_manifest_002__dataset-B.json

# On Linux/Mac
mv preserve_manifest_001.json preserve_manifest_001__dataset-A.json

# The descriptions appear in --list output:
preserve RESTORE --src "E:/backup" --list
#   1. preserve_manifest_001__dataset-A.json - dataset-A (2025-09-18 14:30:00, 150 files)
#   2. preserve_manifest_002__dataset-B.json - dataset-B (2025-09-18 14:55:00, 75 files)
```

### Important Notes

- **No Overwrites**: Each operation creates a new manifest, preserving all history
- **Backward Compatible**: Single operations still work exactly as before
- **Auto-Migration**: The system automatically handles the transition from single to multiple manifests
- **Independent Restoration**: Each manifest can be restored independently

## Recommended Workflow

For critical data, it's recommended to follow a secure multi-step workflow:

1. **Pre-Verification**: Analyze and hash source files
2. **Copy with Structure**: Use `--rel --includeBase` to maintain directory structure
3. **Post-Copy Verification**: Verify all files match their source
4. **Test Restoration**: Run `--dry-run` to confirm restore will work
5. **Source Cleanup**: Only remove originals after verification passes

See the documentation for more details on secure workflows.

## What's New

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

### Latest Release (v0.5.x)

This is a maintenance development cycle. The current goal is stabilize and fully test all major uses of preserve (COPY, MOVE, RESTORE, and VERIFY) with no missing flags / functionality before 0.6.x.

### Recent Highlights
- **Advanced Filtering**: Exclude patterns, depth control, time-based selection
- **Three-Way Verification**: Source, destination, or both forms of verifications during restore operations
- **Sequential Manifests**: Support for multiple operations to same destination
- **GitRepoKit Versioning**: Automated version management with git hooks
- **Document Tidying**: Improving versioning, README, CHANGELOG, and other docs

## Contributing

Contributions are welcome! Feel free to submit a pull request.

Like the project?

[!["Buy Me A Coffee"](https://camo.githubusercontent.com/0b448aabee402aaf7b3b256ae471e7dc66bcf174fad7d6bb52b27138b2364e47/68747470733a2f2f7777772e6275796d6561636f666665652e636f6d2f6173736574732f696d672f637573746f6d5f696d616765732f6f72616e67655f696d672e706e67)](https://www.buymeacoffee.com/djdarcy)

## Acknowledgments

- [dazzlelink](https://github.com/djdarcy/dazzlelink) - Enhanced metadata storage and file references
- [GitRepoKit](https://github.com/djdarcy/GitRepoKit) - Automated version management system
- Community contributors - Testing, feedback, and improvements

## License

preserve, aka preserve.py, Copyright (C) 2025 Dustin Darcy

This program is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License](LICENSE) as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
