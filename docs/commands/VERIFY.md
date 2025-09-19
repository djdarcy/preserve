# VERIFY Command Documentation

## Overview

The `VERIFY` command checks the integrity of preserved files by comparing their current state against the hashes recorded in the manifest. It ensures that preserved files have not been corrupted, modified, or lost since they were preserved.

## What VERIFY Does

When you run VERIFY, it:

1. **Loads the manifest** from the destination directory
2. **For each file in the manifest**:
   - Locates the file at its preserved location
   - Calculates the current hash of the file
   - Compares it against the expected hash stored in the manifest
   - Reports the verification status

## What VERIFY Does NOT Do

- Does NOT check the original source files (unless `--src` is specified)
- Does NOT modify any files - it's read-only
- Does NOT compare against files in their original locations
- Does NOT perform three-way verification (use `RESTORE --verify` for that)

## Basic Usage

### Verify Latest Preservation
```bash
preserve VERIFY --dst /path/to/preserved/files
```
This verifies files using the latest (highest numbered) manifest.

### Verify Specific Manifest
```bash
preserve VERIFY --dst /path/to/preserved/files --manifest-number 2
```
or
```bash
preserve VERIFY --dst /path/to/preserved/files -n 2
```

### List Available Manifests
```bash
preserve VERIFY --dst /path/to/preserved/files --list
```

## Command Options

| Option | Description |
|--------|-------------|
| `--dst PATH` | **Required.** Path to the preserved files to verify |
| `--src PATH` | Optional. Original source location to compare against |
| `--manifest FILE` | Explicit manifest file to use |
| `--manifest-number N`, `-n N` | Select manifest by number (1, 2, 3, etc.) |
| `--list` | Show all available manifests and exit |
| `--hash ALGORITHM` | Hash algorithm to use (MD5, SHA1, SHA256, SHA512) |
| `--report FILE` | Save verification report to file |
| `-v, --verbose` | Show detailed progress |

## Verification Results

VERIFY reports files in these categories:

### ✅ VERIFIED
- File exists at the expected location
- Hash matches the manifest exactly
- File has not been modified or corrupted

### ❌ FAILED
- File exists but hash doesn't match
- Indicates corruption or modification
- **Action needed**: File may need to be re-preserved

### ⚠️ NOT_FOUND
- File is missing from the expected location
- May have been deleted or moved
- **Action needed**: Locate the file or restore from another backup

### ⏭️ SKIPPED
- No hash information in manifest for this file
- Cannot verify without hash data

## Examples

### Example 1: Verify Files on Network Share
```bash
preserve VERIFY --dst "\\server\backup\project_2024"

# Output:
VERIFY Operation Summary:
  Using manifest: preserve_manifest.json
  Verified: 150
  Failed: 0
  Missing: 2
```

### Example 2: Verify Multiple Preservation Operations
```bash
# List all available preservation points
preserve VERIFY --dst /backup/data --list

# Output:
Available manifests:
  1. preserve_manifest_001.json (2024-01-15 10:30:00, 500 files)
  2. preserve_manifest_002.json (2024-02-20 14:15:00, 750 files)
  3. preserve_manifest_003.json (2024-03-10 09:45:00, 600 files)

# Verify the second preservation
preserve VERIFY --dst /backup/data -n 2

# Output:
Selected manifest #2: preserve_manifest_002.json
VERIFY Operation Summary:
  Using manifest: preserve_manifest_002.json
  Verified: 750
  Failed: 0
  Missing: 0
```

### Example 3: Verify with Source Comparison
```bash
# This compares preserved files against their original source
preserve VERIFY --src /original/data --dst /backup/data

# Output:
VERIFY Operation Summary:
  Verified against source: 100
  Source modified: 5
  Failed: 0
  Missing: 0
```

### Example 4: Generate Verification Report
```bash
preserve VERIFY --dst /backup/critical_data --report verify_report.txt

# Creates detailed report with:
# - Timestamp of verification
# - List of all verified files
# - Details of any failures
# - Hash values for failed files
```

## Understanding Manifest Selection

When multiple manifests exist, VERIFY follows this priority:

1. **Explicit manifest** (`--manifest path/to/manifest.json`)
2. **Numbered manifest** (`--manifest-number 2` or `-n 2`)
3. **Latest manifest** (default - highest number)

### Manifest Naming Convention
- `preserve_manifest.json` - Single/initial manifest
- `preserve_manifest_001.json` - First numbered manifest
- `preserve_manifest_002.json` - Second numbered manifest
- `preserve_manifest_001__description.json` - With user description

## Use Cases

### Regular Integrity Checks
Run VERIFY periodically to ensure backup integrity:
```bash
# Weekly verification cron job
0 2 * * 0 preserve VERIFY --dst /backup/important --report /logs/verify_$(date +%Y%m%d).txt
```

### Before Restoration
Always verify before restoring to ensure files are intact:
```bash
# First verify
preserve VERIFY --dst /backup/project

# If verification passes, then restore
preserve RESTORE --src /backup/project
```

### After Network Transfers
Verify files after copying to network shares or cloud storage:
```bash
# After copying to network share
preserve VERIFY --dst "\\nas\backups\project"
```

### Corruption Detection
Detect bit rot or storage corruption over time:
```bash
# Compare current state against original preservation
preserve VERIFY --dst /long-term-archive/data -n 1
```

## Troubleshooting

### "No manifest found"
- Check that you're pointing to the correct directory
- Manifests should be in the destination directory
- Look for `preserve_manifest*.json` files

### "Hash mismatch" errors
- File has been modified or corrupted
- Try verifying with different hash algorithm
- Consider re-preserving the file

### Performance with large files
- Use `--hash MD5` for faster verification (less secure)
- Use `--hash SHA256` for better security (slower)
- Default is SHA256

### Network share issues
- Ensure you have read permissions
- Check network connectivity
- Try with full UNC path: `\\server\share\folder`

## Related Commands

- **COPY/MOVE**: Create preserved files with manifests
- **RESTORE**: Restore files to original locations
- **RESTORE --verify**: Three-way verification (source, preserved, manifest)

## Technical Details

### Hash Algorithms
- **SHA256** (default): Best balance of security and speed
- **SHA512**: Most secure, slower
- **SHA1**: Faster, less secure
- **MD5**: Fastest, least secure (not recommended)

### Manifest Structure
VERIFY reads these fields from the manifest:
```json
{
  "files": {
    "path/to/file": {
      "destination_path": "preserved/path/to/file",
      "hashes": {
        "SHA256": "abc123..."
      },
      "size": 1024
    }
  }
}
```

### Exit Codes
- `0`: All files verified successfully
- `1`: One or more files failed verification or not found
- `2`: Error reading manifest or other operational error

## Best Practices

1. **Verify immediately after preservation** to ensure successful operation
2. **Schedule regular verifications** for long-term storage
3. **Keep verification reports** for audit trails
4. **Use consistent hash algorithms** across operations
5. **Verify before any restoration** to avoid restoring corrupted files

## See Also

- [RESTORE Command](RESTORE.md) - For restoring verified files
- [COPY Command](COPY.md) - For creating preserved copies
- [Manifest Format](../architecture/manifest-format.md) - Understanding manifest structure