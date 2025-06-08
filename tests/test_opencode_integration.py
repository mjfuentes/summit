#!/usr/bin/env python3
"""Tests for OpenCode integration"""

from unittest.mock import AsyncMock, mock_open, patch

import pytest

from src.opencode_integration import (
    OpenCodeConfig,
    OpenCodeManager,
    SummitOpenCodeIntegration,
    initialize_opencode_integration,
)


class TestOpenCodeConfig:
    """Test OpenCodeConfig dataclass"""

    def test_opencode_config_defaults(self):
        """Test OpenCodeConfig with default values"""
        config = OpenCodeConfig()

        assert config.opencode_path == "opencode"
        assert config.model_provider == "anthropic"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        assert config.api_key is None
        assert config.local_endpoint is None
        assert config.session_dir is None
        assert config.custom_commands_dir is None
        assert config.timeout == 300
        assert config.working_directory == "."

    def test_opencode_config_custom_values(self):
        """Test OpenCodeConfig with custom values"""
        config = OpenCodeConfig(
            opencode_path="/usr/local/bin/opencode",
            model_provider="local",
            model_name="llama-3.1-8b",
            api_key="test-key",
            local_endpoint="http://localhost:8000",
            session_dir="/tmp/sessions",
            custom_commands_dir="/tmp/commands",
            timeout=600,
            working_directory="/workspace",
        )

        assert config.opencode_path == "/usr/local/bin/opencode"
        assert config.model_provider == "local"
        assert config.model_name == "llama-3.1-8b"
        assert config.api_key == "test-key"
        assert config.local_endpoint == "http://localhost:8000"
        assert config.session_dir == "/tmp/sessions"
        assert config.custom_commands_dir == "/tmp/commands"
        assert config.timeout == 600
        assert config.working_directory == "/workspace"


class TestOpenCodeManager:
    """Test OpenCodeManager class"""

    def test_init(self):
        """Test manager initialization"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        assert manager.config == config
        assert manager.current_session_id is None

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_check_installation_success(self, mock_run):
        """Test successful installation check"""
        mock_run.return_value = {
            "success": True,
            "output": "opencode version 1.0.0",
        }

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.check_installation()

        assert result is True
        mock_run.assert_called_once_with(["opencode", "--version"])

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_check_installation_failure(self, mock_run):
        """Test installation check failure"""
        mock_run.return_value = {
            "success": False,
            "error": "Command not found",
        }

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.check_installation()

        assert result is False

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_install_opencode_success(self, mock_run):
        """Test successful OpenCode installation"""
        mock_run.side_effect = [
            {"success": True, "output": "Installation complete"},
            {"success": True, "output": "opencode version 1.0.0"},
        ]

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.install_opencode()

        assert result is True

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_install_opencode_failure(self, mock_run):
        """Test OpenCode installation failure"""
        mock_run.return_value = {
            "success": False,
            "error": "Installation failed",
        }

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.install_opencode()

        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    async def test_setup_configuration_success(self, mock_mkdir, mock_file):
        """Test successful configuration setup"""
        config = OpenCodeConfig(api_key="test-key")
        manager = OpenCodeManager(config)

        result = await manager.setup_configuration()

        assert result is True
        mock_mkdir.assert_called()
        mock_file.assert_called()

    @patch("pathlib.Path.mkdir")
    async def test_setup_configuration_failure(self, mock_mkdir):
        """Test configuration setup failure"""
        mock_mkdir.side_effect = Exception("Permission denied")

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.setup_configuration()

        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    async def test_create_custom_command_success(self, mock_mkdir, mock_file):
        """Test successful custom command creation"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.create_custom_command(
            "test_cmd", "Test content"
        )

        assert result is True
        mock_file.assert_called()

    @patch("pathlib.Path.mkdir")
    async def test_create_custom_command_failure(self, mock_mkdir):
        """Test custom command creation failure"""
        mock_mkdir.side_effect = Exception("Permission denied")

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.create_custom_command(
            "test_cmd", "Test content"
        )

        assert result is False

    @patch("pathlib.Path.mkdir")
    async def test_start_session_success(self, mock_mkdir):
        """Test successful session start"""
        config = OpenCodeConfig(session_dir="/tmp/sessions")
        manager = OpenCodeManager(config)

        session_id = await manager.start_session("Test task")

        assert session_id is not None
        assert session_id.startswith("summit-")
        assert manager.current_session_id == session_id

    async def test_start_session_failure(self):
        """Test session start failure"""
        config = OpenCodeConfig(
            session_dir="/tmp/sessions"
        )  # Set session_dir to trigger mkdir
        manager = OpenCodeManager(config)

        # Mock pathlib.Path.mkdir to raise an exception
        with patch(
            "pathlib.Path.mkdir", side_effect=Exception("Permission denied")
        ):
            session_id = await manager.start_session("Test task")

            assert session_id is None

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_send_message_success(self, mock_run):
        """Test successful message sending"""
        mock_run.return_value = {
            "success": True,
            "output": "Response from OpenCode",
        }

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)
        manager.current_session_id = "test-session"

        result = await manager.send_message("Test message")

        assert result["success"] is True
        assert "output" in result

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_send_message_failure(self, mock_run):
        """Test message sending failure"""
        mock_run.return_value = {"success": False, "error": "Command failed"}

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)
        manager.current_session_id = "test-session"

        result = await manager.send_message("Test message")

        assert result["success"] is False

    async def test_send_message_exception(self):
        """Test message sending with exception"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        with patch(
            "tempfile.NamedTemporaryFile", side_effect=Exception("File error")
        ):
            result = await manager.send_message("Test message")

            assert result["success"] is False
            assert "File error" in result["error"]

    @patch("src.opencode_integration.OpenCodeManager._run_command")
    async def test_execute_task_success(self, mock_run):
        """Test successful task execution"""
        mock_run.return_value = {"success": True, "output": "Task completed"}

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager.execute_task("Test task")

        assert result["success"] is True
        assert "output" in result

    async def test_execute_task_failure(self):
        """Test task execution failure"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        with patch(
            "tempfile.NamedTemporaryFile", side_effect=Exception("File error")
        ):
            result = await manager.execute_task("Test task")

            assert result["success"] is False
            assert "File error" in result["error"]

    async def test_get_session_history(self):
        """Test getting session history"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        history = await manager.get_session_history("test-session")

        assert isinstance(history, list)

    async def test_list_sessions(self):
        """Test listing sessions"""
        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        sessions = await manager.list_sessions()

        assert isinstance(sessions, list)

    @patch("asyncio.create_subprocess_exec")
    async def test_run_command_success(self, mock_subprocess):
        """Test successful command execution"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Success output", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager._run_command(["echo", "test"])

        assert result["success"] is True
        assert "Success output" in result["output"]

    @patch("asyncio.create_subprocess_exec")
    async def test_run_command_failure(self, mock_subprocess):
        """Test command execution failure"""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"Error output")
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        config = OpenCodeConfig()
        manager = OpenCodeManager(config)

        result = await manager._run_command(["false"])

        assert result["success"] is False
        assert "Error output" in result["error"]


class TestSummitOpenCodeIntegration:
    """Test SummitOpenCodeIntegration class"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        integration = SummitOpenCodeIntegration()

        assert integration.opencode is not None
        assert integration.opencode.config is not None

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = OpenCodeConfig(model_provider="local")
        integration = SummitOpenCodeIntegration(config)

        assert integration.opencode.config == config
        assert integration.opencode is not None

    @patch("src.opencode_integration.OpenCodeManager.check_installation")
    @patch("src.opencode_integration.OpenCodeManager.setup_configuration")
    async def test_initialize_success(self, mock_setup, mock_check):
        """Test successful initialization"""
        mock_check.return_value = True
        mock_setup.return_value = True

        integration = SummitOpenCodeIntegration()

        result = await integration.initialize()

        assert result is True

    @patch("src.opencode_integration.OpenCodeManager.check_installation")
    async def test_initialize_not_installed(self, mock_check):
        """Test initialization when OpenCode not installed"""
        mock_check.return_value = False

        integration = SummitOpenCodeIntegration()

        result = await integration.initialize()

        assert result is False

    @patch("src.opencode_integration.OpenCodeManager.execute_task")
    async def test_execute_development_task(self, mock_execute):
        """Test development task execution"""
        mock_execute.return_value = {"status": "success"}

        integration = SummitOpenCodeIntegration()

        result = await integration.execute_development_task("Test task")

        assert result["status"] == "success"

    @patch("src.opencode_integration.OpenCodeManager.send_message")
    async def test_analyze_codebase(self, mock_send):
        """Test codebase analysis"""
        mock_send.return_value = {
            "success": True,
            "output": "Analysis complete",
        }

        integration = SummitOpenCodeIntegration()
        integration.opencode.current_session_id = "test-session"

        result = await integration.analyze_codebase()

        assert result["success"] is True

    @patch("src.opencode_integration.OpenCodeManager.send_message")
    async def test_implement_feature(self, mock_send):
        """Test feature implementation"""
        mock_send.return_value = {
            "success": True,
            "output": "Feature implemented",
        }

        integration = SummitOpenCodeIntegration()
        integration.opencode.current_session_id = "test-session"

        result = await integration.implement_feature("New feature")

        assert result["success"] is True

    @patch("src.opencode_integration.OpenCodeManager.send_message")
    async def test_debug_issues(self, mock_send):
        """Test issue debugging"""
        mock_send.return_value = {"success": True, "output": "Issues debugged"}

        integration = SummitOpenCodeIntegration()
        integration.opencode.current_session_id = "test-session"

        result = await integration.debug_issues()

        assert result["success"] is True


class TestUtilityFunctions:
    """Test utility functions"""

    @patch("src.opencode_integration.SummitOpenCodeIntegration")
    async def test_initialize_opencode_integration(
        self, mock_integration_class
    ):
        """Test OpenCode integration initialization"""
        mock_integration = AsyncMock()
        mock_integration.initialize.return_value = True
        mock_integration_class.return_value = mock_integration

        integration = await initialize_opencode_integration(
            model_provider="local", model_name="llama-3.1-8b"
        )

        assert integration is not None
        mock_integration.initialize.assert_called_once()

    @patch("src.opencode_integration.SummitOpenCodeIntegration")
    async def test_initialize_opencode_integration_failure(
        self, mock_integration_class
    ):
        """Test OpenCode integration initialization failure"""
        mock_integration = AsyncMock()
        mock_integration.initialize.return_value = False
        mock_integration_class.return_value = mock_integration

        with pytest.raises(
            Exception, match="Failed to initialize OpenCode integration"
        ):
            await initialize_opencode_integration()
