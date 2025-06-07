#!/usr/bin/env python3
"""
Fast test runner for Summit - uses parallel execution by default
"""

import subprocess
import sys
import time


def run_tests(args=None):
    """Run tests with optimal settings for speed"""
    start_time = time.time()

    # Default arguments for fast testing
    cmd = ["python", "-m", "pytest", "tests/", "-v", "-n", "auto"]

    # Add any additional arguments passed
    if args:
        cmd.extend(args)

    print("Running Summit tests with parallel execution...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, check=True)
        end_time = time.time()
        print(f"\nTests completed in {end_time - start_time:.2f} seconds")
        return result.returncode
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(f"\nTests failed after {end_time - start_time:.2f} seconds")
        return e.returncode


def run_coverage():
    """Run tests with coverage report"""
    start_time = time.time()

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=term-missing",
        "-n",
        "auto",
        "-v",
    ]

    print("Running Summit tests with coverage...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, check=True)
        end_time = time.time()
        print(
            f"\nCoverage tests completed in {end_time - start_time:.2f} seconds"
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(
            f"\nCoverage tests failed after {end_time - start_time:.2f} seconds"
        )
        return e.returncode
    finally:
        # Clean up coverage files per cursor rules
        print("\nCleaning up coverage files...")
        try:
            import os

            coverage_files = ["coverage.json", ".coverage", "coverage.xml"]
            for coverage_file in coverage_files:
                if os.path.exists(coverage_file):
                    os.remove(coverage_file)
                    print(f"Removed {coverage_file}")
        except Exception as cleanup_error:
            print(
                f"Warning: Could not clean up coverage files: {cleanup_error}"
            )


def run_single_test(test_name):
    """Run a single test file or test function"""
    start_time = time.time()

    cmd = ["python", "-m", "pytest", f"tests/{test_name}", "-v", "-s"]

    print(f"Running single test: {test_name}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, check=True)
        end_time = time.time()
        print(
            f"\nSingle test completed in {end_time - start_time:.2f} seconds"
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(
            f"\nSingle test failed after {end_time - start_time:.2f} seconds"
        )
        return e.returncode


def run_autonomous_tests():
    """Run autonomous integration tests (requires Docker)"""
    start_time = time.time()

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/test_autonomous_integration.py",
        "-v",
        "-s",
        "-m",
        "autonomous",
        "--tb=long",
    ]

    print("Running autonomous integration tests...")
    print("  WARNING: This requires Docker and will build containers")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, check=True)
        end_time = time.time()
        print(
            f"\nAutonomous tests completed in {end_time - start_time:.2f} seconds"
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print(
            f"\nAutonomous tests failed after {end_time - start_time:.2f} seconds"
        )
        return e.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--coverage":
            sys.exit(run_coverage())
        elif sys.argv[1] == "--single":
            if len(sys.argv) > 2:
                sys.exit(run_single_test(sys.argv[2]))
            else:
                print("Error: --single requires a test name")
                print("Usage: python run_tests.py --single test_summit.py")
                sys.exit(1)
        elif sys.argv[1] == "--autonomous":
            sys.exit(run_autonomous_tests())
        elif sys.argv[1] == "--help":
            print("Summit Test Runner")
            print("Usage:")
            print(
                "  python run_tests.py                    # Run all tests in parallel"
            )
            print(
                "  python run_tests.py --coverage         # Run tests with coverage"
            )
            print("  python run_tests.py --single <test>    # Run single test")
            print(
                "  python run_tests.py --autonomous       # Run autonomous integration tests (requires Docker)"
            )
            print("  python run_tests.py --help             # Show this help")
            sys.exit(0)
        else:
            # Pass remaining arguments to pytest
            sys.exit(run_tests(sys.argv[1:]))
    else:
        sys.exit(run_tests())
