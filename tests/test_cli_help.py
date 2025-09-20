"""
Tests for CLI help system to prevent regression.

This module tests the three levels of help output to ensure:
1. `preserve` with no args shows friendly intro
2. `preserve -h` shows argparse help with examples
3. `preserve --help` is identical to `-h`
"""

import unittest
import subprocess
import sys
import os


class TestCLIHelp(unittest.TestCase):
    """Test cases for CLI help output."""

    def setUp(self):
        """Set up test environment."""
        # Get the path to preserve module
        self.preserve_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'preserve')

    def run_preserve(self, args=None):
        """Run preserve command and capture output."""
        cmd = [sys.executable, '-m', 'preserve']
        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        return result.stdout, result.stderr, result.returncode

    def test_no_args_shows_friendly_help(self):
        """Test that `preserve` with no args shows friendly intro with examples."""
        stdout, stderr, returncode = self.run_preserve()

        # Should exit with 0 (success) for help display
        self.assertEqual(returncode, 0)

        # Check for key elements of friendly help
        self.assertIn('preserve v', stdout)
        self.assertIn('A tool for preserving files', stdout)
        self.assertIn('Usage:', stdout)
        self.assertIn('Operations:', stdout)
        self.assertIn('Examples:', stdout)

        # Should have multiple examples
        self.assertIn('Copy entire directory with relative paths', stdout)
        self.assertIn('Copy files matching a glob pattern', stdout)
        self.assertIn('Verify files in destination', stdout)
        self.assertIn('Restore files to original locations', stdout)

        # Should NOT have argparse usage line
        self.assertNotIn('usage: preserve [-h]', stdout)

    def test_dash_h_shows_argparse_with_examples(self):
        """Test that `preserve -h` shows argparse help with examples epilog."""
        stdout, stderr, returncode = self.run_preserve(['-h'])

        # Should exit with 0 (success)
        self.assertEqual(returncode, 0)

        # Check for argparse elements
        self.assertIn('usage: preserve [-h]', stdout)
        self.assertIn('positional arguments:', stdout)
        self.assertIn('options:', stdout)
        self.assertIn('-h, --help', stdout)
        self.assertIn('--version, -V', stdout)

        # Check for examples in epilog
        self.assertIn('Examples:', stdout)
        self.assertIn('Copy entire directory with relative paths', stdout)
        self.assertIn('preserve COPY', stdout)
        self.assertIn('preserve VERIFY', stdout)

    def test_double_dash_help_same_as_dash_h(self):
        """Test that `preserve --help` output is identical to `-h`."""
        stdout_h, _, _ = self.run_preserve(['-h'])
        stdout_help, _, _ = self.run_preserve(['--help'])

        # The outputs should be identical
        self.assertEqual(stdout_h, stdout_help)

    def test_no_duplicate_help_sections(self):
        """Test that help doesn't have duplicate sections."""
        stdout, stderr, returncode = self.run_preserve(['-h'])

        # Count occurrences of key sections - should only appear once
        usage_count = stdout.count('usage: preserve')
        examples_count = stdout.count('Examples:')
        positional_count = stdout.count('positional arguments:')

        self.assertEqual(usage_count, 1, "Usage line should appear exactly once")
        self.assertEqual(examples_count, 1, "Examples section should appear exactly once")
        self.assertEqual(positional_count, 1, "Positional arguments should appear exactly once")

    def test_command_help_works(self):
        """Test that command-specific help works (e.g., preserve COPY --help)."""
        stdout, stderr, returncode = self.run_preserve(['COPY', '--help'])

        # Should exit with 0 (success)
        self.assertEqual(returncode, 0)

        # Should show COPY-specific help
        self.assertIn('usage: preserve COPY', stdout)
        self.assertIn('Source options:', stdout)
        self.assertIn('Destination options:', stdout)
        self.assertIn('--dst', stdout)


if __name__ == '__main__':
    unittest.main()