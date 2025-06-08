#!/usr/bin/env python3
"""
Test coverage for specific files with 70% requirement
Example usage for new code coverage checking
"""

import os
import subprocess
import sys


def test_file_coverage(files, coverage_threshold=70):
    """Test coverage for specific files"""
    if isinstance(files, str):
        files = [files]

    print(
        f"Testing coverage for {len(files)} files with {coverage_threshold}% threshold:"
    )
    for file in files:
        print(f"  - {file}")

    # Build coverage command for specific files
    coverage_sources = ",".join(files)
    cmd = [
        "python",
        "-m",
        "pytest",
        f"--cov={coverage_sources}",
        "--cov-report=term-missing",
        f"--cov-fail-under={coverage_threshold}",
        "-v",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print(
            f" Coverage check passed for specified files ({coverage_threshold}%+ required)"
        )
        return True
    except subprocess.CalledProcessError:
        print(
            f" Coverage check failed - files do not meet {coverage_threshold}% coverage requirement"
        )
        return False


def main():
    """Main function with example usage"""
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/test_specific_coverage.py <file1> [file2] ..."
        )
        print("\nExample:")
        print("  python scripts/test_specific_coverage.py src/summit_api.py")
        print(
            "  python scripts/test_specific_coverage.py src/summit_api.py src/agent_worker.py"
        )
        return 1

    files = sys.argv[1:]

    # Validate files exist
    for file in files:
        if not os.path.exists(file):
            print(f"Error: File {file} does not exist")
            return 1

    success = test_file_coverage(files, coverage_threshold=70)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
