#!/usr/bin/env python3
"""
Generate consistent test data structure for preserve testing.

This script creates a standardized directory structure in test-runs/ that can be
used for manual testing and automated unit tests.
"""

import os
import sys
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
import random
import string

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDataGenerator:
    """Generate test data for preserve operations."""

    def __init__(self, base_dir=None):
        """Initialize the test data generator."""
        if base_dir is None:
            # Default to project root/test-runs, not relative to tests directory
            project_root = Path(__file__).parent.parent
            self.base_dir = project_root / "test-runs"
        else:
            self.base_dir = Path(base_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_dir = self.base_dir / f"test_{self.timestamp}"

    def clean_previous_runs(self, keep_last=3):
        """Clean up old test runs, keeping the most recent ones."""
        if not self.base_dir.exists():
            return

        # Get all test directories
        test_dirs = sorted([
            d for d in self.base_dir.iterdir()
            if d.is_dir() and d.name.startswith("test_")
        ])

        # Remove old directories if we have too many
        if len(test_dirs) > keep_last:
            for old_dir in test_dirs[:-keep_last]:
                print(f"Removing old test directory: {old_dir}")
                shutil.rmtree(old_dir)

    def create_file_with_content(self, path, content=None, size_kb=1):
        """Create a file with specific content or random data."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if content is None:
            # Generate random content of specified size
            content = ''.join(random.choices(
                string.ascii_letters + string.digits + ' \n',
                k=size_kb * 1024
            ))

        path.write_text(content, encoding='utf-8')

        # Set specific modification time for testing
        mod_time = datetime.now() - timedelta(days=random.randint(1, 30))
        os.utime(path, (mod_time.timestamp(), mod_time.timestamp()))

        return path

    def create_binary_file(self, path, size_kb=10):
        """Create a binary file with random data."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate random binary data
        data = os.urandom(size_kb * 1024)
        path.write_bytes(data)

        return path

    def generate_basic_structure(self):
        """Generate a basic directory structure for testing."""
        print(f"Creating test structure in: {self.test_dir}")

        # Create main test directory
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Create source directories
        source_dir = self.test_dir / "source"

        # Simple files in root
        files_created = []
        files_created.append(
            self.create_file_with_content(
                source_dir / "readme.txt",
                "This is a test readme file for preserve testing.\n"
            )
        )
        files_created.append(
            self.create_file_with_content(
                source_dir / "config.json",
                json.dumps({"test": True, "version": "1.0"}, indent=2)
            )
        )

        # Documents directory
        docs_dir = source_dir / "documents"
        files_created.append(
            self.create_file_with_content(
                docs_dir / "report.txt",
                "Annual Report 2024\n" + "=" * 50 + "\n" * 5
            )
        )
        files_created.append(
            self.create_file_with_content(
                docs_dir / "notes.md",
                "# Project Notes\n\n- Item 1\n- Item 2\n"
            )
        )

        # Nested structure
        project_dir = source_dir / "project" / "src" / "components"
        files_created.append(
            self.create_file_with_content(
                project_dir / "main.py",
                "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()\n"
            )
        )
        files_created.append(
            self.create_file_with_content(
                project_dir / "utils.py",
                "def helper():\n    return 'Helper function'\n"
            )
        )

        # Binary files
        media_dir = source_dir / "media"
        files_created.append(
            self.create_binary_file(media_dir / "image.bin", size_kb=50)
        )
        files_created.append(
            self.create_binary_file(media_dir / "data.dat", size_kb=25)
        )

        # Files with special characters (Windows-safe)
        special_dir = source_dir / "special_chars"
        files_created.append(
            self.create_file_with_content(
                special_dir / "file with spaces.txt",
                "This file has spaces in its name"
            )
        )
        files_created.append(
            self.create_file_with_content(
                special_dir / "file-with-dashes.txt",
                "This file has dashes in its name"
            )
        )

        # Large file for performance testing
        files_created.append(
            self.create_file_with_content(
                source_dir / "large_file.txt",
                size_kb=500
            )
        )

        # Create file list for loadIncludes testing
        file_list_path = self.test_dir / "files_to_copy.txt"
        with open(file_list_path, 'w') as f:
            # Write absolute paths of some files
            f.write(str(files_created[0].absolute()) + "\n")  # readme.txt
            f.write(str(files_created[2].absolute()) + "\n")  # report.txt
            f.write(str(files_created[4].absolute()) + "\n")  # main.py

        # Create destination directories for testing
        (self.test_dir / "dest_flat").mkdir(exist_ok=True)
        (self.test_dir / "dest_rel").mkdir(exist_ok=True)
        (self.test_dir / "dest_abs").mkdir(exist_ok=True)
        (self.test_dir / "dest_multiple").mkdir(exist_ok=True)

        print(f"Created {len(files_created)} files in test structure")
        return self.test_dir

    def generate_manifest_test_structure(self):
        """Generate structure specifically for testing manifest numbering."""
        manifest_dir = self.test_dir / "manifest_tests"
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple source directories for sequential operations
        for i in range(1, 4):
            src_dir = manifest_dir / f"source_{i}"
            src_dir.mkdir(exist_ok=True)

            # Create some files in each
            for j in range(1, 3):
                self.create_file_with_content(
                    src_dir / f"file_{j}.txt",
                    f"Source {i}, File {j}"
                )

        # Create a shared destination
        dest_dir = manifest_dir / "shared_dest"
        dest_dir.mkdir(exist_ok=True)

        # Create file lists for each source
        for i in range(1, 4):
            file_list = manifest_dir / f"files_{i}.txt"
            src_dir = manifest_dir / f"source_{i}"
            files = list(src_dir.glob("*.txt"))
            with open(file_list, 'w') as f:
                for file in files:
                    f.write(str(file.absolute()) + "\n")

        print(f"Created manifest test structure in: {manifest_dir}")
        return manifest_dir

    def generate_verification_test_structure(self):
        """Generate structure for testing verification operations."""
        verify_dir = self.test_dir / "verify_tests"
        verify_dir.mkdir(parents=True, exist_ok=True)

        # Create source with files
        src_dir = verify_dir / "source"
        files = []
        for i in range(1, 6):
            path = self.create_file_with_content(
                src_dir / f"verify_{i}.txt",
                f"Verification test file {i}\n" * 10
            )
            files.append(path)

        # Create a preserved copy
        preserved_dir = verify_dir / "preserved"
        preserved_dir.mkdir(exist_ok=True)

        # Copy files and track hashes
        hash_data = {}
        for file in files:
            dest = preserved_dir / file.name
            shutil.copy2(file, dest)

            # Calculate hash
            with open(file, 'rb') as f:
                hash_data[file.name] = hashlib.sha256(f.read()).hexdigest()

        # Modify one source file (to test source changes)
        files[0].write_text("Modified content after preservation")

        # Corrupt one preserved file (to test corruption detection)
        (preserved_dir / files[1].name).write_text("Corrupted content")

        # Delete one source file (to test missing source)
        files[2].unlink()

        # Save hash manifest for reference
        manifest = {
            "files": hash_data,
            "notes": {
                files[0].name: "source modified after preserve",
                files[1].name: "preserved copy corrupted",
                files[2].name: "source deleted after preserve",
                files[3].name: "should match",
                files[4].name: "should match"
            }
        }

        manifest_path = verify_dir / "test_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"Created verification test structure in: {verify_dir}")
        return verify_dir

    def generate_all(self):
        """Generate all test structures."""
        print(f"\n{'=' * 60}")
        print(f"Preserve Test Data Generator")
        print(f"{'=' * 60}\n")

        # Clean old runs
        self.clean_previous_runs(keep_last=3)

        # Generate structures
        basic_dir = self.generate_basic_structure()
        manifest_dir = self.generate_manifest_test_structure()
        verify_dir = self.generate_verification_test_structure()

        # Create a summary file
        summary = {
            "timestamp": self.timestamp,
            "directories": {
                "base": str(self.test_dir),
                "basic": str(basic_dir),
                "manifest_tests": str(manifest_dir),
                "verify_tests": str(verify_dir)
            },
            "test_commands": [
                f"preserve COPY \"{basic_dir}/source\" -r --dst \"{basic_dir}/dest_rel\" --rel --includeBase",
                f"preserve COPY --loadIncludes \"{self.test_dir}/files_to_copy.txt\" --dst \"{basic_dir}/dest_flat\" --flat",
                f"preserve RESTORE --src \"{basic_dir}/dest_rel\" --list",
                f"preserve VERIFY --dst \"{basic_dir}/dest_rel\" --hash SHA256"
            ]
        }

        summary_path = self.test_dir / "test_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print(f"Test data generation complete!")
        print(f"Base directory: {self.test_dir}")
        print(f"Summary saved to: {summary_path}")
        print(f"\nExample test commands:")
        for cmd in summary["test_commands"]:
            print(f"  {cmd}")
        print(f"{'=' * 60}\n")

        return self.test_dir


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate test data for preserve")
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Base directory for test data (default: project_root/test-runs)"
    )
    parser.add_argument(
        "--keep-last",
        type=int,
        default=3,
        help="Number of previous test runs to keep (default: 3)"
    )

    args = parser.parse_args()

    generator = TestDataGenerator(args.base_dir)
    generator.generate_all()


if __name__ == "__main__":
    main()