#!/usr/bin/env python3
"""
Test script for relative path mode fallback behavior.

This script tests the new behavior where --rel mode falls back to absolute path style
when no common base directory can be found, instead of defaulting to a flat structure.

Usage:
    python test_rel_fallback.py

The script:
1. Creates a test directory structure with files from diverse locations
2. Runs preserve with --rel mode to copy these files
3. Verifies that the files are copied with directory structure preserved (not flat)
"""

import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path

# Get the root of the project
script_dir = Path(__file__).parent
project_root = script_dir.parent

def setup_test_dirs():
    """Set up test directories with files from diverse locations."""
    # Create base temp dir
    base_dir = tempfile.mkdtemp(prefix="preserve_test_")
    base_path = Path(base_dir)
    
    # Create diverse directory structure
    dir1 = base_path / "dir1" / "subdir1"
    dir2 = base_path / "completely_different" / "path" / "structure"
    dir3 = base_path / "another" / "very" / "different" / "location"
    
    # Create directories
    dir1.mkdir(parents=True, exist_ok=True)
    dir2.mkdir(parents=True, exist_ok=True)
    dir3.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    file1 = dir1 / "test1.txt"
    file2 = dir2 / "test2.txt"
    file3 = dir3 / "test3.txt"
    
    # Write content to files
    file1.write_text("Content for test1")
    file2.write_text("Content for test2")
    file3.write_text("Content for test3")
    
    # Create a list of files to copy
    files_list = base_path / "files.txt"
    with open(files_list, "w") as f:
        f.write(f"{file1}\n{file2}\n{file3}\n")
    
    # Create destination directory
    dest_dir = base_path / "destination"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "base_dir": base_dir,
        "file1": str(file1),
        "file2": str(file2),
        "file3": str(file3),
        "files_list": str(files_list),
        "dest_dir": str(dest_dir)
    }

def run_preserve(test_dirs):
    """Run preserve with --rel mode."""
    # Add the project root to the path so we can import the preserve module
    sys.path.insert(0, str(project_root))
    
    # Directly call the preserve code from Python rather than as a script
    try:
        import preserve.preserve as preserve_module
        
        # Create a dummy args object similar to what argparse would create
        from types import SimpleNamespace
        args = SimpleNamespace()
        args.operation = "COPY"
        args.source_files = []
        args.loadIncludes = test_dirs["files_list"]
        args.dst = test_dirs["dest_dir"]
        args.rel = True
        args.abs = False
        args.flat = False
        args.includeBase = False
        args.overwrite = False
        args.recursive = True
        args.preserveAttrs = True
        args.verify = True
        args.hash = "SHA256"
        args.quiet = False
        args.verbose = 1
        args.dryRun = False
        args.forceOutput = False
        args.noLogFile = True
        args.report = None
        args.manifestPath = None
        args.createDazzlelinks = False
        args.dazzlelinkDir = None
        args.dazzlelinkMode = "info"
        
        # Run preserve
        try:
            preserve_module.handle_copy_operation(args)
            return SimpleNamespace(stdout="SUCCESS", stderr="", returncode=0)
        except Exception as e:
            import traceback
            return SimpleNamespace(stdout="", stderr=f"Error: {str(e)}\n{traceback.format_exc()}", returncode=1)
    except ImportError as e:
        print(f"Error importing preserve module: {e}")
        # Fall back to command-line invocation
        preserve_script = project_root / "preserve" / "preserve.py"
        
        cmd = [
            sys.executable,
            "-m", "preserve.preserve",
            "COPY",
            "--loadIncludes", test_dirs["files_list"],
            "--dst", test_dirs["dest_dir"],
            "--rel"  # Use relative mode
        ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("\nSTDOUT:")
    print(result.stdout)
    
    print("\nSTDERR:")
    print(result.stderr)
    
    return result

def verify_results(test_dirs):
    """Verify that files are copied with directory structure preserved."""
    dest_dir = Path(test_dirs["dest_dir"])
    
    # Check for files in the destination directory
    print("\nChecking destination directory structure:")
    
    # Walk the directory and print all files
    all_files = []
    for root, dirs, files in os.walk(dest_dir):
        for file in files:
            rel_path = Path(root).relative_to(dest_dir)
            if rel_path == Path('.'):
                file_path = Path(file)
            else:
                file_path = rel_path / file
            all_files.append(str(file_path))
    
    print(f"Files found in destination: {all_files}")
    
    # Check if the structure is preserved (not flat)
    # If it's flat, all files would be directly in the destination directory
    is_flat = all(Path(f).parent == Path('.') for f in all_files)
    print(f"Structure is {'flat' if is_flat else 'preserved'}")
    
    # Check if at least some of our directory structure is preserved
    # We'll check if at least one file has a path depth > 1
    has_structure = any(len(Path(f).parts) > 1 for f in all_files)
    print(f"Directory structure is {'preserved' if has_structure else 'not preserved'}")
    
    return not is_flat and has_structure

def main():
    """Main function."""
    print("Testing relative path mode fallback behavior")
    print("===========================================")
    
    # Set up test directories
    test_dirs = setup_test_dirs()
    print(f"Created test directory: {test_dirs['base_dir']}")
    
    try:
        # Run preserve
        result = run_preserve(test_dirs)
        
        # Verify results
        success = verify_results(test_dirs)
        
        if success:
            print("\nTEST PASSED: Directory structure was preserved!")
        else:
            print("\nTEST FAILED: Directory structure was not preserved!")
        
    finally:
        # Uncomment to clean up test directory
        # print(f"Cleaning up test directory: {test_dirs['base_dir']}")
        # shutil.rmtree(test_dirs['base_dir'])
        print(f"Test directory for manual inspection: {test_dirs['base_dir']}")

if __name__ == "__main__":
    main()