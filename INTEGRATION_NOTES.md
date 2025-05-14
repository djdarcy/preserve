# Dazzlelink Integration Notes

## Overview

This document describes the integration of the Dazzlelink library with the Preserve tool. Dazzlelink is a cross-platform tool for exporting, importing, and managing symbolic links, particularly useful for handling network paths and preserving links across different systems.

## Integration Strategy

The Preserve tool can use Dazzlelink in two ways:

1. **Built-in Mode**: Using the simplified DazzleLink implementation in `preservelib/dazzlelink/` when the full Dazzlelink library is not available
2. **Full Mode**: Using the complete Dazzlelink library when available (either installed via pip or using the bundled version)

## Key Integration Points

### Import Discovery

- The code first attempts to import the installed Dazzlelink library
- If not found, it falls back to checking for the bundled version in the `dazzlelink/` directory
- If neither is available, it uses the simplified implementation

### API Compatibility

The integration is designed to work with multiple versions of the Dazzlelink API:

- It checks for both top-level functions (`create_link`, `export_link`, `import_link`, etc.)
- It falls back to using the `DazzleLink` class methods when needed
- It handles API changes between versions

### Core Functions

The following key functions provide the integration:

1. `create_dazzlelink`: Creates a dazzlelink from a source file to a destination file
2. `find_dazzlelinks_in_dir`: Finds dazzlelink files in a directory
3. `restore_from_dazzlelink`: Restores a file from a dazzlelink
4. `dazzlelink_to_manifest`: Converts dazzlelink files to a manifest-compatible structure
5. `manifest_to_dazzlelinks`: Converts a manifest to dazzlelink files

## Usage in Preserve Operations

- **COPY/MOVE**: Creates dazzlelinks alongside copied/moved files when `--dazzlelink` flag is provided
- **RESTORE**: Can restore files from dazzlelinks or convert dazzlelinks to a manifest
- **CONFIG**: Support for dazzlelink-specific configuration options

## Bundled Version

The Preserve tool includes a bundled version of Dazzlelink in the `dazzlelink/` directory, which is used when the pip-installed version is not available. This ensures that basic dazzlelink functionality is always available.

## Dependencies

- The dazzlelink integration is optional and can be installed via `pip install -e ".[dazzlelink]"`
- On Windows, additional functionality is available with `pywin32` (included in the `windows` extras)
- For full functionality, install with `pip install -e ".[all]"`