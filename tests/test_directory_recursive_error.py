"""
Test cases for directory operations and error messages when --recursive is not specified.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest
import logging
import argparse

# Add the parent directory to the path so we can import preserve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preserve import preserve


class TestDirectoryRecursiveError(unittest.TestCase):
    """Test cases for directory operations without --recursive flag"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for our test runs
        self.test_base = Path(".test-runs")
        if self.test_base.exists():
            shutil.rmtree(self.test_base)
        self.test_base.mkdir(exist_ok=True)

        # Create source directory with some test files
        self.source_dir = self.test_base / "source"
        self.source_dir.mkdir(exist_ok=True)

        # Create some test files
        (self.source_dir / "file1.txt").write_text("Test file 1 content")
        (self.source_dir / "file2.txt").write_text("Test file 2 content")

        # Create a subdirectory with files
        self.source_subdir = self.source_dir / "subdir"
        self.source_subdir.mkdir(exist_ok=True)
        (self.source_subdir / "file3.txt").write_text("Test file 3 content")
        (self.source_subdir / "file4.txt").write_text("Test file 4 content")

        # Create destination directory
        self.dest_dir = self.test_base / "dest"
        self.dest_dir.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up after test"""
        if self.test_base.exists():
            shutil.rmtree(self.test_base)

    def test_copy_directory_without_recursive_shows_warning(self):
        """Test that copying a directory without --recursive flag shows a helpful warning message"""

        # Mock sys.argv to simulate command line arguments
        test_args = [
            'preserve', 'COPY',
            str(self.source_dir),
            '--dst', str(self.dest_dir)
        ]

        with patch.object(sys, 'argv', test_args):
            # Capture log output at WARNING level
            with self.assertLogs('preserve', level='WARNING') as cm:
                # Parse arguments and run the copy operation
                parser = preserve.create_parser()
                args = parser.parse_args(test_args[1:])

                # Set up logger
                logger = logging.getLogger('preserve')
                logger.setLevel(logging.DEBUG)

                # Run the copy operation - should return 0 (success) but with warnings
                result = preserve.handle_copy_operation(args, logger)
                assert result == 0  # Should succeed but with warning

                # Check that the warning messages were logged
                warning_messages = '\n'.join(cm.output)

                # Verify the helpful warning message components
                assert f"WARNING: '{self.source_dir}' contains subdirectories with files that will NOT be copied" in warning_messages
                assert "Use --recursive flag to include files from subdirectories" in warning_messages
                assert "To copy all files from a directory" in warning_messages
                assert "--recursive" in warning_messages
                assert "-r" in warning_messages
                assert "--includeBase" in warning_messages

    def test_move_directory_without_recursive_shows_warning(self):
        """Test that moving a directory without --recursive flag shows a helpful warning message"""

        # Mock sys.argv to simulate command line arguments
        test_args = [
            'preserve', 'MOVE',
            str(self.source_dir),
            '--dst', str(self.dest_dir)
        ]

        with patch.object(sys, 'argv', test_args):
            # Capture log output at WARNING level
            with self.assertLogs('preserve', level='WARNING') as cm:
                # Parse arguments and run the move operation
                parser = preserve.create_parser()
                args = parser.parse_args(test_args[1:])

                # Set up logger
                logger = logging.getLogger('preserve')
                logger.setLevel(logging.DEBUG)

                # Run the move operation - should return 0 (success) but with warnings
                result = preserve.handle_move_operation(args, logger)
                assert result == 0  # Should succeed but with warning

                # Check that the warning messages were logged
                warning_messages = '\n'.join(cm.output)

                # Verify the helpful warning message components
                assert f"WARNING: '{self.source_dir}' contains subdirectories with files that will NOT be moved" in warning_messages
                assert "Use --recursive flag to include files from subdirectories" in warning_messages
                assert "To move all files from a directory" in warning_messages
                assert "--recursive" in warning_messages
                assert "-r" in warning_messages
                assert "--includeBase" in warning_messages

    def test_copy_with_recursive_flag_works(self):
        """Test that copying a directory WITH --recursive flag works correctly"""

        # Mock sys.argv to simulate command line arguments
        test_args = [
            'preserve', 'COPY',
            str(self.source_dir),
            '--recursive',
            '--dst', str(self.dest_dir)
        ]

        with patch.object(sys, 'argv', test_args):
            # Parse arguments
            parser = preserve.create_parser()
            args = parser.parse_args(test_args[1:])

            # Set up logger
            logger = logging.getLogger('preserve')
            logger.setLevel(logging.DEBUG)

            # Find source files - should find files with recursive flag
            source_files = preserve.find_files_from_args(args)

            # Should find all 4 files
            assert len(source_files) == 4

            # Check that all expected files are found
            file_names = [f.name for f in source_files]
            assert 'file1.txt' in file_names
            assert 'file2.txt' in file_names
            assert 'file3.txt' in file_names
            assert 'file4.txt' in file_names

    def test_copy_file_directly_works_without_recursive(self):
        """Test that copying a single file directly works without --recursive flag"""

        single_file = self.source_dir / "file1.txt"

        # Mock sys.argv to simulate command line arguments
        test_args = [
            'preserve', 'COPY',
            str(single_file),
            '--dst', str(self.dest_dir)
        ]

        with patch.object(sys, 'argv', test_args):
            # Parse arguments
            parser = preserve.create_parser()
            args = parser.parse_args(test_args[1:])

            # Set up logger
            logger = logging.getLogger('preserve')
            logger.setLevel(logging.DEBUG)

            # Find source files - should find the single file
            source_files = preserve.find_files_from_args(args)

            # Should find exactly 1 file
            assert len(source_files) == 1
            assert source_files[0].name == 'file1.txt'

    def test_copy_directory_with_only_subdirs_shows_error(self):
        """Test that copying a directory with only subdirectories (no top-level files) shows an error"""

        # Remove top-level files, keep only subdirectory files
        (self.source_dir / "file1.txt").unlink()
        (self.source_dir / "file2.txt").unlink()

        # Mock sys.argv to simulate command line arguments
        test_args = [
            'preserve', 'COPY',
            str(self.source_dir),
            '--dst', str(self.dest_dir)
        ]

        with patch.object(sys, 'argv', test_args):
            # Parse arguments
            parser = preserve.create_parser()
            args = parser.parse_args(test_args[1:])

            # Set up logger
            logger = logging.getLogger('preserve')
            logger.setLevel(logging.DEBUG)

            # Run the copy operation - should return 1 (error) when no files found
            result = preserve.handle_copy_operation(args, logger)
            assert result == 1

    def test_help_text_includes_examples(self):
        """Test that the COPY --help text includes examples"""

        # Create parser and get help text
        parser = preserve.create_parser()

        # Get the COPY subparser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]

        copy_parser = None
        for action in subparsers_actions:
            for choice, subparser in action.choices.items():
                if choice == 'COPY':
                    copy_parser = subparser
                    break

        assert copy_parser is not None

        # Get the help text
        help_text = copy_parser.format_help()

        # Check that examples are included
        assert "Common usage patterns:" in help_text
        assert "preserve COPY" in help_text
        assert "--recursive" in help_text
        assert "--includeBase" in help_text
        assert "Note: When copying directories" in help_text


if __name__ == '__main__':
    # Run the tests
    unittest.main()