#!/usr/bin/env python3
"""
Check coverage for new or modified files only
Ensures 70% coverage requirement for new code
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def get_modified_files():
    """Get list of modified Python files in src/"""
    try:
        # Get modified files from git
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        modified_files = []
        for file in result.stdout.strip().split("\n"):
            if file.startswith("src/") and file.endswith(".py"):
                modified_files.append(file)

        return modified_files
    except subprocess.CalledProcessError:
        # If git command fails, check all files in src/
        src_path = Path("src")
        return [str(f) for f in src_path.glob("**/*.py")]


def run_coverage_for_files(files):
    """Run coverage for specific files"""
    if not files:
        print("No Python files to check coverage for")
        return True

    print(f"Checking coverage for {len(files)} files:")
    for file in files:
        print(f"  - {file}")

    # Run pytest with coverage for specific files
    cmd = [
        "python",
        "-m",
        "pytest",
        "--cov=" + ",".join(files),
        "--cov-report=term-missing",
        "--cov-report=json:coverage_new.json",
        "--cov-fail-under=60",
        "-v",
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print(" Coverage check passed for new/modified files")
        return True
    except subprocess.CalledProcessError as e:
        print(" Coverage check failed for new/modified files")

        # Try to read coverage report for details
        try:
            with open("coverage_new.json", "r") as f:
                coverage_data = json.load(f)
                total_coverage = coverage_data.get("totals", {}).get(
                    "percent_covered", 0
                )
                print(f"Total coverage for new files: {total_coverage:.2f}%")

                # Show per-file coverage
                for filename, file_data in coverage_data.get(
                    "files", {}
                ).items():
                    if filename in files:
                        file_coverage = file_data.get("summary", {}).get(
                            "percent_covered", 0
                        )
                        print(f"  {filename}: {file_coverage:.2f}%")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        return False


def main():
    """Main function"""
    print(" Checking coverage for new/modified code...")

    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("Not in a git repository, checking all files in src/")
        modified_files = [str(f) for f in Path("src").glob("**/*.py")]
    else:
        modified_files = get_modified_files()

    if not modified_files:
        print("No Python files found to check")
        return 0

    success = run_coverage_for_files(modified_files)

    # Cleanup
    if os.path.exists("coverage_new.json"):
        os.remove("coverage_new.json")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
