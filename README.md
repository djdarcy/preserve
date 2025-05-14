# Preserve

A cross-platform file preservation tool with path normalization and verification.

## Features

- Copy or move files with path preservation (relative, absolute, or flat structures)
- File verification with multiple hash algorithms (MD5, SHA1, SHA256, SHA512)
- Preserve file attributes (timestamps, permissions, etc.)
- Detailed operation manifests for tracking and reversibility
- Optional integration with dazzlelink for metadata storage
- Cross-platform compatibility (Windows, Linux, macOS)

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

## License

MIT
