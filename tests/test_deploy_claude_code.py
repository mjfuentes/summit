#!/usr/bin/env python3

import os
import sys
from unittest.mock import Mock, patch

# Add scripts to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts_path = os.path.join(repo_root, "scripts")
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)


class TestDeployClaudeCodeCLI:
    """Test the deploy_claude_code CLI script"""

    def test_import_functions(self):
        """Test that CLI functions can be imported"""
        from deploy_claude_code import (
            check_github_cli,
            run_command,
            validate_environment,
        )

        assert callable(check_github_cli)
        assert callable(run_command)
        assert callable(validate_environment)

    def test_run_command_success(self):
        """Test run_command with successful command"""
        from deploy_claude_code import run_command

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "success output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            code, stdout, stderr = run_command(["echo", "test"])

            assert code == 0
            assert stdout == "success output"
            assert stderr == ""

    def test_run_command_failure(self):
        """Test run_command with failed command"""
        from deploy_claude_code import run_command

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "error output"
            mock_run.return_value = mock_result

            code, stdout, stderr = run_command(["false"])

            assert code == 1
            assert stdout == ""
            assert stderr == "error output"

    def test_run_command_timeout(self):
        """Test run_command with timeout"""
        import subprocess

        from deploy_claude_code import run_command

        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("test", 1)
        ):
            code, stdout, stderr = run_command(["sleep", "10"], timeout=1)

            assert code == -1
            assert stdout == ""
            assert "timed out" in stderr.lower()

    def test_check_github_cli_available(self):
        """Test check_github_cli when CLI is available"""
        from deploy_claude_code import check_github_cli

        with patch("deploy_claude_code.run_command") as mock_run:
            mock_run.return_value = (0, "gh version 2.0.0", "")

            result = check_github_cli()
            assert result is True

    def test_check_github_cli_not_available(self):
        """Test check_github_cli when CLI is not available"""
        from deploy_claude_code import check_github_cli

        with patch("deploy_claude_code.run_command") as mock_run:
            mock_run.return_value = (1, "", "command not found")

            result = check_github_cli()
            assert result is False

    def test_validate_environment_success(self):
        """Test validate_environment with all requirements met"""
        from deploy_claude_code import validate_environment

        with patch("os.path.exists", return_value=True):
            with patch(
                "deploy_claude_code.check_github_cli", return_value=True
            ):
                with patch(
                    "deploy_claude_code.run_command", return_value=(0, "", "")
                ):
                    with patch.dict(
                        os.environ, {"ANTHROPIC_API_KEY": "test-key"}
                    ):
                        result = validate_environment()
                        assert result is True

    def test_validate_environment_missing_files(self):
        """Test validate_environment with missing files"""
        from deploy_claude_code import validate_environment

        with patch("os.path.exists", return_value=False):
            result = validate_environment()
            assert result is False

    def test_validate_environment_missing_github_cli(self):
        """Test validate_environment without GitHub CLI"""
        from deploy_claude_code import validate_environment

        with patch("os.path.exists", return_value=True):
            with patch(
                "deploy_claude_code.check_github_cli", return_value=False
            ):
                result = validate_environment()
                assert result is False

    def test_validate_environment_missing_env_var(self):
        """Test validate_environment without required environment variables"""
        from deploy_claude_code import validate_environment

        with patch("os.path.exists", return_value=True):
            with patch(
                "deploy_claude_code.check_github_cli", return_value=True
            ):
                with patch(
                    "deploy_claude_code.run_command", return_value=(0, "", "")
                ):
                    with patch.dict(os.environ, {}, clear=True):
                        result = validate_environment()
                        assert result is False

    def test_trigger_github_workflow_success(self):
        """Test triggering GitHub workflow successfully"""
        from deploy_claude_code import trigger_github_workflow

        with patch("deploy_claude_code.check_github_cli", return_value=True):
            with patch("deploy_claude_code.run_command") as mock_run:
                mock_run.return_value = (0, "workflow triggered", "")

                result = trigger_github_workflow()
                assert result is True

    def test_trigger_github_workflow_no_cli(self):
        """Test triggering workflow without GitHub CLI"""
        from deploy_claude_code import trigger_github_workflow

        with patch("deploy_claude_code.check_github_cli", return_value=False):
            result = trigger_github_workflow()
            assert result is False

    def test_trigger_github_workflow_failure(self):
        """Test triggering workflow with failure"""
        from deploy_claude_code import trigger_github_workflow

        with patch("deploy_claude_code.check_github_cli", return_value=True):
            with patch("deploy_claude_code.run_command") as mock_run:
                mock_run.return_value = (1, "", "workflow failed")

                result = trigger_github_workflow()
                assert result is False

    def test_get_workflow_status_success(self):
        """Test getting workflow status successfully"""
        from deploy_claude_code import get_workflow_status

        with patch("deploy_claude_code.check_github_cli", return_value=True):
            with patch("deploy_claude_code.run_command") as mock_run:
                mock_run.return_value = (
                    0,
                    '[{"status": "completed", "conclusion": "success"}]',
                    "",
                )

                result = get_workflow_status()
                assert result is not None
                assert result["status"] == "completed"

    def test_get_workflow_status_no_cli(self):
        """Test getting workflow status without GitHub CLI"""
        from deploy_claude_code import get_workflow_status

        with patch("deploy_claude_code.check_github_cli", return_value=False):
            result = get_workflow_status()
            assert result is None

    def test_check_container_image_success(self):
        """Test checking container image successfully"""
        from deploy_claude_code import check_container_image

        with patch("deploy_claude_code.run_command") as mock_run:
            mock_run.return_value = (0, '{"config": {"size": 1000}}', "")

            result = check_container_image()
            assert result is True

    def test_check_container_image_failure(self):
        """Test checking container image with failure"""
        from deploy_claude_code import check_container_image

        with patch("deploy_claude_code.run_command") as mock_run:
            mock_run.return_value = (1, "", "image not found")

            result = check_container_image()
            assert result is False
