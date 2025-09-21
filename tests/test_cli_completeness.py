#!/usr/bin/env python3
"""
Test CLI completeness - ensure all parsed arguments are actually used.

This test helps prevent issues like #30 where CLI arguments are parsed
but ignored in the implementation.
"""

import unittest
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path


class TestCLICompleteness(unittest.TestCase):
    """Test that CLI arguments are actually used by the implementation."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_cli_completeness_'))
        self.source_dir = self.test_dir / 'source'
        self.backup_dir = self.test_dir / 'backup'
        self.restore_dir = self.test_dir / 'restore'

        # Create source directory with test files
        self.source_dir.mkdir()
        self.backup_dir.mkdir()
        self.restore_dir.mkdir()

        (self.source_dir / 'test.txt').write_text('test content')

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

    def test_restore_dst_argument_usage(self):
        """Test that RESTORE --dst argument is actually used."""

        # Create backup
        result = self.run_preserve([
            'COPY',
            str(self.source_dir),
            '--recursive',
            '--rel',
            '--includeBase',
            '--dst', str(self.backup_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # Remove original
        shutil.rmtree(self.source_dir)

        # Restore with --dst should create files in restore_dir, not original location
        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir),
            '--dst', str(self.restore_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # Verify file was restored to the specified destination
        restored_file = self.restore_dir / 'source' / 'test.txt'
        self.assertTrue(restored_file.exists(),
                       "RESTORE --dst should create files in destination directory")

        # Verify file was NOT restored to original location
        original_file = self.source_dir / 'test.txt'
        self.assertFalse(original_file.exists(),
                        "RESTORE --dst should NOT restore to original location")

    def test_verify_report_argument_usage(self):
        """Test that VERIFY --report argument creates a report file."""

        # Create backup
        result = self.run_preserve([
            'COPY',
            str(self.source_dir),
            '--recursive',
            '--dst', str(self.backup_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # Verify with --report should create report file
        report_file = self.test_dir / 'verify_report.txt'
        result = self.run_preserve([
            'VERIFY',
            '--src', str(self.source_dir),
            '--dst', str(self.backup_dir),
            '--report', str(report_file)
        ])
        self.assertEqual(result.returncode, 0)

        # Verify report file was created
        self.assertTrue(report_file.exists(),
                       "VERIFY --report should create report file")

        # Verify report has content
        report_content = report_file.read_text()
        self.assertGreater(len(report_content), 0,
                          "Report file should not be empty")

    def test_copy_dst_argument_usage(self):
        """Test that COPY --dst argument creates files in destination."""

        result = self.run_preserve([
            'COPY',
            str(self.source_dir / 'test.txt'),
            '--dst', str(self.backup_dir)
        ])
        self.assertEqual(result.returncode, 0)

        # With --rel as default (no base directory included for single files),
        # the file should be placed directly in the backup directory
        copied_file = self.backup_dir / 'test.txt'
        self.assertTrue(copied_file.exists(),
                       "COPY --dst should create files in destination directory")

    def test_copy_hash_argument_usage(self):
        """Test that COPY --hash argument affects verification behavior."""

        # Copy with SHA256 hash
        result = self.run_preserve([
            'COPY',
            str(self.source_dir / 'test.txt'),
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256'
        ])
        self.assertEqual(result.returncode, 0)

        # Check that manifest contains hash information
        manifest_files = list(self.backup_dir.glob('preserve_manifest*.json'))
        self.assertTrue(len(manifest_files) > 0, "Manifest should be created")

        import json
        with open(manifest_files[0]) as f:
            manifest = json.load(f)

        # Verify that hash algorithm is recorded in operations
        self.assertIn('operations', manifest)
        self.assertGreater(len(manifest['operations']), 0, "Should have at least one operation")
        self.assertEqual(manifest['operations'][0]['options']['hash_algorithm'], 'SHA256')


if __name__ == '__main__':
    unittest.main()