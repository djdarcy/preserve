# 📜 CHANGELOG.md - Preserve

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

---

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