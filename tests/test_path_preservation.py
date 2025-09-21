#!/usr/bin/env python3
"""
Test path preservation behavior for COPY/MOVE operations.
Ensures subdirectory structure is preserved correctly with and without --includeBase.

This test suite verifies the correct behavior:
- Without --includeBase: Preserve immediate subdirectory structure
- With --includeBase: Include the source directory name (last component only)
"""

import unittest
import tempfile
import shutil
import subprocess
import sys
import json
from pathlib import Path


class TestSubdirectoryPreservation(unittest.TestCase):
    """Test that subdirectory structure is correctly preserved during operations."""

    def setUp(self):
        """Create test directory structure."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_path_preservation_'))
        self.maxDiff = None  # Show full diff on assertion failures

    def tearDown(self):
        """Clean up test directories."""
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

    def create_test_structure(self, name):
        """Create a specific test directory structure."""
        source_dir = self.test_dir / f'source_{name}'
        dest_dir = self.test_dir / f'dest_{name}'

        source_dir.mkdir(parents=True)
        dest_dir.mkdir(parents=True)

        return source_dir, dest_dir

    def verify_structure(self, dest_dir, expected_paths):
        """Verify the destination directory has the expected structure."""
        actual_paths = set()
        for path in dest_dir.rglob('*'):
            if path.is_file():
                # Skip manifest files - they're expected but not part of structure verification
                if path.name in ['preserve_manifest.json', 'preserve_manifest.yaml']:
                    continue
                relative = path.relative_to(dest_dir)
                actual_paths.add(str(relative).replace('\\', '/'))

        expected = set(expected_paths)
        self.assertEqual(actual_paths, expected,
                        f"Structure mismatch.\nExpected: {sorted(expected)}\nActual: {sorted(actual_paths)}")

    def test_single_subdir_without_includeBase(self):
        """Without --includeBase should preserve immediate subdirectory structure."""
        source, dest = self.create_test_structure('single_no_base')

        # Create: source/subdir/file.txt
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'file.txt').write_text('content')

        # Run: preserve COPY source -r --rel --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/subdir/file.txt (preserve subdir structure)
        self.verify_structure(dest, ['subdir/file.txt'])

    def test_single_subdir_with_includeBase(self):
        """With --includeBase should include the source directory name."""
        source, dest = self.create_test_structure('single_with_base')

        # Create: source/subdir/file.txt
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'file.txt').write_text('content')

        # Run: preserve COPY source -r --rel --includeBase --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/source_single_with_base/subdir/file.txt
        # The base directory name should be included
        expected_base = source.name  # 'source_single_with_base'
        self.verify_structure(dest, [f'{expected_base}/subdir/file.txt'])

    def test_multiple_subdirs_without_includeBase(self):
        """Multiple subdirectories should all be preserved without base."""
        source, dest = self.create_test_structure('multi_no_base')

        # Create: source/subdir1/file1.txt, source/subdir2/file2.txt, source/subdir3/file3.txt
        for i in range(1, 4):
            subdir = source / f'subdir{i}'
            subdir.mkdir()
            (subdir / f'file{i}.txt').write_text(f'content{i}')

        # Run: preserve COPY source -r --rel --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/subdir1/file1.txt, dest/subdir2/file2.txt, dest/subdir3/file3.txt
        self.verify_structure(dest, [
            'subdir1/file1.txt',
            'subdir2/file2.txt',
            'subdir3/file3.txt'
        ])

    def test_multiple_subdirs_with_includeBase(self):
        """Multiple subdirectories with base should include source directory name."""
        source, dest = self.create_test_structure('multi_with_base')

        # Create: source/subdir1/file1.txt, source/subdir2/file2.txt
        for i in range(1, 3):
            subdir = source / f'subdir{i}'
            subdir.mkdir()
            (subdir / f'file{i}.txt').write_text(f'content{i}')

        # Run: preserve COPY source -r --rel --includeBase --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/source_multi_with_base/subdir1/file1.txt, etc.
        expected_base = source.name
        self.verify_structure(dest, [
            f'{expected_base}/subdir1/file1.txt',
            f'{expected_base}/subdir2/file2.txt'
        ])

    def test_nested_subdirs_without_includeBase(self):
        """Deeply nested subdirectories should preserve full structure."""
        source, dest = self.create_test_structure('nested_no_base')

        # Create: source/level1/level2/level3/deep.txt
        deep_path = source / 'level1' / 'level2' / 'level3'
        deep_path.mkdir(parents=True)
        (deep_path / 'deep.txt').write_text('deep content')

        # Run: preserve COPY source -r --rel --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/level1/level2/level3/deep.txt
        self.verify_structure(dest, ['level1/level2/level3/deep.txt'])

    def test_nested_subdirs_with_includeBase(self):
        """Deeply nested subdirectories with base should include source name."""
        source, dest = self.create_test_structure('nested_with_base')

        # Create: source/level1/level2/level3/deep.txt
        deep_path = source / 'level1' / 'level2' / 'level3'
        deep_path.mkdir(parents=True)
        (deep_path / 'deep.txt').write_text('deep content')

        # Run: preserve COPY source -r --rel --includeBase --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/source_nested_with_base/level1/level2/level3/deep.txt
        expected_base = source.name
        self.verify_structure(dest, [f'{expected_base}/level1/level2/level3/deep.txt'])

    def test_mixed_files_and_dirs_without_includeBase(self):
        """Files at root and in subdirs should maintain their relative positions."""
        source, dest = self.create_test_structure('mixed_no_base')

        # Create mixed structure
        (source / 'root_file.txt').write_text('root content')
        subdir1 = source / 'subdir1'
        subdir1.mkdir()
        (subdir1 / 'sub_file.txt').write_text('sub content')
        (source / 'another_root.txt').write_text('another root')
        subdir2 = source / 'subdir2'
        subdir2.mkdir()
        (subdir2 / 'deep_file.txt').write_text('deep content')

        # Run: preserve COPY source -r --rel --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: files at root level and subdirs preserved
        self.verify_structure(dest, [
            'root_file.txt',
            'another_root.txt',
            'subdir1/sub_file.txt',
            'subdir2/deep_file.txt'
        ])

    def test_mixed_files_and_dirs_with_includeBase(self):
        """Mixed content with base should all be under source directory name."""
        source, dest = self.create_test_structure('mixed_with_base')

        # Create mixed structure
        (source / 'root_file.txt').write_text('root content')
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'sub_file.txt').write_text('sub content')

        # Run: preserve COPY source -r --rel --includeBase --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: everything under source directory name
        expected_base = source.name
        self.verify_structure(dest, [
            f'{expected_base}/root_file.txt',
            f'{expected_base}/subdir/sub_file.txt'
        ])

    def test_empty_directories_preserved(self):
        """Empty directories should be skipped (no files to copy)."""
        source, dest = self.create_test_structure('empty_dirs')

        # Create: source/empty_dir/ and source/dir_with_file/file.txt
        empty = source / 'empty_dir'
        empty.mkdir()
        with_file = source / 'dir_with_file'
        with_file.mkdir()
        (with_file / 'file.txt').write_text('content')

        # Run: preserve COPY source -r --rel --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: only dir_with_file/file.txt (empty dirs not created)
        self.verify_structure(dest, ['dir_with_file/file.txt'])

    def test_single_file_without_includeBase(self):
        """Copying a single file should place it directly in destination."""
        source_dir, dest = self.create_test_structure('single_file')

        # Create a single file
        source_file = source_dir / 'single.txt'
        source_file.write_text('single file content')

        # Run: preserve COPY source_file --dst dest
        result = self.run_preserve([
            'COPY', str(source_file), '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/single.txt (file at root of dest)
        self.verify_structure(dest, ['single.txt'])

    def test_single_file_with_includeBase(self):
        """Single file with --includeBase includes parent directory name."""
        source_dir, dest = self.create_test_structure('single_file_base')

        # Create a single file
        source_file = source_dir / 'single.txt'
        source_file.write_text('single file content')

        # Run: preserve COPY source_file --includeBase --dst dest
        # With --includeBase, even single files get their parent dir included
        result = self.run_preserve([
            'COPY', str(source_file), '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/source_single_file_base/single.txt (parent dir included)
        parent_name = source_dir.name  # 'source_single_file_base'
        self.verify_structure(dest, [f'{parent_name}/single.txt'])


class TestPathStyleInteraction(unittest.TestCase):
    """Test how different path styles interact with subdirectory preservation."""

    def setUp(self):
        """Create test directory structure."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_path_styles_'))

    def tearDown(self):
        """Clean up test directories."""
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

    def verify_structure(self, dest_dir, expected_paths):
        """Verify the destination directory has the expected structure."""
        actual_paths = set()
        for path in dest_dir.rglob('*'):
            if path.is_file():
                # Skip manifest files - they're expected but not part of structure verification
                if path.name in ['preserve_manifest.json', 'preserve_manifest.yaml']:
                    continue
                relative = path.relative_to(dest_dir)
                actual_paths.add(str(relative).replace('\\', '/'))

        expected = set(expected_paths)
        self.assertEqual(actual_paths, expected,
                        f"Structure mismatch.\nExpected: {sorted(expected)}\nActual: {sorted(actual_paths)}")

    def test_flat_mode_ignores_structure(self):
        """Flat mode should flatten all structure regardless of includeBase."""
        source = self.test_dir / 'source_flat'
        dest = self.test_dir / 'dest_flat'
        source.mkdir()
        dest.mkdir()

        # Create nested structure
        deep = source / 'sub1' / 'sub2'
        deep.mkdir(parents=True)
        (deep / 'file1.txt').write_text('content1')
        (source / 'sub3' / 'file2.txt').parent.mkdir(parents=True)
        (source / 'sub3' / 'file2.txt').write_text('content2')

        # Run: preserve COPY source -r --flat --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--flat', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/file1.txt, dest/file2.txt (all flattened)
        self.verify_structure(dest, ['file1.txt', 'file2.txt'])

    def test_absolute_mode_preserves_full_path(self):
        """Absolute mode should preserve the full absolute path structure."""
        source = self.test_dir / 'source_abs'
        dest = self.test_dir / 'dest_abs'
        source.mkdir()
        dest.mkdir()

        # Create structure
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'file.txt').write_text('content')

        # Run: preserve COPY source -r --abs --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--abs', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Expected: dest/[drive]/full/path/to/source_abs/subdir/file.txt
        # The absolute path structure should be preserved
        # This is tricky to test cross-platform, so we just verify deep nesting
        all_files = list(dest.rglob('file.txt'))
        self.assertEqual(len(all_files), 1, "Should have exactly one file")

        # Verify it's deeply nested (absolute paths create deep structure)
        file_path = all_files[0]
        path_parts = file_path.relative_to(dest).parts
        self.assertGreater(len(path_parts), 2, "Absolute path should create deep nesting")
        self.assertTrue('subdir' in path_parts, "Should preserve subdir in path")

    def test_absolute_mode_with_includeBase(self):
        """Absolute mode with --includeBase should still preserve full path (includeBase ignored in abs mode)."""
        source = self.test_dir / 'source_abs_base'
        dest = self.test_dir / 'dest_abs_base'
        source.mkdir()
        dest.mkdir()

        # Create structure
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'file.txt').write_text('content')

        # Run: preserve COPY source -r --abs --includeBase --dst dest
        result = self.run_preserve([
            'COPY', str(source), '-r', '--abs', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # In absolute mode, --includeBase is typically ignored because
        # the full absolute path is already preserved
        all_files = list(dest.rglob('file.txt'))
        self.assertEqual(len(all_files), 1, "Should have exactly one file")

        # Verify the full path is preserved
        file_path = all_files[0]
        path_parts = file_path.relative_to(dest).parts
        self.assertGreater(len(path_parts), 2, "Absolute path should create deep nesting")
        self.assertTrue('subdir' in path_parts, "Should preserve subdir in path")
        # The source_abs_base directory name should be in the path
        self.assertTrue('source_abs_base' in path_parts, "Should include source directory name")


class TestManifestPathRecording(unittest.TestCase):
    """Test that manifest correctly records paths with different options."""

    def setUp(self):
        """Create test directory structure."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_manifest_paths_'))

    def tearDown(self):
        """Clean up test directories."""
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

    def test_manifest_records_correct_paths(self):
        """Manifest should record the actual paths used."""
        source = self.test_dir / 'source_manifest'
        dest = self.test_dir / 'dest_manifest'
        source.mkdir()
        dest.mkdir()

        # Create structure
        subdir = source / 'subdir'
        subdir.mkdir()
        (subdir / 'file.txt').write_text('content')

        # Run with --includeBase
        result = self.run_preserve([
            'COPY', str(source), '-r', '--rel', '--includeBase', '--dst', str(dest)
        ])

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Check manifest
        manifest_file = dest / 'preserve_manifest.json'
        self.assertTrue(manifest_file.exists(), "Manifest should be created")

        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        # Verify paths are recorded correctly
        self.assertIn('operations', manifest)
        self.assertGreater(len(manifest['operations']), 0)

        # The manifest structure has operations at the top level
        # Each operation records source_path and destination_path directly
        operation = manifest['operations'][0]
        self.assertIn('source_path', operation)
        self.assertIn('destination_path', operation)

        # With --includeBase, the actual file should be under the source directory name
        # Check that the copied file exists with the source base name included
        expected_file = dest / source.name / 'subdir' / 'file.txt'
        self.assertTrue(expected_file.exists(), f"File should exist at {expected_file}")


if __name__ == '__main__':
    unittest.main()