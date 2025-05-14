# Preserve (v0.2.1)

A cross-platform file preservation tool with path normalization and verification.

[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](https://github.com/username/preserve/releases/tag/v0.2.1)

## Features

- **Path Preservation**: Copy or move files with multiple path preservation styles:
  - Relative paths that maintain directory structure (`--rel`)
  - Absolute paths with drive letter preservation (`--abs`)
  - Flat structure with all files in one directory (`--flat`)
- **Verification**: File integrity verification with multiple hash algorithms (MD5, SHA1, SHA256, SHA512)
- **Metadata**: Preserve file attributes (timestamps, permissions, etc.)
- **Manifests**: Detailed operation tracking for auditing and reversibility
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

For dazzlelink integration:

```bash
pip install preserve[dazzlelink]
```

## Usage

### Basic Usage

Copy files with relative path preservation:

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

## Recommended Workflow

For critical data, we recommend following a secure multi-step workflow:

1. **Pre-Verification**: Analyze and hash source files
2. **Copy with Structure**: Use `--rel --includeBase` to maintain directory structure
3. **Post-Copy Verification**: Verify all files match their source
4. **Test Restoration**: Run `--dry-run` to confirm restore will work
5. **Source Cleanup**: Only remove originals after verification passes

See the documentation for more details on secure workflows.

## What's New in v0.2.1

- Improved relative path mode fallback behavior: now falls back to absolute path style (preserving structure) instead of flat structure when no common base directory can be found
- Enhanced logging for path resolution to make fallback behavior clearer
- Added test script for relative path fallback scenarios

## What's New in v0.2.0

- Fixed relative path mode (`--rel`) to properly preserve directory structure
- Improved path detection and common base directory finding
- Fixed RESTORE operation for all path modes
- Enhanced debugging and error reporting
- Fixed duplicate log messages
- Added verification report generation

## License

MIT
