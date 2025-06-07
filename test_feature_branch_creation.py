#!/usr/bin/env python3
"""
Test script for feature branch creation functionality.
Tests the fixed create_feature_branch and switch_branch methods.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
repo_root = Path(__file__).parent
src_path = repo_root / "src"
scripts_path = repo_root / "scripts"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(scripts_path))

from src.agent_git_api import AgentGitAPI


def test_create_feature_branch():
    """Test creating a new feature branch"""
    print("Testing create_feature_branch functionality...")

    with patch("src.agent_git_api.AgentGitWrapper") as mock_wrapper_class:
        mock_wrapper = Mock()
        mock_wrapper_class.return_value = mock_wrapper

        # Mock successful branch creation
        mock_wrapper._run_command.return_value = Mock(returncode=0)

        api = AgentGitAPI()

        # Test successful branch creation
        result = api.create_feature_branch("feature/test-branch")
        assert result is True, "Should successfully create feature branch"

        # Verify git checkout -b was called with correct parameters
        mock_wrapper._run_command.assert_called_with(
            ["git", "checkout", "-b", "feature/test-branch"], check=False
        )

        print("✓ create_feature_branch: Success case passed")

        # Test failed branch creation
        mock_wrapper._run_command.return_value = Mock(
            returncode=1,
            stderr="fatal: A branch named 'feature/test-branch' already exists.",
        )

        result = api.create_feature_branch("feature/test-branch")
        assert result is False, "Should fail when branch already exists"

        print("✓ create_feature_branch: Failure case passed")


def test_switch_branch():
    """Test switching to an existing branch"""
    print("Testing switch_branch functionality...")

    with patch("src.agent_git_api.AgentGitWrapper") as mock_wrapper_class:
        mock_wrapper = Mock()
        mock_wrapper_class.return_value = mock_wrapper

        # Mock successful branch switch
        mock_wrapper._run_command.return_value = Mock(returncode=0)

        api = AgentGitAPI()

        # Test successful branch switch
        result = api.switch_branch("main")
        assert result is True, "Should successfully switch to existing branch"

        # Verify git checkout was called with correct parameters
        mock_wrapper._run_command.assert_called_with(
            ["git", "checkout", "main"], check=False
        )

        print("✓ switch_branch: Success case passed")

        # Test failed branch switch
        mock_wrapper._run_command.return_value = Mock(
            returncode=1,
            stderr="error: pathspec 'nonexistent' did not match any file(s)",
        )

        result = api.switch_branch("nonexistent")
        assert result is False, "Should fail when branch doesn't exist"

        print("✓ switch_branch: Failure case passed")


def test_branch_workflow():
    """Test a complete branch creation and switching workflow"""
    print("Testing complete branch workflow...")

    with patch("src.agent_git_api.AgentGitWrapper") as mock_wrapper_class:
        mock_wrapper = Mock()
        mock_wrapper_class.return_value = mock_wrapper

        api = AgentGitAPI()

        # Simulate workflow: create feature branch, switch back to main
        mock_wrapper._run_command.return_value = Mock(returncode=0)

        # Create feature branch
        result1 = api.create_feature_branch("feature/workflow-test")
        assert result1 is True

        # Switch back to main
        result2 = api.switch_branch("main")
        assert result2 is True

        # Switch back to feature branch
        result3 = api.switch_branch("feature/workflow-test")
        assert result3 is True

        print("✓ Complete branch workflow passed")

        # Verify all calls were made
        expected_calls = [
            (["git", "checkout", "-b", "feature/workflow-test"],),
            (["git", "checkout", "main"],),
            (["git", "checkout", "feature/workflow-test"],),
        ]

        actual_calls = [
            call[0] for call in mock_wrapper._run_command.call_args_list
        ]

        for expected, actual in zip(expected_calls, actual_calls):
            assert (
                expected[0] == actual[0]
            ), f"Expected {expected}, got {actual}"

        print("✓ All git commands called correctly")


def run_all_tests():
    """Run all branch creation tests"""
    print("=" * 60)
    print("TESTING FIXED FEATURE BRANCH CREATION FUNCTIONALITY")
    print("=" * 60)
    print()

    try:
        test_create_feature_branch()
        print()

        test_switch_branch()
        print()

        test_branch_workflow()
        print()

        print("=" * 60)
        print("✅ ALL TESTS PASSED - FEATURE BRANCH CREATION IS FIXED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
