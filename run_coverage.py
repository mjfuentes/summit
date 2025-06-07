#!/usr/bin/env python3
"""
Simple script to run tests with code coverage.
Straightforward implementation - no visuals, just core functionality.
"""

import os
import subprocess
import sys


def run_coverage():
    """Run tests with coverage and display results"""

    print(" Running tests with code coverage...")
    print("=" * 50)

    # Run pytest with coverage
    cmd = [
        "python",
        "-m",
        "pytest",
        "--cov=src",  # Cover the src directory
        "--cov-report=term",  # Terminal report
        "--cov-report=term-missing",  # Show missing lines
        "tests/",  # Run tests from tests directory
        "-v",  # Verbose output
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)

        if result.returncode == 0:
            print("\n Tests passed with coverage report above")
        else:
            print("\n Some tests failed - see output above")

        return result.returncode

    except FileNotFoundError:
        print(
            " pytest not found. Please install with: pip install pytest pytest-cov"
        )
        return 1
    except Exception as e:
        print(f" Error running coverage: {e}")
        return 1
    finally:
        # Clean up coverage files per cursor rules
        print("\nCleaning up coverage files...")
        try:
            coverage_files = ["coverage.json", ".coverage", "coverage.xml"]
            for coverage_file in coverage_files:
                if os.path.exists(coverage_file):
                    os.remove(coverage_file)
                    print(f"Removed {coverage_file}")
        except Exception as cleanup_error:
            print(
                f"Warning: Could not clean up coverage files: {cleanup_error}"
            )


def show_coverage_summary():
    """Show a simple coverage summary"""
    print("\n Coverage Commands:")
    print("- Run with coverage: python run_coverage.py")
    print("- Quick coverage:    pytest --cov=src")
    print("- Detailed report:   pytest --cov=src --cov-report=term-missing")
    print("- HTML report:       pytest --cov=src --cov-report=html")

    print("Checking for emoji violations...")
    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "tools/emoji_linter.py", "--fix"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Emoji violations found and fixed:")
            print(result.stdout)
            print("Please review changes and re-run tests")
            return
        else:
            print("No emoji violations found")
    except Exception as e:
        print(f"Warning: Could not run emoji linter: {e}")


if __name__ == "__main__":
    exit_code = run_coverage()
    show_coverage_summary()
    sys.exit(exit_code)
