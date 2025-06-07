#!/usr/bin/env python3
"""Tests for the agent git wrapper"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.agent_git_api import AgentGitWrapper

# Add src and scripts to path
repo_root = Path(__file__).parent.parent
src_path = repo_root / "src"
scripts_path = repo_root / "scripts"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(scripts_path))


class TestAgentGitWrapper:
    """Test the agent git wrapper functionality"""

    @pytest.fixture
    def wrapper(self):
        """Create a wrapper instance with mocked repo root"""
        with patch.object(
            AgentGitWrapper, "_find_repo_root", return_value=Path("/fake/repo")
        ):
            wrapper = AgentGitWrapper()
            wrapper.github_token = "fake-token"
            return wrapper

    def test_validate_commit_message(self):
        """Test commit message validation"""
        wrapper = AgentGitWrapper()

        # Valid messages
        valid_msgs = [
            "Fix bug in API client",
            "Add new feature for user auth",
            "Update documentation for API endpoints",
            "Refactor database connection handling",
        ]

        for msg in valid_msgs:
            assert wrapper._validate_commit_message(msg)

        # Invalid messages (emoji, multiple lines, etc)
        invalid_msgs = [
            " Fix bug in API",
            "Fix bug\nAdd feature",
            "",  # Empty message
        ]

        for msg in invalid_msgs:
            assert not wrapper._validate_commit_message(msg)

    def test_run_tests_success(self, wrapper):
        """Test successful test run"""
        # Mock successful test run and coverage file
        with patch.object(wrapper, "_run_command") as mock_cmd:
            mock_cmd.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )

            with patch("builtins.open"), patch(
                "json.load", return_value={"totals": {"percent_covered": 85.5}}
            ):
                assert wrapper._run_tests() is True

    def test_run_tests_failure(self, wrapper):
        """Test failed test run"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            result = MagicMock(
                returncode=1, stdout="Test failed", stderr="Error"
            )
            mock_cmd.return_value = result
            assert wrapper._run_tests() is False

    def test_run_tests_low_coverage(self, wrapper):
        """Test low coverage rejection"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            mock_cmd.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )

            with patch("builtins.open"), patch(
                "json.load", return_value={"totals": {"percent_covered": 65.0}}
            ):
                assert wrapper._run_tests() is False

    @patch("subprocess.run")
    def test_get_current_branch(self, mock_run, wrapper):
        """Test getting current branch"""
        result = MagicMock(
            returncode=0, stdout="feature/test-branch\n", stderr=""
        )
        mock_run.return_value = result
        assert wrapper._get_current_branch() == "feature/test-branch"

    def test_get_repo_info_ssh(self, wrapper):
        """Test parsing SSH repo URL"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            stdout = "git@github.com:owner/repo.git\n"
            mock_cmd.return_value = MagicMock(stdout=stdout)
            owner, repo = wrapper._get_repo_info()
            assert owner == "owner"
            assert repo == "repo"

    def test_get_repo_info_https(self, wrapper):
        """Test parsing HTTPS repo URL"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            stdout = "https://github.com/owner/repo.git\n"
            mock_cmd.return_value = MagicMock(stdout=stdout)
            owner, repo = wrapper._get_repo_info()
            assert owner == "owner"
            assert repo == "repo"

    def test_get_repo_info_invalid_url(self, wrapper):
        """Test parsing invalid repo URL"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            mock_cmd.return_value = MagicMock(stdout="invalid-url\n")

            match_text = "Could not parse GitHub repository info"
            with pytest.raises(ValueError, match=match_text):
                wrapper._get_repo_info()

    @patch.object(
        AgentGitWrapper, "_validate_commit_message", return_value=True
    )
    @patch.object(AgentGitWrapper, "_run_tests", return_value=True)
    @patch.object(AgentGitWrapper, "_run_linting", return_value=True)
    @patch.object(
        AgentGitWrapper, "_check_pre_commit_hooks", return_value=True
    )
    @patch.object(AgentGitWrapper, "_run_command")
    def test_commit_success(
        self,
        mock_cmd,
        mock_hooks,
        mock_lint,
        mock_tests,
        mock_validate,
        wrapper,
    ):
        """Test successful commit"""
        mock_cmd.return_value = MagicMock(returncode=0, stdout="", stderr="")

        assert wrapper.commit("Fix important bug") is True
        mock_validate.assert_called_once()
        mock_tests.assert_called_once()
        mock_lint.assert_called_once()
        mock_hooks.assert_called_once()

    @patch.object(
        AgentGitWrapper, "_validate_commit_message", return_value=False
    )
    def test_commit_invalid_message(self, mock_validate, wrapper):
        """Test commit with invalid message"""
        assert wrapper.commit("Bad message ") is False

    @patch.object(
        AgentGitWrapper, "_get_current_branch", return_value="feature/test"
    )
    @patch.object(AgentGitWrapper, "_run_command")
    def test_push_success(self, mock_cmd, mock_branch, wrapper):
        """Test successful push"""
        mock_cmd.return_value = MagicMock(
            returncode=0, stdout="abc123\n", stderr=""
        )

        assert wrapper.push() is True
        assert mock_cmd.call_count >= 2  # At least push and get commit SHA

    @patch.object(AgentGitWrapper, "commit", return_value=True)
    @patch.object(AgentGitWrapper, "push", return_value=True)
    @patch.object(AgentGitWrapper, "_run_command")
    def test_quick_commit_push(
        self, mock_cmd, mock_push, mock_commit, wrapper
    ):
        """Test quick commit and push workflow"""
        mock_cmd.return_value = MagicMock(returncode=0, stdout="", stderr="")

        assert wrapper.quick_commit_push("Quick fix") is True
        mock_commit.assert_called_once_with("Quick fix")
        mock_push.assert_called_once()

    def test_run_linting_no_flake8(self, wrapper):
        """Test linting when flake8 is not available"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            # First call to 'which flake8' fails
            mock_cmd.side_effect = [
                MagicMock(returncode=1),  # which flake8 fails
            ]
            # Should skip and return True
            assert wrapper._run_linting() is True

    def test_check_pre_commit_hooks_not_available(self, wrapper):
        """Test pre-commit hooks when not available"""
        with patch.object(wrapper, "_run_command") as mock_cmd:
            # First call to 'which pre-commit' fails
            mock_cmd.side_effect = [
                MagicMock(returncode=1),  # which pre-commit fails
            ]
            # Should skip and return True
            assert wrapper._check_pre_commit_hooks() is True

    @patch.object(AgentGitWrapper, "push", return_value=True)
    @patch.object(
        AgentGitWrapper, "_get_current_branch", return_value="feature/test"
    )
    @patch.object(
        AgentGitWrapper, "_get_repo_info", return_value=("owner", "repo")
    )
    @patch("requests.post")
    def test_create_pr_success(
        self, mock_post, mock_repo, mock_branch, mock_push, wrapper
    ):
        """Test successful PR creation"""
        # Mock successful GitHub API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/123",
            "number": 123,
        }
        mock_post.return_value = mock_response

        # Test PR creation
        result = wrapper.create_pr("Test PR Title", "Test PR Body")

        assert result is True
        mock_push.assert_called_once()
        mock_post.assert_called_once()

        # Verify the API call
        call_args = mock_post.call_args
        assert (
            call_args[0][0] == "https://api.github.com/repos/owner/repo/pulls"
        )

        # Verify the request data
        data = call_args[1]["json"]
        assert data["title"] == "Test PR Title"
        assert data["body"] == "Test PR Body"
        assert data["head"] == "feature/test"
        assert data["base"] == "main"

    @patch.object(AgentGitWrapper, "_get_current_branch", return_value="main")
    def test_create_pr_from_main_branch(self, mock_branch, wrapper):
        """Test PR creation fails from main branch"""
        result = wrapper.create_pr("Test PR", "Test body")
        assert result is False

    @patch.object(AgentGitWrapper, "push", return_value=False)
    @patch.object(
        AgentGitWrapper, "_get_current_branch", return_value="feature/test"
    )
    def test_create_pr_push_fails(self, mock_branch, mock_push, wrapper):
        """Test PR creation fails when push fails"""
        result = wrapper.create_pr("Test PR", "Test body")
        assert result is False

    @patch.object(AgentGitWrapper, "push", return_value=True)
    @patch.object(
        AgentGitWrapper, "_get_current_branch", return_value="feature/test"
    )
    @patch.object(
        AgentGitWrapper, "_get_repo_info", return_value=("owner", "repo")
    )
    @patch("requests.post")
    def test_create_pr_api_failure(
        self, mock_post, mock_repo, mock_branch, mock_push, wrapper
    ):
        """Test PR creation handles API failures"""
        mock_post.side_effect = Exception("API Error")

        result = wrapper.create_pr("Test PR", "Test body")
        assert result is False

    def test_create_pr_no_github_token(self, wrapper):
        """Test PR creation fails without GitHub token"""
        wrapper.github_token = None
        result = wrapper.create_pr("Test PR", "Test body")
        assert result is False

    @patch.object(AgentGitWrapper, "push", return_value=True)
    @patch.object(
        AgentGitWrapper, "_get_current_branch", return_value="feature/test"
    )
    @patch.object(
        AgentGitWrapper, "_get_repo_info", return_value=("owner", "repo")
    )
    @patch("requests.post")
    def test_create_pr_with_default_body(
        self, mock_post, mock_repo, mock_branch, mock_push, wrapper
    ):
        """Test PR creation with default body when none provided"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "html_url": "https://github.com/owner/repo/pull/123"
        }
        mock_post.return_value = mock_response

        # Test with empty body
        result = wrapper.create_pr("Test PR Title", "")

        assert result is True

        # Verify the default body was used
        call_args = mock_post.call_args
        data = call_args[1]["json"]
        assert data["body"] == "Automated PR from branch feature/test"


class TestAgentGitAPI:
    """Test the simplified API"""

    def test_api_imports(self):
        """Test API convenience functions can be imported"""
        with patch("agent_git_api.AgentGitWrapper"):
            from agent_git_api import create_pr, pull, save_work, status

            # Test imports work
            assert callable(save_work)
            assert callable(create_pr)
            assert callable(status)
            assert callable(pull)

    @patch("agent_git_api.AgentGitWrapper")
    def test_agent_git_api_init(self, mock_wrapper):
        """Test AgentGitAPI initialization"""
        from agent_git_api import AgentGitAPI

        api = AgentGitAPI()
        assert api.git is not None
        mock_wrapper.assert_called_once()

    @patch("agent_git_api.agent_git")
    def test_save_work_function(self, mock_agent_git):
        """Test the save_work convenience function"""
        mock_agent_git.git.quick_commit_push.return_value = True

        from agent_git_api import save_work

        result = save_work("Test message", ["file1.py"])

        assert result is True
        mock_agent_git.git.quick_commit_push.assert_called_once_with(
            "Test message", ["file1.py"]
        )

    @patch("agent_git_api.agent_git")
    def test_create_pr_function(self, mock_agent_git):
        """Test the create_pr convenience function"""
        mock_agent_git.save_and_create_pr.return_value = True

        from agent_git_api import create_pr

        result = create_pr("Commit msg", "PR title", "PR body")

        assert result is True
        mock_agent_git.save_and_create_pr.assert_called_once_with(
            "Commit msg", "PR title", "PR body"
        )

    @patch("agent_git_api.agent_git")
    def test_status_function(self, mock_agent_git):
        """Test the status convenience function"""
        from agent_git_api import status

        status()
        mock_agent_git.check_status.assert_called_once()

    @patch("agent_git_api.agent_git")
    def test_pull_function(self, mock_agent_git):
        """Test the pull convenience function"""
        mock_agent_git.update_from_remote.return_value = True

        from agent_git_api import pull

        result = pull()

        assert result is True
        mock_agent_git.update_from_remote.assert_called_once()

    def test_agent_git_api_methods(self):
        """Test AgentGitAPI class methods"""
        from agent_git_api import AgentGitAPI

        with patch("agent_git_api.AgentGitWrapper") as mock_wrapper_class:
            mock_wrapper = Mock()
            mock_wrapper_class.return_value = mock_wrapper

            api = AgentGitAPI()

            # Test quick_save
            mock_wrapper.quick_commit_push.return_value = True
            assert api.quick_save("test msg") is True
            mock_wrapper.quick_commit_push.assert_called_with("test msg", None)

            # Test check_status
            api.check_status()
            mock_wrapper.status.assert_called_once()

            # Test update_from_remote
            mock_wrapper.pull.return_value = True
            assert api.update_from_remote() is True

            # Test is_clean
            mock_wrapper._run_command.return_value = Mock(stdout="")
            assert api.is_clean() is True
            mock_wrapper._run_command.return_value = Mock(stdout="M file.py")
            assert api.is_clean() is False

            # Test get_current_branch
            mock_wrapper._get_current_branch.return_value = "main"
            assert api.get_current_branch() == "main"

            # Test create_feature_branch
            mock_wrapper._run_command.return_value = Mock(returncode=0)
            assert api.create_feature_branch("feature/test") is True

            # Test switch_branch
            mock_wrapper._run_command.return_value = Mock(returncode=0)
            assert api.switch_branch("main") is True

    def test_ci_cd_monitoring_functions(self):
        """Test CI/CD monitoring convenience functions"""
        from agent_git_api import (
            check_ci_status,
            check_pipeline_status,
            show_failed_checks,
            wait_for_ci,
        )

        with patch("agent_git_api.agent_git") as mock_agent_git:
            # Test check_ci_status
            mock_agent_git.check_ci_status.return_value = {
                "state": "success",
                "statuses": [],
                "total_count": 0,
            }
            result = check_ci_status("abc123")
            assert result["state"] == "success"
            mock_agent_git.check_ci_status.assert_called_with("abc123")

            # Test check_ci_status with default commit
            check_ci_status()
            mock_agent_git.check_ci_status.assert_called_with(None)

            # Test show_failed_checks
            show_failed_checks("abc123")
            mock_agent_git.show_failed_checks.assert_called_with("abc123")

            # Test show_failed_checks with default commit
            show_failed_checks()
            mock_agent_git.show_failed_checks.assert_called_with(None)

            # Test wait_for_ci
            mock_agent_git.wait_for_ci.return_value = True
            result = wait_for_ci("abc123")
            assert result is True
            mock_agent_git.wait_for_ci.assert_called_with("abc123")

            # Test wait_for_ci with default commit
            wait_for_ci()
            mock_agent_git.wait_for_ci.assert_called_with(None)

            # Test check_pipeline_status
            check_pipeline_status()
            mock_agent_git.check_pipeline_status.assert_called_once()

    def test_agent_git_api_ci_methods(self):
        """Test AgentGitAPI CI/CD monitoring methods"""
        from agent_git_api import AgentGitAPI

        with patch("agent_git_api.AgentGitWrapper") as mock_wrapper_class:
            mock_wrapper = Mock()
            mock_wrapper_class.return_value = mock_wrapper

            api = AgentGitAPI()

            # Test check_ci_status method
            expected_status = {
                "state": "pending",
                "statuses": [],
                "total_count": 0,
            }

            # Mock the git rev-parse command
            mock_wrapper._run_command.return_value = Mock(stdout="abc123")
            # Mock the actual CI status check method (with underscore)
            mock_wrapper._check_ci_status.return_value = expected_status

            result = api.check_ci_status("abc123")
            assert result == expected_status
            mock_wrapper._check_ci_status.assert_called_with("abc123")

            # Test show_failed_checks method
            api.show_failed_checks("abc123")
            mock_wrapper._show_failed_checks.assert_called_with("abc123")

            # Test wait_for_ci method
            mock_wrapper._wait_for_ci.return_value = True
            result = api.wait_for_ci("abc123")
            assert result is True
            mock_wrapper._wait_for_ci.assert_called_with("abc123")

            # Test check_pipeline_status method
            api.check_pipeline_status()
            mock_wrapper._check_ci_status.assert_called()
            mock_wrapper._run_command.assert_called()

    @patch("agent_git_api.agent_git")
    def test_save_and_create_pr_success(self, mock_agent_git):
        """Test save_and_create_pr method success"""
        from agent_git_api import AgentGitAPI

        mock_agent_git.git.quick_commit_push.return_value = True
        mock_agent_git.git.create_pr.return_value = True

        api = AgentGitAPI()
        api.git = mock_agent_git.git

        result = api.save_and_create_pr(
            "Fix test issue",
            "Fix: Resolve test failure",
            "This PR fixes the failing test by updating the assertion",
        )

        assert result is True
        mock_agent_git.git.quick_commit_push.assert_called_once_with(
            "Fix test issue", None
        )
        mock_agent_git.git.create_pr.assert_called_once_with(
            "Fix: Resolve test failure",
            "This PR fixes the failing test by updating the assertion",
        )

    @patch("agent_git_api.agent_git")
    def test_save_and_create_pr_commit_fails(self, mock_agent_git):
        """Test save_and_create_pr when commit fails"""
        from agent_git_api import AgentGitAPI

        mock_agent_git.git.quick_commit_push.return_value = False

        api = AgentGitAPI()
        api.git = mock_agent_git.git

        result = api.save_and_create_pr("Bad commit", "PR Title", "PR Body")

        assert result is False
        mock_agent_git.git.quick_commit_push.assert_called_once()
        # Should not call create_pr if commit fails
        mock_agent_git.git.create_pr.assert_not_called()

    @patch("agent_git_api.agent_git")
    def test_save_and_create_pr_pr_creation_fails(self, mock_agent_git):
        """Test save_and_create_pr when PR creation fails"""
        from agent_git_api import AgentGitAPI

        mock_agent_git.git.quick_commit_push.return_value = True
        mock_agent_git.git.create_pr.return_value = False

        api = AgentGitAPI()
        api.git = mock_agent_git.git

        result = api.save_and_create_pr("Good commit", "PR Title", "PR Body")

        assert result is False
        mock_agent_git.git.quick_commit_push.assert_called_once()
        mock_agent_git.git.create_pr.assert_called_once()
