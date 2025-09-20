#!/usr/bin/env python3
"""
Test suite for CLI option parsing to ensure all documented options are accepted.

This test suite was created to prevent regression after options were lost during
code reorganization (see Issue #19).
"""

import unittest
import argparse
from preserve.cli import create_parser, _add_source_args, _add_destination_args


class TestCLIOptions(unittest.TestCase):
    """Test that all CLI options are properly defined and accepted."""

    def setUp(self):
        """Create a fresh parser for each test."""
        self.parser = create_parser()

    def test_source_args_all_options_accepted(self):
        """Test that all source-related arguments are accepted."""
        # Test basic source arguments
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest', 'file1.txt', 'file2.txt'])
        self.assertEqual(args.sources, ['file1.txt', 'file2.txt'])

        # Test glob pattern
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest', '--glob', '*.txt'])
        self.assertEqual(args.glob, ['*.txt'])

        # Test multiple glob patterns
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest', '--glob', '*.txt', '--glob', '*.py'])
        self.assertEqual(args.glob, ['*.txt', '*.py'])

        # Test regex pattern
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest', '--regex', '.*\\.txt$'])
        self.assertEqual(args.regex, ['.*\\.txt$'])

        # Test include/exclude
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--include', 'important.txt',
                                      '--exclude', 'temp.txt'])
        self.assertEqual(args.include, ['important.txt'])
        self.assertEqual(args.exclude, ['temp.txt'])

        # Test loadIncludes/loadExcludes
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--loadIncludes', 'includes.txt',
                                      '--loadExcludes', 'excludes.txt'])
        self.assertEqual(args.loadIncludes, 'includes.txt')
        self.assertEqual(args.loadExcludes, 'excludes.txt')

        # Test recursion options
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest', '-r',
                                      '--max-depth', '3',
                                      '--follow-symlinks'])
        self.assertTrue(args.recursive)
        self.assertEqual(args.max_depth, 3)
        self.assertTrue(args.follow_symlinks)

        # Test newer-than filter
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--newer-than', '7d'])
        self.assertEqual(args.newer_than, '7d')

        # Test srchPath
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--srchPath', '/path1',
                                      '--srchPath', '/path2'])
        self.assertEqual(args.srchPath, ['/path1', '/path2'])

        # Test includeBase
        args = self.parser.parse_args(['COPY', 'dir/', '--dst', '/tmp/dest',
                                      '--recursive', '--includeBase'])
        self.assertTrue(args.includeBase)

    def test_append_action_multiple_values(self):
        """Test that append actions work with multiple values."""
        # Test multiple includes
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--include', 'file1.txt',
                                      '--include', 'file2.txt',
                                      '--include', 'file3.txt'])
        self.assertEqual(args.include, ['file1.txt', 'file2.txt', 'file3.txt'])

        # Test multiple excludes
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--exclude', 'temp/',
                                      '--exclude', '*.log',
                                      '--exclude', 'cache/'])
        self.assertEqual(args.exclude, ['temp/', '*.log', 'cache/'])

        # Test multiple regex patterns
        args = self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                      '--regex', '.*\\.txt$',
                                      '--regex', '.*\\.py$'])
        self.assertEqual(args.regex, ['.*\\.txt$', '.*\\.py$'])

    def test_destination_args_all_options_accepted(self):
        """Test that all destination-related arguments are accepted."""
        # Test preserve-dir option
        args = self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                      '--preserve-dir'])
        self.assertTrue(args.preserve_dir)

        # Test custom manifest filename
        args = self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                      '--manifest', 'custom_manifest.json'])
        self.assertEqual(args.manifest, 'custom_manifest.json')

        # Test no-manifest option
        args = self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                      '--no-manifest'])
        self.assertTrue(args.no_manifest)

    def test_mutually_exclusive_groups(self):
        """Test that mutually exclusive groups work correctly."""
        # Can't use both sources and --srchPath (they're mutually exclusive)
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                   '--srchPath', '/path1'])

        # Can't use both --glob and --regex (they're mutually exclusive)
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['COPY', '--dst', '/tmp/dest',
                                   '--glob', '*.txt',
                                   '--regex', '.*\\.txt$'])

    def test_path_args_mutually_exclusive(self):
        """Test that path style arguments are mutually exclusive."""
        # Can't use multiple path styles
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                   '--rel', '--abs'])

        with self.assertRaises(SystemExit):
            self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                   '--abs', '--flat'])

        with self.assertRaises(SystemExit):
            self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                   '--rel', '--flat'])

    def test_operation_specific_args(self):
        """Test that operation-specific arguments work."""
        # COPY-specific args
        args = self.parser.parse_args(['COPY', 'file.txt', '--dst', '/tmp/dest',
                                      '--dry-run', '--overwrite',
                                      '--no-preserve-attrs'])
        self.assertTrue(args.dry_run)
        self.assertTrue(args.overwrite)
        self.assertTrue(args.no_preserve_attrs)

        # MOVE-specific args
        args = self.parser.parse_args(['MOVE', 'file.txt', '--dst', '/tmp/dest',
                                      '--force'])
        self.assertTrue(args.force)

        # VERIFY-specific args
        args = self.parser.parse_args(['VERIFY', '--dst', '/tmp/dest',
                                      '--check', 'both',
                                      '--auto',
                                      '--manifest', 'manifest.json',
                                      '--alt-src', '/alt/path'])
        self.assertEqual(args.check, 'both')
        self.assertTrue(args.auto)
        self.assertEqual(args.manifest, 'manifest.json')
        self.assertEqual(args.alt_src, ['/alt/path'])

        # RESTORE-specific args
        args = self.parser.parse_args(['RESTORE', '--src', '/backup',
                                      '--list', '--force',
                                      '--use-dazzlelinks'])
        self.assertTrue(args.list)
        self.assertTrue(args.force)
        self.assertTrue(args.use_dazzlelinks)

    def test_help_examples_import(self):
        """Test that help examples module is properly imported."""
        from preserve.cli import display_help_with_examples
        from preserve.help import examples

        # Verify the function exists and imports are correct
        self.assertTrue(callable(display_help_with_examples))
        self.assertTrue(hasattr(examples, 'get_operation_examples'))

    def test_all_cli_helper_functions_present(self):
        """Test that all CLI helper functions are defined."""
        from preserve import cli

        # Check all helper functions exist
        self.assertTrue(hasattr(cli, '_add_source_args'))
        self.assertTrue(hasattr(cli, '_add_destination_args'))
        self.assertTrue(hasattr(cli, '_add_path_args'))
        self.assertTrue(hasattr(cli, '_add_verification_args'))
        self.assertTrue(hasattr(cli, '_add_dazzlelink_args'))
        self.assertTrue(hasattr(cli, 'display_help_with_examples'))
        self.assertTrue(hasattr(cli, 'create_parser'))


if __name__ == '__main__':
    unittest.main()