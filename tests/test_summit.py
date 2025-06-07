#!/usr/bin/env python3

import asyncio
import os
import sys
from unittest.mock import Mock, patch

import pytest
from anthropic import Anthropic

# Add src to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import summit
from summit import (
    create_codespace,
    create_pull_request,
    delete_codespace,
    get_advice_from_claude,
    get_anthropic_client,
    get_codespace_status,
    get_github_headers,
    get_github_repo_info,
    list_user_codespaces,
    plan_capability_implementation,
    start_codespace,
    stop_codespace,
)


@pytest.mark.asyncio
async def test_summit_ai():
    """Test Summit's AI capabilities directly"""

    # Check if API key is set
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    print(f"API key found: {api_key[:20]}...")

    # Test Claude API directly
    try:
        client = Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "You are Summit, an autonomous AI. Say hello and describe your purpose in one sentence.",
                }
            ],
        )

        print("Summit AI Response:")
        print(message.content[0].text)
        print("\nSummit AI is working correctly.")

    except Exception as e:
        print(f"ERROR: Summit AI test failed: {e}")


class TestSummit:
    """Test Summit MCP server functionality"""

    def test_get_anthropic_client_with_key(self):
        """Test getting Anthropic client with API key"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("summit.Anthropic") as mock_anthropic:
                client = get_anthropic_client()
                mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_get_anthropic_client_without_key(self):
        """Test getting Anthropic client without API key"""
        with patch.dict(os.environ, {}, clear=True):
            client = get_anthropic_client()
            assert client is None

    def test_get_github_headers_with_token(self):
        """Test getting GitHub headers with token"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            headers = get_github_headers()
            expected = {
                "Authorization": "Bearer test-token",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            assert headers == expected

    def test_get_github_headers_without_token(self):
        """Test getting GitHub headers without token"""
        with patch.dict(os.environ, {}, clear=True):
            headers = get_github_headers()
            assert headers is None

    def test_get_github_repo_info_from_env(self):
        """Test getting repo info from environment variables"""
        with patch.dict(
            os.environ,
            {"GITHUB_OWNER": "test-owner", "GITHUB_REPO": "test-repo"},
        ):
            owner, repo = get_github_repo_info()
            assert owner == "test-owner"
            assert repo == "test-repo"

    def test_get_github_repo_info_from_git_ssh(self):
        """Test getting repo info from git remote SSH URL"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = (
                    "git@github.com:test-owner/test-repo.git\n"
                )

                owner, repo = get_github_repo_info()
                assert owner == "test-owner"
                assert repo == "test-repo"

    def test_get_github_repo_info_from_git_https(self):
        """Test getting repo info from git remote HTTPS URL"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = (
                    "https://github.com/test-owner/test-repo.git\n"
                )

                owner, repo = get_github_repo_info()
                assert owner == "test-owner"
                assert repo == "test-repo"

    def test_get_github_repo_info_failure(self):
        """Test getting repo info when git command fails"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 1

                owner, repo = get_github_repo_info()
                assert owner is None
                assert repo is None

    @pytest.mark.asyncio
    async def test_get_advice_from_claude_success(self):
        """Test getting advice from Claude successfully"""
        mock_client = Mock()
        mock_message = Mock()
        mock_content_item = Mock()
        mock_content_item.text = "Test advice response"
        mock_message.content = [mock_content_item]

        # Mock usage attributes
        mock_usage = Mock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 100
        mock_message.usage = mock_usage

        mock_client.messages.create.return_value = mock_message

        with patch("summit.get_anthropic_client", return_value=mock_client):
            with patch("summit.cost_tracker") as mock_tracker:
                mock_tracker.can_make_request.return_value = True
                mock_tracker.can_make_call.return_value = (True, None)
                mock_tracker.record_call.return_value = 0.01
                mock_tracker.get_daily_spent.return_value = 0.05
                mock_tracker.daily_budget = 1.00

                result = await get_advice_from_claude("test question")
                assert "Test advice response" in result
                mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_advice_from_claude_no_client(self):
        """Test getting advice when no Anthropic client available"""
        with patch("summit.get_anthropic_client", return_value=None):
            result = await get_advice_from_claude("test question")
            assert "ANTHROPIC_API_KEY" in result

    @pytest.mark.asyncio
    async def test_get_advice_from_claude_budget_exceeded(self):
        """Test getting advice when budget is exceeded"""
        with patch("summit.get_anthropic_client", return_value=Mock()):
            with patch("summit.cost_tracker") as mock_tracker:
                mock_tracker.can_make_call.return_value = (
                    False,
                    "Budget exceeded",
                )

                result = await get_advice_from_claude("test question")
                assert "budget" in result.lower()

    @pytest.mark.asyncio
    async def test_create_codespace_success(self):
        """Test creating a codespace successfully"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "codespace-123",
            "name": "test-codespace",
            "state": "Available",
            "web_url": "https://test.github.dev",
            "created_at": "2023-01-01T00:00:00Z",
        }

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.post", return_value=mock_response):
                result = await create_codespace("owner", "repo")
                assert result["name"] == "test-codespace"
                assert result["state"] == "Available"

    @pytest.mark.asyncio
    async def test_create_codespace_no_headers(self):
        """Test creating codespace without GitHub headers"""
        with patch("summit.get_github_headers", return_value=None):
            with pytest.raises(
                ValueError,
                match="GITHUB_TOKEN environment variable is required",
            ):
                await create_codespace("owner", "repo")

    @pytest.mark.asyncio
    async def test_start_codespace_success(self):
        """Test starting a codespace successfully"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"state": "Starting"}

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.post", return_value=mock_response):
                result = await start_codespace("test-codespace")
                assert result["state"] == "Starting"

    @pytest.mark.asyncio
    async def test_stop_codespace_success(self):
        """Test stopping a codespace successfully"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"state": "Stopping"}

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.post", return_value=mock_response):
                result = await stop_codespace("test-codespace")
                assert result["state"] == "Stopping"

    @pytest.mark.asyncio
    async def test_delete_codespace_success(self):
        """Test deleting a codespace successfully"""
        mock_response = Mock()
        mock_response.status_code = 204

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.delete", return_value=mock_response):
                result = await delete_codespace("test-codespace")
                assert result is True

    @pytest.mark.asyncio
    async def test_get_codespace_status_success(self):
        """Test getting codespace status successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test-codespace",
            "state": "Available",
        }

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.get", return_value=mock_response):
                result = await get_codespace_status("test-codespace")
                assert result["name"] == "test-codespace"
                assert result["state"] == "Available"

    @pytest.mark.asyncio
    async def test_list_user_codespaces_success(self):
        """Test listing user codespaces successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "codespaces": [
                {"name": "codespace1", "state": "Available"},
                {"name": "codespace2", "state": "Stopped"},
            ]
        }

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.get", return_value=mock_response):
                result = await list_user_codespaces()
                assert len(result) == 2
                assert result[0]["name"] == "codespace1"

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self):
        """Test creating a pull request successfully"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "number": 123,
            "html_url": "https://github.com/owner/repo/pull/123",
            "state": "open",
            "title": "Test PR",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
        }

        with patch(
            "summit.get_github_headers",
            return_value={"Authorization": "Bearer test"},
        ):
            with patch("requests.post", return_value=mock_response):
                result = await create_pull_request(
                    "owner", "repo", "Test PR", "feature-branch"
                )
                assert result["number"] == 123
                assert result["state"] == "open"

    @pytest.mark.asyncio
    async def test_plan_capability_implementation_success(self):
        """Test planning capability implementation successfully"""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock(text="Implementation plan")]
        mock_client.messages.create.return_value = mock_message

        with patch("summit.get_anthropic_client", return_value=mock_client):
            with patch(
                "summit.get_github_repo_info", return_value=("owner", "repo")
            ):
                result = await plan_capability_implementation(
                    "test capability"
                )
                assert "Implementation plan" in result
                mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_plan_capability_implementation_no_client(self):
        """Test planning capability when no client available"""
        with patch("summit.get_anthropic_client", return_value=None):
            result = await plan_capability_implementation("test capability")
            assert "ANTHROPIC_API_KEY" in result


def test_summit_ai():
    """Test Summit AI basic functionality"""
    # This test verifies that the summit module can be imported and basic functions work
    assert hasattr(summit, "server")
    assert hasattr(summit, "cost_tracker")
    assert callable(get_anthropic_client)
    assert callable(get_github_headers)
    assert callable(get_github_repo_info)


if __name__ == "__main__":
    asyncio.run(test_summit_ai())
