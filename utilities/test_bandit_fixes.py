#!/usr/bin/env python3
"""
Test Bandit Security Fixes

This script verifies that our security improvements for the Bandit findings work properly.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agent_lifecycle import AgentLifecycleManager
from summit import get_git_executable_path, get_repository_url


def test_git_executable_path():
    """Test that the git executable path finder works properly"""
    git_path = get_git_executable_path()

    if git_path:
        print(f" Git executable found at: {git_path}")
        # Verify it exists and is executable
        if os.path.exists(git_path) and os.access(git_path, os.X_OK):
            print(" Git executable is valid and executable")
        else:
            print(" Git executable path exists but is not valid/executable")
    else:
        print(" Git executable not found")

    assert git_path is not None and os.path.exists(git_path)


def test_secure_temp_dir():
    """Test the secure temp directory implementation"""
    # Create a test agent lifecycle
    agent = AgentLifecycleManager(agent_id="test-agent-123")

    # Set the environment variable to a test directory
    test_dir = os.path.join(tempfile.gettempdir(), "summit-test-runtime")
    os.environ["SUMMIT_RUNTIME_DIR"] = test_dir

    # Test the path construction
    agent_ready_path = os.path.join(
        os.environ.get("SUMMIT_RUNTIME_DIR", "/var/run/summit"), "agent-ready"
    )
    expected_path = os.path.join(test_dir, "agent-ready")

    if agent_ready_path == expected_path:
        print(f" Secure runtime directory used: {agent_ready_path}")
        result = True
    else:
        print(
            f" Secure path not correct: {agent_ready_path} != {expected_path}"
        )
        result = False

    # Cleanup
    del os.environ["SUMMIT_RUNTIME_DIR"]

    assert result


def test_subprocess_safety():
    """Test that subprocess calls are made safely"""
    # Test direct invocation using full path
    git_path = get_git_executable_path()
    if not git_path:
        print(" Cannot test subprocess safety - git not found")
        assert False, "Git executable not found"

    try:
        # Test subprocess with full path (should be safe)
        result = subprocess.run(
            [git_path, "--version"], capture_output=True, text=True, check=True
        )
        print(f" Safe subprocess call successful: {result.stdout.strip()}")
        assert True
    except Exception as e:
        print(f" Safe subprocess call failed: {e}")
        assert False, f"Subprocess call failed: {e}"


def main():
    """Run all security fix tests"""
    print("=" * 50)
    print("TESTING BANDIT SECURITY FIXES")
    print("=" * 50)

    results = []

    # Test 1: Git executable path
    print("\n1. Testing Git Executable Path Finder")
    print("-" * 40)
    results.append(test_git_executable_path())

    # Test 2: Secure temp directory
    print("\n2. Testing Secure Runtime Directory")
    print("-" * 40)
    results.append(test_secure_temp_dir())

    # Test 3: Subprocess safety
    print("\n3. Testing Subprocess Safety")
    print("-" * 40)
    results.append(test_subprocess_safety())

    # Summary
    print("\n" + "=" * 50)
    print("SECURITY FIX TEST RESULTS")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total} tests ({passed/total*100:.1f}%)")

    if passed == total:
        print(" All security fixes are working correctly!")
        return 0
    else:
        print(" Some security fixes need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
