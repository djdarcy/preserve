#!/usr/bin/env python
"""Debug test for restore operation"""

import sys
import os
import json
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import preserve.preserve as preserve

# Create test directory
test_dir = Path(tempfile.mkdtemp())

# Create valid manifest
manifest_data = {
    "manifest_version": 1,
    "created_at": "2024-01-01T12:00:00",
    "operations": [{
        "operation_id": "test123",
        "operation_type": "COPY",
        "timestamp": "2024-01-01T12:00:00",
        "files": {}
    }],
    "files": {
        "file1.txt": {
            "source": "/original/file1.txt",
            "destination": "file1.txt",
            "hashes": {"SHA256": "abc123"},
            "metadata": {}
        }
    }
}

manifest_path = test_dir / "preserve_manifest_002.json"
manifest_path.write_text(json.dumps(manifest_data, indent=2))

print(f"Created test manifest at: {manifest_path}")
print(f"Manifest contents valid: {manifest_path.exists()}")

# Mock args for --number 2
args = MagicMock()
args.src = str(test_dir)
args.list = False
args.manifest_number = 2
args.number = 2
args.dry_run = False
args.force = False

# Create a proper logger for tests instead of MagicMock
logger = logging.getLogger('test_restore_debug')
logger.setLevel(logging.INFO)  # Show info for debugging

# Try to run restore
print("\nRunning handle_restore_operation...")
try:
    with patch('preserve.preserve.operations') as mock_ops:
        mock_result = MagicMock()
        mock_result.success_count.return_value = 5
        mock_result.failure_count.return_value = 0
        mock_result.skip_count.return_value = 0
        mock_result.skipped = []
        mock_result.error_messages = {}
        mock_ops.restore_operation.return_value = mock_result

        result = preserve.handle_restore_operation(args, logger)
        print(f"Result: {result}")

        if result != 0:
            print(f"ERROR: Expected result 0, got {result}")
            # Check what was logged
            print("\nLogger calls:")
            for call in logger.error.call_args_list:
                print(f"  ERROR: {call}")
            for call in logger.warning.call_args_list:
                print(f"  WARNING: {call}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
shutil.rmtree(test_dir, ignore_errors=True)