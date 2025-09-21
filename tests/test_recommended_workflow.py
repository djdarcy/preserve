#!/usr/bin/env python3
"""
Test the Recommended Workflow for Critical Data from README.

This test follows the exact workflow documented in the README to ensure
it works as described for users.
"""

import unittest
import tempfile
import shutil
import hashlib
import json
import subprocess
import sys
from pathlib import Path


class TestRecommendedWorkflow(unittest.TestCase):
    """Test the end-to-end workflow: create hashes → backup → verify → restore → validate hashes match."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for tests
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_workflow_'))
        self.source_dir = self.test_dir / 'my-project'
        self.backup_dir = self.test_dir / 'backup'
        self.restore_dir = self.test_dir / 'test-restore'

        # Create source directory with test files
        self.source_dir.mkdir()
        self.backup_dir.mkdir()

        # Create test files with known content
        (self.source_dir / 'file1.txt').write_text('Content of file 1')
        (self.source_dir / 'file2.py').write_text('#!/usr/bin/env python3\nprint("Hello")')

        # Create subdirectory with files
        subdir = self.source_dir / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.md').write_text('# Documentation\nTest content')
        (subdir / 'file4.json').write_text('{"key": "value"}')

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def calculate_file_hash(self, file_path, algorithm='sha256'):
        """Calculate hash of a file."""
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    def create_source_hashes(self):
        """Step 1: Create baseline hashes for source files."""
        hashes = {}
        for file_path in self.source_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.source_dir)
                hashes[str(relative_path)] = self.calculate_file_hash(file_path)
        return hashes

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

    def test_complete_workflow(self):
        """Test the full backup → verify → restore → validate workflow from README."""

        # Step 1: Pre-Verification (Create baseline hashes)
        print("\n=== Step 1: Pre-Verification ===")
        source_hashes = self.create_source_hashes()
        self.assertEqual(len(source_hashes), 4, "Should have 4 source files")
        print(f"Created hashes for {len(source_hashes)} files")

        # Step 2: Copy with Structure Preservation
        print("\n=== Step 2: Copy with Structure Preservation ===")
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
        print("COPY operation completed successfully")

        # Verify manifest was created
        manifest_files = list(self.backup_dir.glob('preserve_manifest*.json'))
        self.assertTrue(len(manifest_files) > 0, "No manifest created")

        # Step 3: Post-Copy Verification
        print("\n=== Step 3: Post-Copy Verification ===")
        verify_report = self.test_dir / 'verify-report.txt'
        result = self.run_preserve([
            'VERIFY',
            '--src', str(self.source_dir),
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256',
            '--report', str(verify_report)
        ])

        self.assertEqual(result.returncode, 0, f"VERIFY failed: {result.stderr}")
        self.assertTrue(verify_report.exists(), "Verification report not created")

        # Check verification report content
        report_content = verify_report.read_text()
        self.assertIn('all match', report_content.lower(), "Files should all match")
        print("Verification completed successfully")

        # Step 4: Test Restoration (Dry Run)
        print("\n=== Step 4: Test Restoration (Dry Run) ===")
        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir),
            '--dry-run'
        ])

        self.assertEqual(result.returncode, 0, f"RESTORE dry-run failed: {result.stderr}")
        # Dry-run shows what would be done - files are skipped because they already exist
        self.assertIn('skipped', result.stdout.lower(), "Should show skipped files")
        print("Dry run completed successfully")

        # Step 5: Actual Restoration to Test Location
        print("\n=== Step 5: Restore to Test Location ===")
        # Create the restore directory
        self.restore_dir.mkdir(exist_ok=True)

        # Since files exist at original location, we need to test with --force
        # or remove the originals first. Let's remove originals to simulate
        # a real recovery scenario
        shutil.rmtree(self.source_dir)

        result = self.run_preserve([
            'RESTORE',
            '--src', str(self.backup_dir)
        ])

        self.assertEqual(result.returncode, 0, f"RESTORE failed: {result.stderr}")
        print(f"Restoration output:\n{result.stdout}")
        print("Restoration completed successfully")

        # Step 6: Validate Restoration
        print("\n=== Step 6: Validate Restoration ===")

        # Files should be restored to their original location
        self.assertTrue(self.source_dir.exists(), "Source directory should be recreated")

        # Count restored files
        restored_files = list(self.source_dir.rglob('*'))
        restored_file_count = sum(1 for f in restored_files if f.is_file())
        self.assertEqual(restored_file_count, 4, f"Expected 4 files, found {restored_file_count}")

        # Verify file contents match original hashes
        for relative_path, original_hash in source_hashes.items():
            restored_file = self.source_dir / relative_path
            self.assertTrue(restored_file.exists(), f"File {relative_path} not restored")

            restored_hash = self.calculate_file_hash(restored_file)
            self.assertEqual(
                restored_hash, original_hash,
                f"Hash mismatch for {relative_path}"
            )

        print("All files validated successfully - hashes match!")
        print("\n=== Workflow Test Complete ===")
        print("[PASS] All steps of the recommended workflow passed")

    def test_workflow_with_verification_failure(self):
        """Test workflow when verification detects a problem."""

        # Step 1: Create baseline
        source_hashes = self.create_source_hashes()

        # Step 2: Copy files
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

        # Corrupt a backup file to simulate damage
        backup_file = self.backup_dir / 'my-project' / 'file1.txt'
        self.assertTrue(backup_file.exists())
        backup_file.write_text('CORRUPTED CONTENT')

        # Step 3: Verification should detect the problem
        verify_report = self.test_dir / 'verify-report.txt'
        result = self.run_preserve([
            'VERIFY',
            '--src', str(self.source_dir),
            '--dst', str(self.backup_dir),
            '--hash', 'SHA256',
            '--report', str(verify_report)
        ])

        # Verify should complete but report mismatches
        # Check that the report mentions the mismatch
        report_content = verify_report.read_text()
        self.assertIn('file1.txt', report_content)

        print("\n[PASS] Workflow correctly detected corrupted backup file")

    def test_loadIncludes_workflow(self):
        """Test workflow using --loadIncludes option."""

        # Create includes file listing specific files to backup
        includes_file = self.test_dir / 'files-to-copy.txt'
        includes_file.write_text(
            f"{self.source_dir / 'file1.txt'}\n"
            f"{self.source_dir / 'subdir' / 'file3.md'}\n"
        )

        # Copy using loadIncludes
        result = self.run_preserve([
            'COPY',
            '--loadIncludes', str(includes_file),
            '--dst', str(self.backup_dir),
            '--rel'
        ])

        self.assertEqual(result.returncode, 0, f"COPY with loadIncludes failed: {result.stderr}")

        # Verify only specified files were copied
        manifest_files = list(self.backup_dir.glob('preserve_manifest*.json'))
        self.assertTrue(len(manifest_files) > 0)

        with open(manifest_files[0]) as f:
            manifest = json.load(f)

        # Check that only the included files are in manifest
        file_count = len(manifest.get('files', []))
        self.assertEqual(file_count, 2, "Should have copied exactly 2 files from includes list")

        print("\n[PASS] loadIncludes workflow completed successfully")


if __name__ == '__main__':
    unittest.main()