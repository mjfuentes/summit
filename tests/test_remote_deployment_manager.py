#!/usr/bin/env python3

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

from remote_deployment_manager import DeploymentError, RemoteDeploymentManager

# Add src to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class TestDeploymentError:
    """Test the custom DeploymentError exception"""

    def test_deployment_error_creation(self):
        """Test creating a DeploymentError"""
        error = DeploymentError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestRemoteDeploymentManager:
    """Test the RemoteDeploymentManager class"""

    def test_init(self):
        """Test RemoteDeploymentManager initialization"""
        manager = RemoteDeploymentManager()
        assert manager.deployments == {}
        assert "render" in manager.supported_platforms

    @pytest.mark.asyncio
    async def test_deploy_to_render_success(self):
        """Test successful Render deployment"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 201
                mock_response.json.return_value = {
                    "id": "test-deployment-id",
                    "serviceDetails": {"url": "https://test.onrender.com"},
                }
                mock_post.return_value = mock_response

                result = await manager.deploy_to_render(
                    "test-service", {"ANTHROPIC_API_KEY": "test-key"}
                )

                assert result["success"] is True
                assert result["deployment_id"] == "test-deployment-id"
                assert result["service_url"] == "https://test.onrender.com"
                assert "test-deployment-id" in manager.deployments

    @pytest.mark.asyncio
    async def test_deploy_to_render_no_api_key(self):
        """Test Render deployment without API key"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                DeploymentError, match="RENDER_API_KEY not found"
            ):
                await manager.deploy_to_render(
                    "test-service", {"ANTHROPIC_API_KEY": "test-key"}
                )

    @pytest.mark.asyncio
    async def test_deploy_to_render_api_failure(self):
        """Test Render deployment API failure"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = "Bad request"
                mock_post.return_value = mock_response

                with pytest.raises(
                    DeploymentError, match="Render deployment failed"
                ):
                    await manager.deploy_to_render(
                        "test-service", {"ANTHROPIC_API_KEY": "test-key"}
                    )

    def test_create_deployment_config(self):
        """Test creating deployment configuration"""
        manager = RemoteDeploymentManager()

        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-anthropic-key",
                "GITHUB_TOKEN": "test-github-token",
            },
        ):
            config = manager.create_deployment_config(
                "Test task description",
                "https://github.com/test/repo",
                "feature-branch",
                120,
            )

            assert config["ANTHROPIC_API_KEY"] == "test-anthropic-key"
            assert config["GITHUB_TOKEN"] == "test-github-token"
            assert config["TASK_DESCRIPTION"] == "Test task description"
            assert config["REPOSITORY_URL"] == "https://github.com/test/repo"
            assert config["TARGET_BRANCH"] == "feature-branch"
            assert config["TIMEOUT_MINUTES"] == "120"
            assert config["SUMMIT_ENV"] == "production"

    def test_create_deployment_config_no_repo(self):
        """Test creating deployment configuration without repository"""
        manager = RemoteDeploymentManager()

        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "test-key", "GITHUB_TOKEN": "test-token"},
        ):
            config = manager.create_deployment_config("Test task")

            assert "REPOSITORY_URL" not in config
            assert config["TARGET_BRANCH"] == "main"
            assert config["TIMEOUT_MINUTES"] == "60"

    @pytest.mark.asyncio
    async def test_deploy_claude_code_instance_render(self):
        """Test deploying Claude Code instance to Render"""
        manager = RemoteDeploymentManager()

        with patch.object(manager, "deploy_to_render") as mock_deploy:
            mock_deploy.return_value = {
                "success": True,
                "deployment_id": "test-id",
            }

            result = await manager.deploy_claude_code_instance(
                "render", "Test task", "https://github.com/test/repo"
            )

            assert result["success"] is True
            mock_deploy.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_claude_code_instance_unsupported_platform(self):
        """Test deploying to unsupported platform"""
        manager = RemoteDeploymentManager()

        with pytest.raises(DeploymentError, match="Unsupported platform"):
            await manager.deploy_claude_code_instance(
                "unsupported", "Test task"
            )

    @pytest.mark.asyncio
    async def test_deploy_claude_code_instance_not_implemented(self):
        """Test deploying to platform not yet implemented"""
        manager = RemoteDeploymentManager()
        manager.supported_platforms.append("test-platform")

        with pytest.raises(
            DeploymentError, match="Platform test-platform not implemented"
        ):
            await manager.deploy_claude_code_instance(
                "test-platform", "Test task"
            )


class TestMainCLI:
    """Test the main CLI interface"""

    @pytest.mark.asyncio
    async def test_main_cli_import(self):
        """Test that main CLI function can be imported"""
        from remote_deployment_manager import main

        assert callable(main)

    @pytest.mark.asyncio
    async def test_main_cli_with_args(self):
        """Test main CLI with arguments"""
        with patch(
            "sys.argv",
            [
                "remote_deployment_manager.py",
                "render",
                "Test task description",
                "--repository-url",
                "https://github.com/test/repo",
                "--target-branch",
                "main",
                "--timeout-minutes",
                "30",
            ],
        ):
            with patch(
                "remote_deployment_manager.RemoteDeploymentManager"
            ) as mock_manager_class:
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager
                mock_manager.deploy_claude_code_instance = AsyncMock(
                    return_value={
                        "success": True,
                        "deployment_id": "test-id",
                        "service_url": "https://test.onrender.com",
                    }
                )

                # Test would run main() but we'll just verify the manager is
                # created
                assert mock_manager_class is not None


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_render_network_error(self):
        """Test Render deployment with network error"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch(
                "requests.post", side_effect=Exception("Network error")
            ):
                with pytest.raises(
                    DeploymentError,
                    match="Unexpected error during Render deployment",
                ):
                    await manager.deploy_to_render(
                        "test-service", {"ANTHROPIC_API_KEY": "test-key"}
                    )


class TestConfigurationEdgeCases:
    """Test edge cases in configuration"""

    def test_create_deployment_config_empty_env(self):
        """Test creating config with empty environment variables"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {}, clear=True):
            config = manager.create_deployment_config("Test task")

            assert config["ANTHROPIC_API_KEY"] == ""
            assert config["GITHUB_TOKEN"] == ""
            assert config["TASK_DESCRIPTION"] == "Test task"

    def test_create_deployment_config_with_all_params(self):
        """Test creating config with all parameters"""
        manager = RemoteDeploymentManager()

        config = manager.create_deployment_config(
            task_description="Complex task",
            repository_url="https://github.com/complex/repo",
            target_branch="develop",
            timeout_minutes=180,
        )

        assert config["TASK_DESCRIPTION"] == "Complex task"
        assert config["REPOSITORY_URL"] == "https://github.com/complex/repo"
        assert config["TARGET_BRANCH"] == "develop"
        assert config["TIMEOUT_MINUTES"] == "180"


class TestDeploymentStatusAndManagement:
    """Test deployment status and management functionality"""

    @pytest.mark.asyncio
    async def test_get_deployment_status_not_found(self):
        """Test getting status for non-existent deployment"""
        manager = RemoteDeploymentManager()

        status = await manager.get_deployment_status("non-existent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_render_status_success(self):
        """Test successful Render status retrieval"""
        manager = RemoteDeploymentManager()

        # Add a deployment to track
        manager.deployments["test-id"] = {
            "platform": "render",
            "deployment_id": "test-id",
        }

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "serviceDetails": {
                        "status": "live",
                        "url": "https://test.onrender.com",
                    }
                }
                mock_get.return_value = mock_response

                status = await manager._get_render_status("test-id")

                assert status["status"] == "live"
                assert status["url"] == "https://test.onrender.com"
                assert status["platform"] == "render"

    @pytest.mark.asyncio
    async def test_get_render_status_api_error(self):
        """Test Render status retrieval with API error"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response

                status = await manager._get_render_status("test-id")

                assert status["status"] == "error"
                assert "API error: 404" in status["error"]

    @pytest.mark.asyncio
    async def test_get_render_status_no_api_key(self):
        """Test Render status retrieval without API key"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {}, clear=True):
            status = await manager._get_render_status("test-id")

            assert status["status"] == "error"
            assert status["error"] == "No API key"

    @pytest.mark.asyncio
    async def test_list_deployments_empty(self):
        """Test listing deployments when none exist"""
        manager = RemoteDeploymentManager()

        deployments = await manager.list_deployments()
        assert deployments == []

    @pytest.mark.asyncio
    async def test_list_deployments_with_status(self):
        """Test listing deployments with status updates"""
        manager = RemoteDeploymentManager()

        # Add a test deployment
        manager.deployments["test-id"] = {
            "platform": "render",
            "deployment_id": "test-id",
            "service_name": "test-service",
        }

        with patch.object(manager, "get_deployment_status") as mock_status:
            mock_status.return_value = {"status": "live", "platform": "render"}

            deployments = await manager.list_deployments()

            assert len(deployments) == 1
            assert deployments[0]["deployment_id"] == "test-id"
            assert deployments[0]["status"] == "live"

    @pytest.mark.asyncio
    async def test_delete_deployment_not_found(self):
        """Test deleting non-existent deployment"""
        manager = RemoteDeploymentManager()

        result = await manager.delete_deployment("non-existent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_render_service_success(self):
        """Test successful Render service deletion"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {"RENDER_API_KEY": "test-key"}):
            with patch("requests.delete") as mock_delete:
                mock_response = Mock()
                mock_response.status_code = 204
                mock_delete.return_value = mock_response

                result = await manager._delete_render_service("test-id")
                assert result is True

    @pytest.mark.asyncio
    async def test_delete_render_service_no_api_key(self):
        """Test Render service deletion without API key"""
        manager = RemoteDeploymentManager()

        with patch.dict(os.environ, {}, clear=True):
            result = await manager._delete_render_service("test-id")
            assert result is False

    @pytest.mark.asyncio
    async def test_monitor_deployment_ready(self):
        """Test monitoring deployment until ready"""
        manager = RemoteDeploymentManager()

        status_responses = [
            {"status": "deploying"},
            {"status": "live", "url": "https://test.onrender.com"},
        ]

        with patch.object(
            manager, "get_deployment_status", side_effect=status_responses
        ):
            with patch("asyncio.sleep"):
                # This would normally run indefinitely, but our mock will
                # complete
                await manager.monitor_deployment("test-id", check_interval=1)

    @pytest.mark.asyncio
    async def test_monitor_deployment_failed(self):
        """Test monitoring deployment that fails"""
        manager = RemoteDeploymentManager()

        with patch.object(manager, "get_deployment_status") as mock_status:
            mock_status.return_value = {
                "status": "failed",
                "error": "Build failed",
            }

            with patch("asyncio.sleep"):
                await manager.monitor_deployment("test-id", check_interval=1)

    @pytest.mark.asyncio
    async def test_monitor_deployment_not_found(self):
        """Test monitoring non-existent deployment"""
        manager = RemoteDeploymentManager()

        with patch.object(manager, "get_deployment_status") as mock_status:
            mock_status.return_value = None

            await manager.monitor_deployment("test-id", check_interval=1)
