#!/usr/bin/env python3
"""
Test RESTORE --dst functionality.

This test verifies that the --dst flag correctly overrides the destination
path when restoring files, rather than restoring to original locations.
"""

import unittest
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path


class TestRestoreDst(unittest.TestCase):
    """Test RESTORE --dst destination override functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_restore_dst_'))
        self.source_dir = self.test_dir / 'source'
        self.backup_dir = self.test_dir / 'backup'
        self.restore_dir = self.test_dir / 'new_location'

        # Create source directory with test files
        self.source_dir.mkdir()
        self.backup_dir.mkdir()
        self.restore_dir.mkdir()

        # Create test files
        (self.source_dir / 'file1.txt').write_text('Test content 1')
        (self.source_dir / 'file2.py').write_text('print("hello")')

        # Create subdirectory
        subdir = self.source_dir / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.md').write_text('# Test document')

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_preserve(self, args):
        """Run preserve command and capture output."""
        cmd = [sys.executable, '-m', 'preserve'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        return result

    def test_restore_dst_override(self):
        """Test that RESTORE --dst correctly overrides destination path."""

        # Step 1: Create backup
        result = self.run_preserve([
            'COPY',
            str(self.source_dir),
            '--recursive',
            '--rel',
            '--includeBase',
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256'
        ])
        self.assertEqual(result.returncode, 0, f"COPY failed: {result.stderr}")

        # Step 2: Remove original source files to simulate need for restoration
        shutil.rmtree(self.source_dir)

        # Step 3: Restore to NEW location using --dst override
        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir),
            '--dst', str(self.restore_dir)
        ])

        # Currently this will fail because --dst is ignored
        self.assertEqual(result.returncode, 0, f"RESTORE failed: {result.stderr}")

        # Step 4: Verify files were restored to NEW location (not original)
        # Files should be in restore_dir, not recreated in source_dir

        # Check that files exist in the new location
        # With --rel --includeBase, the structure should be preserved
        restored_file1 = self.restore_dir / 'source' / 'file1.txt'
        restored_file2 = self.restore_dir / 'source' / 'file2.py'
        restored_file3 = self.restore_dir / 'source' / 'subdir' / 'file3.md'

        # Debug: List what actually got created
        print(f"\nDEBUG: Contents of restore directory {self.restore_dir}:")
        for f in self.restore_dir.rglob('*'):
            print(f"  {f}")
        print()

        self.assertTrue(restored_file1.exists(),
                       f"file1.txt should be restored to {restored_file1}")
        self.assertTrue(restored_file2.exists(),
                       f"file2.py should be restored to {restored_file2}")
        self.assertTrue(restored_file3.exists(),
                       f"file3.md should be restored to {restored_file3}")

        # Check content is correct
        self.assertEqual(restored_file1.read_text(), 'Test content 1')
        self.assertEqual(restored_file2.read_text(), 'print("hello")')
        self.assertEqual(restored_file3.read_text(), '# Test document')

        # Check that files were NOT restored to original location
        if self.source_dir.exists():
            original_files = list(self.source_dir.rglob('*'))
            original_file_count = sum(1 for f in original_files if f.is_file())
            print(f"DEBUG: Found {original_file_count} files in original location:")
            for f in original_files:
                if f.is_file():
                    print(f"  {f}")
            self.assertEqual(original_file_count, 0,
                           f"Files should NOT be restored to original location when --dst is used. Found {original_file_count} files.")
        else:
            print("DEBUG: Original source directory does not exist (correct)")

        # The key test: files should exist in NEW location but NOT in original
        self.assertTrue(self.source_dir.exists() == False or
                       len(list(self.source_dir.rglob('*.txt'))) == 0,
                       "Original location should be empty when using --dst")

    def test_restore_without_dst_uses_original_paths(self):
        """Test that RESTORE without --dst restores to original locations."""

        # Step 1: Create backup
        result = self.run_preserve([
            'COPY',
            str(self.source_dir),
            '--recursive',
            '--rel',
            '--includeBase',
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256'
        ])
        self.assertEqual(result.returncode, 0)

        # Step 2: Remove original source files
        shutil.rmtree(self.source_dir)

        # Step 3: Restore without --dst (should use original paths)
        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # Step 4: Verify files were restored to original location
        self.assertTrue((self.source_dir / 'file1.txt').exists())
        self.assertTrue((self.source_dir / 'file2.py').exists())
        self.assertTrue((self.source_dir / 'subdir' / 'file3.md').exists())

    def test_restore_dst_with_absolute_paths(self):
        """Test RESTORE --dst with absolute path handling."""

        # Create backup with absolute paths
        result = self.run_preserve([
            'COPY',
            str(self.source_dir),
            '--recursive',
            '--abs',
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256'
        ])
        self.assertEqual(result.returncode, 0)

        # Remove original
        shutil.rmtree(self.source_dir)

        # Restore to new location
        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir),
            '--dst', str(self.restore_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # With absolute paths, the structure should be preserved under restore_dir
        # but files should not go back to their original absolute locations
        restored_files = list(self.restore_dir.rglob('*.txt'))
        self.assertGreater(len(restored_files), 0, "Should find restored files in new location")


if __name__ == '__main__':
    unittest.main()