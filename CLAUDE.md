# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Organization

When working with git, please note that the project is organized with the following main branches:
- `main`: The main branch for stable releases
- `claude-dev`: Current development branch (used for Claude Code development)

The initial implementation is based on v0.1.0 commit e6d283fde9aee95e63364d767d0b585207b18e52.

### Git Workflow Guidelines

When making changes to the codebase, follow these guidelines:

0. **Always Test Before Committing**: This is the most important guideline!
   - Run the tool with relevant commands before each commit
   - Test all modified functionality with representative inputs
   - For this project, test commands like `preserve COPY --loadIncludes "private\files-to-copy.txt" --dst ".\private\dst2" --abs` and `preserve RESTORE --src .\private\dst2`
   - Install dependencies as needed: `pip install -e ./tools/dazzlelink`

1. **Commit Frequently**: After each batch of related changes working towards a feature, make a targeted git commit.
   - This enables easier tracking of changes and rollback if something goes wrong.
   - Choose files to commit intentionally rather than using `git add .`
   - Write clear commit messages that explain the purpose of the changes.

2. **Test Before Committing**: Always test your changes before committing them.
   - Run basic tests and verify functionality first.
   - Don't commit code that hasn't been tested.

3. **Targeted Commits**: Group related changes into logical commits.
   - Feature additions should be committed separately from bug fixes.
   - Refactoring should be committed separately from feature work when possible.

4. **Git Hook Issues**: If you encounter issues with git hooks when committing, use the following alternatives:
   - Use `git commit --no-verify` to bypass the pre-commit hooks
   - You may need this if you see errors like `fatal: cannot exec '.git/hooks/pre-commit': No such file or directory`

5. **Development Workflow**: For every problem you tackle:
   - Read and understand "the dev workflow process in ".\convos\AI_notes\THE DEV WORKFLOW PROCESS (AKA THE PROCESS) – 5 STAGES.md"
   - Document your analysis in the `convos/AI_notes/` directory
   - Leave summaries of your thoughts and approach in these notes
   - Update CLAUDE.md with any critical new learnings or workflow tips
   - Test changes thoroughly before committing

## Build and Test Commands
- Install package: `pip install -e .`
- Install with development dependencies: `pip install -e ".[dev]"`
- Install with Windows extras: `pip install -e ".[windows]"`
- Install with dazzlelink support: `pip install -e ".[dazzlelink]"`
- Run the tool: `preserve [OPERATION] [OPTIONS]`
- Example commands:
  - `preserve COPY --loadIncludes "private\files-to-copy.txt" --dst ".\private\dst2" --abs`
  - `preserve MOVE --loadIncludes "private\files-to-copy.txt" --dst ".\private\dst5" --abs`
  - `preserve RESTORE --src .\private\dst5`
  - `preserve VERIFY --hash SHA1 --dst .\private\dst2 --report report.txt`
  - `preserve CONFIG VIEW`
- Formatting/linting: `black .` and `flake8`
- Type checking: `mypy preserve preservelib`

## Known Issues and Solutions

### Dazzlelink Path Handling

When creating dazzlelinks with `--abs` flag, the paths can be incorrectly constructed when the destination path already includes the destination base directory. Solutions include:

1. For 'absolute' path style, use the source_path to determine dazzlelink structure
2. Strip destination base from destination path before constructing dazzlelink paths
3. Handle path normalization consistently across all code paths

See full analysis in `convos/AI_notes/dazzlelink_path_analysis.md`.

### Relative Path Style Handling

When using `--rel` mode, the system needs to find a common base directory for source files. Challenges include:

1. Identifying the most appropriate common parent directory for the files
2. Applying the same relative path structure to dazzlelinks
3. Properly handling mixed path separators between Windows and Unix-style paths

Implemented solution:
- Detect common parent directories when no explicit source_base is provided
- Special handling for known patterns (e.g., 'D:\temp', 'TodoAI-GPTs') for both source paths and dazzlelinks
- Enhanced debugging output to help diagnose path resolution issues

### RESTORE Operation Path Resolution

The RESTORE operation may experience path resolution issues when paths are double-prefixed or when hardcoded paths are embedded in the code. Solutions implemented:

1. Generic detection of source directory names in paths to avoid double-prefixing
2. Recognition of common destination directory names ('dst', 'dst2', etc.)
3. Enhanced error reporting for skipped files with file existence checks
4. Fallback mechanism to find alternative paths when the exact file can't be found

## Code Architecture

### Project Structure
- `preserve/`: Core CLI application
  - `preserve.py`: Main entry point with CLI argument parsing and command handling
  - `config.py`: Configuration management
  - `utils.py`: Utility functions for CLI operations
  - `setup-logging.py`: Logging configuration
  
- `preservelib/`: Core operation implementation
  - `operations.py`: Implements COPY, MOVE, VERIFY, and RESTORE operations
  - `manifest.py`: Manages operation manifests for tracking files and metadata
  - `metadata.py`: File metadata handling
  - `restore.py`: File restoration logic
  - `dazzlelink/`: Integration with dazzlelink (optional)
  
- `filetoolkit/`: Lower-level file operations
  - `operations.py`: File operation primitives
  - `paths.py`: Path handling utilities
  - `verification.py`: File verification functions
  - `platform/`: Platform-specific implementations

### Key Components

1. **CLI Interface**: The `preserve.py` script defines the command-line interface using argparse, with subcommands for different operations (COPY, MOVE, VERIFY, RESTORE, CONFIG).

2. **Manifest System**: Operations create and update manifests (`manifest.py`) that track file sources, destinations, hashes, and metadata. Manifests enable verification and restoration.

3. **Path Preservation Options**:
   - `--rel`: Preserve relative paths
   - `--abs`: Preserve absolute paths (with drive letter as directory)
   - `--flat`: Flatten directory structure

4. **File Verification**: Uses hash algorithms (MD5, SHA1, SHA256, SHA512) to verify file integrity after operations.

5. **Cross-Platform Compatibility**: The `filetoolkit` package provides platform-specific implementations for file operations.

## Important Development Guidelines

### Avoid Hardcoding Paths or Using "Fixed" Known Values

Never hardcode specific paths (like "D:\\temp") or use fixed known values in algorithms that should be generic. This is effectively "cheating" and prevents the code from working in other environments or with different data. Instead:

- Always write generic algorithms that can handle any valid input
- Implement proper common prefix/suffix detection for path operations
- Use appropriate data structures (trees, tries, etc.) to find common elements
- Test with various directory structures, not just the sample data

### Generic Path Handling

When implementing relative path handling:

- Find the longest common prefix of all paths programmatically
- Don't assume any specific directory structure
- Handle cross-platform path separators correctly
- Consider different drives on Windows systems
- Handle edge cases like no common prefix or only the root as common

## Code Style Guidelines
- **Edits**: Do not change comments or class, function, variable names, etc. needlessly. This makes diffing harder. Only make changes to naming or comments where it is either necessary for a fix or it dramatically improves the logic or understandability.
- **Imports**: Use standard Python imports. Follow existing import ordering patterns.
- **Formatting**: 4-space indentation for Python code
- **Function Pattern**: Prefer early returns over nested conditionals.
- **Error Handling**: Use try/except blocks and log errors appropriately.
- **Documentation**: Maintain docstrings in Google style format.
- **Logging**: Use the module-level logger (`logger = logging.getLogger(__name__)`) for logging.

When editing, maintain existing patterns and conduct thorough testing before submitting.