#!/usr/bin/env python3
"""
Test the live API methods for branch operations.
Tests the real methods against current repository state.
"""

import sys
from pathlib import Path

# Add src to path for imports
repo_root = Path(__file__).parent
src_path = repo_root / "src"
scripts_path = repo_root / "scripts"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(scripts_path))

from src.agent_git_api import AgentGitAPI


def test_current_branch_api():
    """Test getting current branch name"""
    print("Testing get_current_branch API...")

    api = AgentGitAPI()
    current_branch = api.get_current_branch()

    print(f"Current branch: {current_branch}")
    assert isinstance(current_branch, str), "Branch name should be a string"
    assert len(current_branch) > 0, "Branch name should not be empty"

    print("✓ get_current_branch API works correctly")


def test_repository_status():
    """Test checking repository status"""
    print("Testing is_clean API...")

    api = AgentGitAPI()
    is_clean = api.is_clean()

    print(f"Repository is clean: {is_clean}")
    assert isinstance(is_clean, bool), "is_clean should return boolean"

    print("✓ is_clean API works correctly")


def test_api_initialization():
    """Test that API initializes without errors"""
    print("Testing AgentGitAPI initialization...")

    api = AgentGitAPI()

    # Check that all expected methods exist
    required_methods = [
        "create_feature_branch",
        "switch_branch",
        "get_current_branch",
        "is_clean",
        "quick_save",
        "check_status",
    ]

    for method_name in required_methods:
        assert hasattr(api, method_name), f"API missing method: {method_name}"
        assert callable(
            getattr(api, method_name)
        ), f"Method not callable: {method_name}"

    print("✓ AgentGitAPI initialized with all required methods")


def run_live_tests():
    """Run all live API tests"""
    print("=" * 60)
    print("TESTING LIVE AGENT GIT API FUNCTIONALITY")
    print("=" * 60)
    print()

    try:
        test_api_initialization()
        print()

        test_current_branch_api()
        print()

        test_repository_status()
        print()

        print("=" * 60)
        print("✅ ALL LIVE API TESTS PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ LIVE TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_live_tests()
    sys.exit(0 if success else 1)
