#!/usr/bin/env python3
"""
Test script for the --rel mode of preserve CLI.

This script creates a test directory structure, copies files using the --rel mode,
and verifies that the subdirectory structure is maintained.
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

def create_test_structure(base_dir):
    """Create a test directory structure with files at different depths"""
    # Create directories
    (base_dir / "level1").mkdir(parents=True, exist_ok=True)
    (base_dir / "level1" / "level2").mkdir(parents=True, exist_ok=True)
    (base_dir / "level1" / "level2" / "level3").mkdir(parents=True, exist_ok=True)
    
    # Create files at different depths
    (base_dir / "root_file.txt").write_text("This is a file at the root level")
    (base_dir / "level1" / "level1_file.txt").write_text("This is a file at level 1")
    (base_dir / "level1" / "level2" / "level2_file.txt").write_text("This is a file at level 2")
    (base_dir / "level1" / "level2" / "level3" / "level3_file.txt").write_text("This is a file at level 3")
    
    print(f"Created test structure in {base_dir}")
    print("Files created:")
    for path in base_dir.glob("**/*.txt"):
        print(f"  {path.relative_to(base_dir)}")

def run_preserve_copy(source_dir, dest_dir, options):
    """Run preserve COPY command with the given options"""
    cmd = [
        "python", "-m", "preserve", "COPY",
        "--glob", "**/*.txt",
        "--srchPath", str(source_dir),
        "--dst", str(dest_dir),
    ] + options
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
    
    return result.returncode == 0

def verify_structure(source_dir, dest_dir, mode):
    """Verify that the directory structure was preserved according to the mode"""
    print(f"\nVerifying structure for mode: {mode}")
    
    # List all files in both directories
    source_files = list(source_dir.glob("**/*.txt"))
    dest_files = list(dest_dir.glob("**/*.txt"))
    
    print(f"Source files: {len(source_files)}")
    print(f"Destination files: {len(dest_files)}")
    
    if len(source_files) != len(dest_files):
        print("❌ ERROR: Number of files doesn't match")
        return False
    
    if mode == "--rel":
        # For relative mode, verify directory structure is preserved
        # Get paths relative to their respective base directories
        rel_source_paths = [p.relative_to(source_dir) for p in source_files]
        
        # Check if each relative path exists in the destination
        success = True
        for rel_path in rel_source_paths:
            dest_path = dest_dir / rel_path
            if not dest_path.exists():
                print(f"❌ ERROR: Expected {rel_path} not found in destination")
                success = False
        
        if success:
            print("✅ SUCCESS: All files found with preserved directory structure")
        return success
    
    elif mode == "--flat":
        # For flat mode, verify all files are in the root of dest_dir
        for file in dest_files:
            if file.parent != dest_dir:
                print(f"❌ ERROR: File {file} is not in the root of destination directory")
                return False
        
        print("✅ SUCCESS: All files are in the root directory (flat structure)")
        return True
    
    elif mode == "--abs":
        # For absolute mode, directory structure should match the absolute paths
        # This is more complex and depends on the platform
        print("Absolute mode verification not implemented in this test")
        return True

def run_test():
    """Run the tests for different modes"""
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "source"
        source_dir.mkdir()
        
        # Create test structure
        create_test_structure(source_dir)
        
        # Test --rel mode
        rel_dest = temp_path / "rel_dest"
        rel_dest.mkdir()
        rel_success = run_preserve_copy(source_dir, rel_dest, ["--rel", "--verbose"])
        if rel_success:
            rel_verified = verify_structure(source_dir, rel_dest, "--rel")
        else:
            rel_verified = False
        
        # Test --flat mode for comparison
        flat_dest = temp_path / "flat_dest"
        flat_dest.mkdir()
        flat_success = run_preserve_copy(source_dir, flat_dest, ["--flat"])
        if flat_success:
            flat_verified = verify_structure(source_dir, flat_dest, "--flat")
        else:
            flat_verified = False
        
        # Print summary
        print("\n=== TEST SUMMARY ===")
        print(f"Relative mode: {'✅ PASSED' if rel_verified else '❌ FAILED'}")
        print(f"Flat mode: {'✅ PASSED' if flat_verified else '❌ FAILED'}")
        
        # List directory structures for manual verification
        print("\n=== DIRECTORY STRUCTURES ===")
        print("\nSource Structure:")
        subprocess.run(["find", str(source_dir), "-type", "f", "-name", "*.txt"], text=True)
        
        print("\nRelative Mode Destination Structure:")
        subprocess.run(["find", str(rel_dest), "-type", "f", "-name", "*.txt"], text=True)
        
        print("\nFlat Mode Destination Structure:")
        subprocess.run(["find", str(flat_dest), "-type", "f", "-name", "*.txt"], text=True)

if __name__ == "__main__":
    run_test()