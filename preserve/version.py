"""
Version information for the preserve project.

This file is automatically updated by git pre-commit hooks.
Format: VERSION_BRANCH_BUILD-YYYYMMDD-COMMITHASH

Example: 0.5.0_main_42-20250920-a1b2c3d4

Components:
- VERSION: Semantic version (MAJOR.MINOR.PATCH)
- BRANCH: Git branch name
- BUILD: Commit count
- YYYYMMDD: Commit date
- COMMITHASH: Short commit hash
"""

# Semantic version components
MAJOR = 0
MINOR = 5
PATCH = 0

# Optional release phase (alpha, beta, rc1, rc2, etc.)
# Set to None for stable releases
PHASE = None  # Stable release

# Full version string - updated by git pre-commit hook
# DO NOT EDIT THIS LINE MANUALLY
# Note: Hash reflects the commit this version builds upon (HEAD at commit time)
# The hash will be one commit behind after the commit is created (git limitation)
__version__ = "0.5.0_main_23-20250920-aa34dc9f"


def get_version():
    """Return the full version string including branch and build info."""
    return __version__


def get_base_version():
    """Return the semantic version string (MAJOR.MINOR.PATCH) with optional phase."""
    # Extract base version from __version__ string to maintain single source of truth
    # Format: VERSION_BRANCH_BUILD-DATE-HASH
    # Example: 0.4.0_main_13-20250920-ad442287 -> 0.4.0
    if '_' in __version__:
        base = __version__.split('_')[0]
    else:
        # Fallback if __version__ doesn't have expected format
        base = f"{MAJOR}.{MINOR}.{PATCH}"

    # Add phase if specified
    if PHASE:
        base = f"{base}-{PHASE}"

    return base


def get_version_dict():
    """Return version information as a dictionary."""
    parts = __version__.split('_')
    if len(parts) >= 3:
        base_version = parts[0]
        branch = parts[1]
        # Handle remaining parts which include build-date-hash
        build_info = '_'.join(parts[2:])
        build_parts = build_info.split('-')

        return {
            'full': __version__,
            'base': base_version,
            'branch': branch,
            'build': build_parts[0] if len(build_parts) > 0 else '',
            'date': build_parts[1] if len(build_parts) > 1 else '',
            'commit': build_parts[2] if len(build_parts) > 2 else '',
        }

    # Fallback for malformed version strings
    return {
        'full': __version__,
        'base': get_base_version(),
        'branch': 'unknown',
        'build': '0',
        'date': '',
        'commit': '',
    }


def get_pip_version():
    """
    Return PEP 440 compliant version for pip/setuptools.

    Converts our version format to PEP 440:
    - Main branch: 0.4.0_main_13-20250920-hash → 0.4.0
    - Dev branch: 0.4.0_dev_13-20250920-hash → 0.4.0.dev13
    - Feature branch: 0.4.0_feature_13-20250920-hash → 0.4.0.dev13+feature
    """
    if '_' not in __version__:
        return get_base_version()

    parts = __version__.split('_')
    base = parts[0]
    branch = parts[1] if len(parts) > 1 else 'unknown'

    if branch == 'main':
        # Release version
        return base
    else:
        # Development version
        build_info = '_'.join(parts[2:]) if len(parts) > 2 else ''
        build_num = build_info.split('-')[0] if '-' in build_info else '0'
        return f"{base}.dev{build_num}"

# For convenience in imports
VERSION = get_version()
BASE_VERSION = get_base_version()
PIP_VERSION = get_pip_version()