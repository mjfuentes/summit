#!/usr/bin/env python3
"""
Tests for GitHub CI/CD Integration Module
"""

from github_cicd import (
    GitHubCICDManager,
    get_task_ci_status,
    get_workflow_runs_for_task,
)
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestGitHubCICDManager:
    """Test GitHub CI/CD Manager functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = GitHubCICDManager("test-token")
        self.test_repo_url = "https://github.com/owner/repo"
        self.test_task_data = {
            "task_id": "test-task-123",
            "repository_url": self.test_repo_url,
            "pr_number": 42,
            "commit_sha": "abc123def456",
            "branch_name": "feature/test-branch",
        }

    def test_init_with_token(self):
        """Test manager initialization with token"""
        manager = GitHubCICDManager("test-token")
        assert manager.github_token == "test-token"
        assert manager.base_url == "https://api.github.com"
        assert "Authorization" in manager.headers
        assert manager.headers["Authorization"] == "Bearer test-token"

    def test_init_without_token(self):
        """Test manager initialization without token"""
        with patch.dict(os.environ, {}, clear=True):
            manager = GitHubCICDManager()
            assert manager.github_token is None
            assert manager.headers == {}

    def test_parse_repo_url_https(self):
        """Test parsing HTTPS GitHub URL"""
        owner, repo = self.manager._parse_repo_url(
            "https://github.com/owner/repo"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repo_url_ssh(self):
        """Test parsing SSH GitHub URL"""
        owner, repo = self.manager._parse_repo_url(
            "git@github.com:owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repo_url_with_git_suffix(self):
        """Test parsing GitHub URL with .git suffix"""
        owner, repo = self.manager._parse_repo_url(
            "https://github.com/owner/repo.git"
        )
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_repo_url_invalid(self):
        """Test parsing invalid GitHub URL"""
        with pytest.raises(
            ValueError, match="Could not parse GitHub repository URL"
        ):
            self.manager._parse_repo_url("invalid-url")

    @patch("requests.get")
    async def test_get_pr_info_success(self, mock_get):
        """Test successful PR info retrieval"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/42",
            "head": {"sha": "abc123", "ref": "feature/test"},
            "base": {"ref": "main"},
        }
        mock_get.return_value = mock_response

        result = await self.manager.get_pr_info(self.test_repo_url, 42)

        assert result is not None
        assert result["number"] == 42
        assert result["title"] == "Test PR"
        mock_get.assert_called_once()

    async def test_get_pr_info_no_token(self):
        """Test PR info retrieval without token"""
        manager = GitHubCICDManager()
        result = await manager.get_pr_info(self.test_repo_url, 42)
        assert result is None

    @patch("requests.get")
    async def test_get_commit_status_success(self, mock_get):
        """Test successful commit status retrieval"""
        # Mock status API response
        status_response = Mock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "state": "success",
            "statuses": [],
            "total_count": 0,
            "sha": "abc123",
        }

        # Mock checks API response
        checks_response = Mock()
        checks_response.status_code = 200
        checks_response.json.return_value = {
            "check_runs": [
                {
                    "name": "test",
                    "conclusion": "success",
                    "status": "completed",
                }
            ]
        }

        mock_get.side_effect = [status_response, checks_response]

        result = await self.manager.get_commit_status(
            self.test_repo_url, "abc123"
        )

        assert result["state"] == "success"
        assert "check_runs" in result
        assert len(result["check_runs"]) == 1
        assert mock_get.call_count == 2

    @patch("requests.get")
    async def test_get_workflow_runs_success(self, mock_get):
        """Test successful workflow runs retrieval"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "id": 123,
                    "name": "CI",
                    "status": "completed",
                    "conclusion": "success",
                    "head_branch": "main",
                    "head_sha": "abc123",
                    "event": "push",
                    "created_at": "2023-01-01T00:00:00Z",
                    "html_url": "https://github.com/owner/repo/actions/runs/123",
                }
            ]
        }
        mock_get.return_value = mock_response

        result = await self.manager.get_workflow_runs(
            self.test_repo_url, "main", 10
        )

        assert len(result) == 1
        assert result[0]["name"] == "CI"
        assert result[0]["status"] == "completed"
        mock_get.assert_called_once()

    def test_combine_status_data_all_success(self):
        """Test combining status data when all checks pass"""
        status_data = {"state": "success", "statuses": [], "total_count": 0}
        checks_data = {
            "check_runs": [
                {"conclusion": "success"},
                {"conclusion": "neutral"},
            ]
        }

        result = self.manager._combine_status_data(status_data, checks_data)
        assert result["state"] == "success"

    def test_combine_status_data_with_failure(self):
        """Test combining status data when some checks fail"""
        status_data = {"state": "pending", "statuses": [], "total_count": 0}
        checks_data = {
            "check_runs": [
                {"conclusion": "success"},
                {"conclusion": "failure"},
            ]
        }

        result = self.manager._combine_status_data(status_data, checks_data)
        assert result["state"] == "failure"

    def test_combine_status_data_pending(self):
        """Test combining status data when checks are pending"""
        status_data = {"state": "pending", "statuses": [], "total_count": 0}
        checks_data = {
            "check_runs": [
                {"conclusion": None},  # Still running
            ]
        }

        result = self.manager._combine_status_data(status_data, checks_data)
        assert result["state"] == "pending"

    @patch("requests.get")
    async def test_get_workflow_run_jobs_success(self, mock_get):
        """Test successful workflow run jobs retrieval"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "jobs": [
                {
                    "id": 456,
                    "name": "test",
                    "status": "completed",
                    "conclusion": "success",
                }
            ]
        }
        mock_get.return_value = mock_response

        result = await self.manager.get_workflow_run_jobs(
            self.test_repo_url, 123
        )

        assert len(result) == 1
        assert result[0]["name"] == "test"
        mock_get.assert_called_once()

    @patch.object(GitHubCICDManager, "get_pr_info")
    @patch.object(GitHubCICDManager, "get_workflow_runs")
    async def test_get_pr_workflow_runs_success(
        self, mock_get_runs, mock_get_pr
    ):
        """Test successful PR workflow runs retrieval"""
        # Mock PR info
        mock_get_pr.return_value = {
            "head": {"sha": "abc123", "ref": "feature/test"},
        }

        # Mock workflow runs
        mock_get_runs.return_value = [
            {
                "id": 123,
                "head_sha": "abc123",
                "event": "pull_request",
                "head_branch": "feature/test",
            },
            {
                "id": 124,
                "head_sha": "def456",  # Different SHA
                "event": "push",
                "head_branch": "main",
            },
        ]

        result = await self.manager.get_pr_workflow_runs(
            self.test_repo_url, 42
        )

        assert len(result) == 1  # Only the matching run
        assert result[0]["id"] == 123

    def test_format_workflow_run_summary(self):
        """Test workflow run formatting for frontend"""
        workflow_runs = [
            {
                "id": 123,
                "name": "CI",
                "status": "completed",
                "conclusion": "success",
                "event": "push",
                "head_branch": "main",
                "head_sha": "abc123def456",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:05:00Z",
                "html_url": "https://github.com/owner/repo/actions/runs/123",
                "run_number": 1,
            }
        ]

        result = self.manager.format_workflow_run_summary(workflow_runs)

        assert len(result) == 1
        formatted_run = result[0]
        assert formatted_run["emoji"] == ""
        assert formatted_run["color"] == "green"
        assert formatted_run["commit_sha"] == "abc123d"
        assert formatted_run["name"] == "CI"

    @patch.object(GitHubCICDManager, "get_commit_status")
    @patch.object(GitHubCICDManager, "get_pr_workflow_runs")
    @patch.object(GitHubCICDManager, "get_pr_info")
    async def test_monitor_task_ci_status_with_pr(
        self, mock_get_pr, mock_get_pr_runs, mock_get_commit
    ):
        """Test monitoring CI status for task with PR"""
        # Mock commit status
        mock_get_commit.return_value = {"state": "success"}

        # Mock PR workflow runs
        mock_get_pr_runs.return_value = [
            {"status": "completed", "conclusion": "success"}
        ]

        # Mock PR info
        mock_get_pr.return_value = {
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/42",
        }

        result = await self.manager.monitor_task_ci_status(self.test_task_data)

        assert result["state"] == "success"
        assert "workflow_runs" in result
        assert "pr_info" in result
        assert result["pr_info"]["number"] == 42

    async def test_monitor_task_ci_status_no_repo(self):
        """Test monitoring CI status without repository URL"""
        task_data = {"task_id": "test"}
        result = await self.manager.monitor_task_ci_status(task_data)

        assert result["state"] == "unknown"
        assert "No repository URL" in result["message"]


class TestConvenienceFunctions:
    """Test convenience functions"""

    @patch("github_cicd.github_cicd_manager")
    async def test_get_task_ci_status(self, mock_manager):
        """Test get_task_ci_status convenience function"""
        mock_manager.monitor_task_ci_status = AsyncMock(
            return_value={"state": "success"}
        )

        task_data = {"repository_url": "https://github.com/owner/repo"}
        result = await get_task_ci_status(task_data)

        assert result["state"] == "success"
        mock_manager.monitor_task_ci_status.assert_called_once_with(task_data)

    @patch("github_cicd.github_cicd_manager")
    async def test_get_workflow_runs_for_task_with_pr(self, mock_manager):
        """Test get_workflow_runs_for_task with PR number"""
        mock_manager.get_pr_workflow_runs = AsyncMock(
            return_value=[{"id": 123}]
        )
        mock_manager.format_workflow_run_summary.return_value = [
            {"id": 123, "formatted": True}
        ]

        task_data = {
            "repository_url": "https://github.com/owner/repo",
            "pr_number": 42,
        }
        result = await get_workflow_runs_for_task(task_data)

        assert len(result) == 1
        assert result[0]["formatted"] is True
        mock_manager.get_pr_workflow_runs.assert_called_once()

    @patch("github_cicd.github_cicd_manager")
    async def test_get_workflow_runs_for_task_with_branch(self, mock_manager):
        """Test get_workflow_runs_for_task with branch name"""
        mock_manager.get_workflow_runs = AsyncMock(return_value=[{"id": 123}])
        mock_manager.format_workflow_run_summary.return_value = [
            {"id": 123, "formatted": True}
        ]

        task_data = {
            "repository_url": "https://github.com/owner/repo",
            "branch_name": "feature/test",
        }
        result = await get_workflow_runs_for_task(task_data)

        assert len(result) == 1
        mock_manager.get_workflow_runs.assert_called_once()

    async def test_get_workflow_runs_for_task_no_repo(self):
        """Test get_workflow_runs_for_task without repository URL"""
        task_data = {"task_id": "test"}
        result = await get_workflow_runs_for_task(task_data)

        assert result == []


class TestErrorHandling:
    """Test error handling scenarios"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = GitHubCICDManager("test-token")

    @patch("requests.get")
    async def test_get_pr_info_request_error(self, mock_get):
        """Test PR info retrieval with request error"""
        mock_get.side_effect = requests.RequestException("Network error")

        result = await self.manager.get_pr_info(
            "https://github.com/owner/repo", 42
        )
        assert result is None

    @patch("requests.get")
    async def test_get_commit_status_request_error(self, mock_get):
        """Test commit status retrieval with request error"""
        mock_get.side_effect = requests.RequestException("Network error")

        result = await self.manager.get_commit_status(
            "https://github.com/owner/repo", "abc123"
        )
        assert result["state"] == "error"

    @patch("requests.get")
    async def test_get_workflow_runs_request_error(self, mock_get):
        """Test workflow runs retrieval with request error"""
        mock_get.side_effect = requests.RequestException("Network error")

        result = await self.manager.get_workflow_runs(
            "https://github.com/owner/repo"
        )
        assert result == []

    @patch.object(GitHubCICDManager, "get_commit_status")
    async def test_monitor_task_ci_status_error(self, mock_get_commit):
        """Test monitoring CI status with error"""
        mock_get_commit.side_effect = Exception("Test error")

        task_data = {
            "repository_url": "https://github.com/owner/repo",
            "commit_sha": "abc123",
        }
        result = await self.manager.monitor_task_ci_status(task_data)

        assert result["state"] == "error"
        assert "error" in result


class TestIntegration:
    """Integration tests with real-like data"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = GitHubCICDManager("test-token")

    @patch("requests.get")
    async def test_full_workflow_monitoring(self, mock_get):
        """Test complete workflow monitoring scenario"""
        # Mock multiple API calls
        responses = [
            # Commit status API
            Mock(
                status_code=200,
                json=lambda: {
                    "state": "pending",
                    "statuses": [],
                    "total_count": 0,
                    "sha": "abc123",
                },
            ),
            # Check runs API
            Mock(
                status_code=200,
                json=lambda: {
                    "check_runs": [
                        {
                            "name": "test",
                            "conclusion": "success",
                            "status": "completed",
                        },
                        {
                            "name": "build",
                            "conclusion": "success",
                            "status": "completed",
                        },
                    ]
                },
            ),
            # PR info API
            Mock(
                status_code=200,
                json=lambda: {
                    "number": 42,
                    "title": "Test PR",
                    "state": "open",
                    "html_url": "https://github.com/owner/repo/pull/42",
                    "head": {"sha": "abc123", "ref": "feature/test"},
                    "base": {"ref": "main"},
                },
            ),
            # Workflow runs API
            Mock(
                status_code=200,
                json=lambda: {
                    "workflow_runs": [
                        {
                            "id": 123,
                            "name": "CI",
                            "status": "completed",
                            "conclusion": "success",
                            "head_sha": "abc123",
                            "event": "pull_request",
                            "head_branch": "feature/test",
                            "created_at": "2023-01-01T00:00:00Z",
                            "updated_at": "2023-01-01T00:05:00Z",
                            "html_url": "https://github.com/owner/repo/actions/runs/123",
                            "run_number": 1,
                        }
                    ]
                },
            ),
        ]

        for response in responses:
            response.raise_for_status = Mock()

        mock_get.side_effect = responses

        task_data = {
            "repository_url": "https://github.com/owner/repo",
            "pr_number": 42,
            "commit_sha": "abc123",
        }

        result = await self.manager.monitor_task_ci_status(task_data)

        assert result["state"] == "success"  # All checks passed
        assert len(result["workflow_runs"]) == 1
        # PR info should be populated from the mocked API call
        assert "pr_info" in result
        # Should make multiple API calls (commit status, check runs, PR info,
        # workflow runs)
        assert mock_get.call_count >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
