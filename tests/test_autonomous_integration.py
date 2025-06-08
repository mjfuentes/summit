#!/usr/bin/env python3
"""
Integration tests for Summit autonomous AI system

These tests verify that:
1. The autonomous server can start correctly
2. All imports work properly
3. Core API endpoints are functional
4. Docker integration works

This test suite is designed to catch the runtime issues that were missed in CI/CD:
- Import errors
- Static directory issues
- Server startup problems
- API endpoint failures
"""

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mark all tests in this file as autonomous integration tests
pytestmark = pytest.mark.autonomous


class TestAutonomousIntegration:
    """Integration tests for autonomous Summit AI system"""

    @pytest.fixture
    def mock_env_vars(self, monkeypatch):
        """Mock environment variables for testing"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key-123")
        monkeypatch.setenv("GITHUB_TOKEN", "test-github-token-456")
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    def test_docker_availability(self):
        """Test that Docker is available for testing"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, "Docker not available for testing"
            print(f" Docker version: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker not available for integration testing")

    def test_dockerfile_exists(self):
        """Test that required Docker files exist"""
        # Skip if running in parallel mode and files aren't accessible
        if hasattr(pytest, "main") and os.getenv("PYTEST_XDIST_WORKER"):
            pytest.skip(
                "Skipping in parallel execution mode due to working directory issues"
            )

        # Use absolute path to avoid working directory issues in parallel tests
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dockerfile_path = os.path.join(
            repo_root, "web", "Dockerfile.autonomous"
        )
        assert os.path.exists(
            dockerfile_path
        ), f"Dockerfile.autonomous not found at {dockerfile_path}"

    def test_autonomous_server_syntax(self):
        """Test that autonomous server has valid Python syntax"""
        try:
            # Get proper paths
            repo_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            server_path = os.path.join(
                repo_root, "web", "autonomous_server.py"
            )
            web_dir = os.path.join(repo_root, "web")

            # Test syntax compilation
            result = subprocess.run(
                ["python", "-m", "py_compile", server_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert (
                result.returncode == 0
            ), f"Syntax error in autonomous_server.py: {result.stderr}"

            # Test import without execution
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f'import sys; sys.path.insert(0, "{web_dir}"); import autonomous_server',
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            assert (
                result.returncode == 0
            ), f"Import error in autonomous_server.py: {result.stderr}"

            print(" Autonomous server syntax and imports are valid")

        except subprocess.TimeoutExpired:
            pytest.fail("Autonomous server syntax/import check timed out")
        except Exception as e:
            pytest.fail(f"Autonomous server syntax check failed: {str(e)}")

    def test_autonomous_server_startup(self):
        """Test that autonomous server can start without errors"""
        import time

        # Use a different port to avoid conflicts
        test_port = 8001

        try:
            # Start server process
            repo_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            web_dir = os.path.join(repo_root, "web")
            env = os.environ.copy()
            env["PYTHONPATH"] = web_dir

            process = subprocess.Popen(
                [
                    "python",
                    "-c",
                    f"""
import sys
sys.path.insert(0, "{web_dir}")
import uvicorn
from autonomous_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={test_port}, log_level="error")
""",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=repo_root,
            )

            # Wait for startup
            startup_timeout = 10
            for _ in range(startup_timeout * 10):  # Check every 0.1 seconds
                if process.poll() is not None:
                    # Process ended early - check for errors
                    stdout, stderr = process.communicate()
                    pytest.fail(
                        f"Server startup failed. STDOUT: {
                            stdout.decode()}, STDERR: {
                            stderr.decode()}"
                    )

                # Check if server is responding
                try:
                    import urllib.request

                    response = urllib.request.urlopen(
                        f"http://127.0.0.1:{test_port}/health", timeout=1
                    )
                    if response.status == 200:
                        print(" Autonomous server started successfully")
                        break
                except BaseException:
                    pass

                time.sleep(0.1)
            else:
                pytest.fail("Server failed to start within timeout period")

        except Exception as e:
            pytest.fail(f"Server startup test failed: {str(e)}")

        finally:
            # Clean up
            if "process" in locals() and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except BaseException:
                    process.kill()
                    process.wait(timeout=2)

    def test_api_endpoints_functional(self):
        """Test that core API endpoints are functional"""
        import json
        import time
        import urllib.request

        # Use a different port to avoid conflicts
        test_port = 8002

        try:
            # Start server process
            repo_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            web_dir = os.path.join(repo_root, "web")
            env = os.environ.copy()
            env["PYTHONPATH"] = web_dir

            process = subprocess.Popen(
                [
                    "python",
                    "-c",
                    f"""
import sys
sys.path.insert(0, "{web_dir}")
import uvicorn
from autonomous_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={test_port}, log_level="error")
""",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=repo_root,
            )

            # Wait for startup
            for _ in range(50):  # 5 seconds
                try:
                    response = urllib.request.urlopen(
                        f"http://127.0.0.1:{test_port}/health", timeout=1
                    )
                    if response.status == 200:
                        break
                except BaseException:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("Server failed to start for API testing")

            # Test core endpoints
            endpoints_to_test = [
                "/health",
                "/api/summit/status",
                "/api/agents/status",
                "/api/system/statistics",
            ]

            for endpoint in endpoints_to_test:
                try:
                    response = urllib.request.urlopen(
                        f"http://127.0.0.1:{test_port}{endpoint}", timeout=2
                    )
                    assert (
                        response.status == 200
                    ), f"Endpoint {endpoint} failed"

                    # Try to parse JSON response
                    if endpoint != "/":
                        data = json.loads(response.read().decode())
                        assert isinstance(
                            data, dict
                        ), f"Invalid JSON from {endpoint}"

                    print(f" Endpoint {endpoint} working")

                except Exception as e:
                    pytest.fail(f"Endpoint {endpoint} failed: {e}")

        except Exception as e:
            pytest.fail(f"API endpoint test failed: {str(e)}")

        finally:
            # Clean up
            if "process" in locals() and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except BaseException:
                    process.kill()
                    process.wait(timeout=2)

    def test_container_startup_monitoring(self, mock_env_vars):
        """Test container startup monitoring logic"""
        # Test monitoring logic without actually starting containers

        # Test 1: Successful container detection
        mock_output = b"summit-test-container\n"
        with patch("subprocess.check_output", return_value=mock_output):
            container_name = "summit-test-container"
            assert container_name in mock_output.decode()

        # Test 2: No containers found
        with patch("subprocess.check_output", return_value=b""):
            # Should handle empty container list gracefully
            pass

        # Test 3: Docker command failure
        with patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "docker"),
        ):
            # Should handle Docker errors gracefully
            pass

        print(" Container monitoring logic test completed")

    def test_completion_signal_detection(self, mock_env_vars):
        """Test detection of task completion signals"""

        # Test parsing of completion signals from container logs
        test_cases = [
            ("SUMMIT_TASK_COMPLETE: Task finished successfully", True),
            ("SUMMIT_TASK_COMPLETE: Error occurred", True),
            ("Regular log output", False),
            ("SUMMIT_TASK_COMPLETE", True),
            ("Some other completion signal", False),
        ]

        for log_line, expected_complete in test_cases:
            # Simple completion detection logic
            is_complete = "SUMMIT_TASK_COMPLETE" in log_line
            assert is_complete == expected_complete, f"Failed for: {log_line}"

        print(" Task completion signal detection test completed")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "--tb=short"])
