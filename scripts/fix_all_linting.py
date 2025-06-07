#!/usr/bin/env python3
"""
Comprehensive automated linting fix script for Summit project.
Runs all formatting tools and fixes common issues automatically.
"""

import os
import subprocess
import sys
from typing import List, Tuple


def run_command(cmd: List[str], description: str) -> Tuple[int, str, str]:
    """Run a command and return result"""
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print(f" {description} - Success")
        else:
            print(f" {description} - Failed (exit {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr}")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print(f" {description} - Timeout")
        return -1, "", "Command timed out"
    except Exception as e:
        print(f" {description} - Exception: {e}")
        return -1, "", str(e)


def fix_import_issues():
    """Fix import ordering and organization issues"""
    print("\n" + "=" * 60)
    print(" FIXING IMPORT ISSUES")
    print("=" * 60)

    # Run isort multiple times with different configurations
    commands = [
        (
            [
                "python",
                "-m",
                "isort",
                "src/",
                "tests/",
                "--profile",
                "black",
                "--line-length",
                "79",
                "--force-sort-within-sections",
                "--force-single-line",
            ],
            "isort - force single line imports",
        ),
        (
            [
                "python",
                "-m",
                "isort",
                "src/",
                "tests/",
                "--profile",
                "black",
                "--line-length",
                "79",
            ],
            "isort - standard formatting",
        ),
        (
            [
                "python",
                "-m",
                "autoflake",
                "--in-place",
                "--recursive",
                "--remove-unused-variables",
                "--remove-all-unused-imports",
                "--expand-star-imports",
                "src/",
                "tests/",
            ],
            "autoflake - remove unused imports and variables",
        ),
    ]

    for cmd, desc in commands:
        run_command(cmd, desc)


def fix_line_length_issues():
    """Fix line length issues automatically where possible"""
    print("\n" + "=" * 60)
    print(" FIXING LINE LENGTH ISSUES")
    print("=" * 60)

    commands = [
        (
            ["python", "-m", "black", "src/", "tests/", "--line-length", "79"],
            "Black formatting with 79 char limit",
        ),
        (
            [
                "python",
                "-m",
                "autopep8",
                "--in-place",
                "--aggressive",
                "--aggressive",
                "--recursive",
                "--max-line-length",
                "79",
                "src/",
                "tests/",
            ],
            "autopep8 aggressive line length fixing",
        ),
    ]

    for cmd, desc in commands:
        run_command(cmd, desc)


def fix_specific_files():
    """Fix specific problematic files that need manual intervention"""
    print("\n" + "=" * 60)
    print(" FIXING SPECIFIC PROBLEMATIC FILES")
    print("=" * 60)

    # Files that commonly have issues
    problematic_files = [
        "src/pr_reviewers.py",
        "src/summit.py",
        "src/database.py",
        "tests/test_summit_basic.py",
        "tests/test_autonomous_integration.py",
    ]

    for file_path in problematic_files:
        if os.path.exists(file_path):
            print(f"\nProcessing {file_path}...")

            # Apply multiple rounds of formatting
            commands = [
                (
                    [
                        "python",
                        "-m",
                        "autoflake",
                        "--in-place",
                        "--remove-unused-variables",
                        "--remove-all-unused-imports",
                        file_path,
                    ],
                    f"autoflake on {file_path}",
                ),
                (
                    [
                        "python",
                        "-m",
                        "isort",
                        file_path,
                        "--profile",
                        "black",
                        "--line-length",
                        "79",
                    ],
                    f"isort on {file_path}",
                ),
                (
                    [
                        "python",
                        "-m",
                        "black",
                        file_path,
                        "--line-length",
                        "79",
                    ],
                    f"black on {file_path}",
                ),
                (
                    [
                        "python",
                        "-m",
                        "autopep8",
                        "--in-place",
                        "--aggressive",
                        "--max-line-length",
                        "79",
                        file_path,
                    ],
                    f"autopep8 on {file_path}",
                ),
            ]

            for cmd, desc in commands:
                run_command(cmd, desc)


def check_remaining_issues():
    """Check what linting issues remain after fixes"""
    print("\n" + "=" * 60)
    print(" CHECKING REMAINING ISSUES")
    print("=" * 60)

    code, stdout, stderr = run_command(
        [
            "python",
            "-m",
            "flake8",
            "src/",
            "tests/",
            "--select=E501,F401,E402,E712,E722,W291,I100,I101,I201",
        ],
        "flake8 check for remaining issues",
    )

    if code == 0:
        print(" All targeted linting issues fixed!")
        return True
    else:
        print(f"\nRemaining issues:\n{stdout}")
        # Count issues by type
        lines = stdout.strip().split("\n") if stdout.strip() else []
        issue_counts = {}
        for line in lines:
            if ":" in line and " " in line:
                parts = line.split(" ")
                if len(parts) >= 2:
                    error_code = parts[1]
                    issue_counts[error_code] = (
                        issue_counts.get(error_code, 0) + 1
                    )

        print(f"\nIssue breakdown:")
        for code, count in sorted(issue_counts.items()):
            print(f"  {code}: {count} occurrences")

        return False


def main():
    """Main automation function"""
    print(" AUTOMATED LINTING FIX SCRIPT")
    print("=" * 60)
    print("This script will automatically fix common linting issues")
    print("=" * 60)

    # Change to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")

    # Step 1: Fix imports
    fix_import_issues()

    # Step 2: Fix line lengths
    fix_line_length_issues()

    # Step 3: Fix specific problematic files
    fix_specific_files()

    # Step 4: Final comprehensive pass
    print("\n" + "=" * 60)
    print(" FINAL COMPREHENSIVE FORMATTING PASS")
    print("=" * 60)

    final_commands = [
        (
            [
                "python",
                "-m",
                "isort",
                "src/",
                "tests/",
                "--profile",
                "black",
                "--line-length",
                "79",
            ],
            "Final isort pass",
        ),
        (
            ["python", "-m", "black", "src/", "tests/", "--line-length", "79"],
            "Final black pass",
        ),
        (
            [
                "python",
                "-m",
                "autopep8",
                "--in-place",
                "--aggressive",
                "--recursive",
                "--max-line-length",
                "79",
                "src/",
                "tests/",
            ],
            "Final autopep8 pass",
        ),
    ]

    for cmd, desc in final_commands:
        run_command(cmd, desc)

    # Step 5: Check results
    all_fixed = check_remaining_issues()

    if all_fixed:
        print("\n SUCCESS: All linting issues have been automatically fixed!")
        print("\nYou can now commit your changes:")
        print(
            "python -c \"from src.agent_git_api import save_work; save_work('Automated linting fixes')\""
        )
    else:
        print("\n  Some issues remain and may need manual intervention")
        print(
            "Most common remaining issues typically require manual string breaking"
        )

    return 0 if all_fixed else 1


if __name__ == "__main__":
    sys.exit(main())
