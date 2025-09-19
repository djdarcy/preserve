# 📜 CHANGELOG.md - Preserve

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Fixed
- **Critical**: Fixed manifest overwriting bug when multiple operations target the same destination (#4)
- Directory operations without --recursive flag now show helpful error messages

### Added
- Sequential manifest numbering system (preserve_manifest_001.json, _002, etc.)
- RESTORE --list option to show all available restore points
- RESTORE --number/-n option to restore from specific operation
- Support for user descriptions in manifest filenames (e.g., _001__description.json)
- Colored terminal output for warnings and errors (with graceful fallback)
- Auto-migration of existing single manifests to numbered format

### Improved
- RESTORE command now defaults to latest manifest when multiple exist
- Help text for COPY/MOVE operations with common usage examples
- Error messages for Windows path escaping issues

## [0.2.1] - 2025-05-14

### Fixed
- Improved relative path mode fallback behavior: now falls back to absolute path style (preserving structure) instead of flat structure when no common base directory can be found
- Enhanced logging for path resolution to make fallback behavior clearer

### Added
- Test scripts to verify relative path fallback scenarios
- Detailed documentation of relative path handling logic

## [0.2.0] - 2025-05-14

### Fixed
- Relative path mode (`--rel`) now properly preserves directory structure
- RESTORE operation behavior for all path modes
- Duplicate log messages in console output
- Directory structure preservation for files with no common parent

### Added
- Enhanced debugging and error reporting with [DEBUG PATH] prefix
- Verification report generation functionality
- Path tree analysis for better common base directory detection
- Test script for relative path mode verification

### Improved
- Path detection logic with robust common base directory finding
- Logging system with better configuration options
- Error handling during file operations

## [0.1.0] - 2025-05-14

### Added
- Initial implementation with basic functionality
- Core operations:
  - COPY: Copy files with path preservation options
  - MOVE: Move files with verification
  - RESTORE: Return files to original locations
  - VERIFY: Check file integrity with hash verification
  - CONFIG: View and modify configuration
- Path preservation styles:
  - Absolute paths (`--abs`)
  - Relative paths (`--rel`)
  - Flat structure (`--flat`)
- Hash verification using multiple algorithms (MD5, SHA1, SHA256, SHA512)
- Metadata preservation for file attributes
- Manifest system for tracking file operations
- Command-line interface with comprehensive options
- Cross-platform support (Windows, Linux, macOS)
- Basic dazzlelink integration (limited functionality)

### Known Issues
- Dazzlelink integration not fully functional
- Path preservation in relative mode needs improvement
- VERIFY report generation has some errors