# Hashing Layer Architecture

## Overview

The preserve project has file hashing functionality owned by `preservelib`, with `filetoolkit` optionally using simpler standalone utilities when needed.

## Architecture Decision

**Decision Date**: 2025-09-19
**Pattern**: Ownership Pattern

### Layers

```
┌─────────────────────────────────────┐
│         External Code               │
│  (imports from preservelib when     │
│   using preserve features)          │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│         preservelib                 │
│   preservelib/manifest.py           │
│                                     │
│  • calculate_file_hash()            │  ← Main implementation
│  • verify_file_hash()               │  ← Owner of hashing logic
│  • Manifest integration             │
│  • Progress callbacks               │
│  • Buffer size configuration        │
└─────────────────────────────────────┘

     (independent, optional)

┌─────────────────────────────────────┐
│         filetoolkit                 │
│   filetoolkit/verification.py       │
│                                     │
│  • calculate_file_hash()            │  ← Simple standalone version
│  • verify_file_hash()               │  ← For filetoolkit-only uses
│  • No dependencies on preservelib   │
│  • Lightweight utilities            │
└─────────────────────────────────────┘
```

## Implementation Details

### Main Implementation (preservelib)

Located in `preservelib/manifest.py`:

```python
def calculate_file_hash(
    file_path: Union[str, Path],
    algorithms: List[str] = None,
    buffer_size: int = 65536,
    manifest: Optional['PreserveManifest'] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, str]:
    """Main implementation with preserve-specific features."""
```

**Features**:
- Full-featured hashing with MD5, SHA1, SHA256, SHA512
- Manifest integration for recording hash calculations
- Progress callbacks for UI feedback
- Configurable buffer size for performance tuning
- Future: Batch operations support
- Future: Caching of hash results

### Optional Standalone Utilities (filetoolkit)

Located in `filetoolkit/verification.py`:

```python
def calculate_file_hash(
    file_path: Union[str, Path],
    algorithms: List[str] = None,
    buffer_size: int = 65536
) -> Dict[str, str]:
    """Simple standalone utility - no preservelib dependencies."""
```

**Features**:
- Lightweight standalone operation
- No dependencies on preservelib
- Simple hash calculation for filetoolkit-only operations
- Can be used independently when preserve features aren't needed

## Import Guidelines

### Rule 1: Inside preservelib/
Always import from `preservelib.manifest`:
```python
from .manifest import calculate_file_hash
```

### Rule 2: Inside filetoolkit/
Uses its own implementation in `filetoolkit.verification`:
```python
from .verification import calculate_file_hash
```

### Rule 3: External Code
- For preserve operations: Import from `preservelib.manifest`
- For standalone utilities: Can import from `filetoolkit.verification`

## Benefits

1. **Clear Ownership**: preservelib owns the main hashing implementation
2. **Independence**: filetoolkit has no dependencies on preservelib
3. **No Circular Dependencies**: Clean architecture with clear layers
4. **Extensibility**: preservelib can add features independently
5. **Backward Compatible**: Existing code continues to work
6. **Flexibility**: Two implementations for different use cases

## Migration Path

For existing code:
1. Code importing from `preservelib.manifest` continues to work
2. Code importing from `filetoolkit.verification` gets simple version
3. No breaking changes to existing APIs

## Future Enhancements

The preservelib implementation can add:
- Hash result caching
- Parallel hashing for multiple files
- Cloud storage integration
- Custom hash algorithm plugins
- Compression before hashing
- Incremental hashing for large files

All without affecting filetoolkit's simple utilities.