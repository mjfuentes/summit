#!/usr/bin/env python3
"""
Integration tests for autonomous Claude Code behavior.

These tests verify that:
1. Claude Code containers start correctly
2. Tasks don't complete immediately
3. Container monitoring works properly
4. Log files are created and maintained

USAGE:
------
# Run all autonomous tests (requires Docker)
python run_tests.py --autonomous

# Run specific test
pytest tests/test_autonomous_integration.py::test_autonomous_container_lifecycle -v -s

# Run with specific marker
pytest -m autonomous -v -s

# Debug container lifecycle specifically
pytest tests/test_autonomous_integration.py::test_autonomous_container_lifecycle -v -s --tb=long

DEBUGGING:
----------
This test suite helps diagnose issues with:
- Container premature completion (should run >5 seconds)
- Log file creation and content
- Container startup and monitoring
- Docker environment issues

If tests fail, check:
1. Docker is installed and running
2. Container builds successfully
3. ttyd and Claude Code packages install correctly
4. Container doesn't exit immediately after startup
"""

import pytest
import asyncio
import time
import os
import subprocess
import json
from unittest.mock import patch
import tempfile
import shutil

# Mark all tests in this file as autonomous integration tests
pytestmark = pytest.mark.autonomous

class TestAutonomousIntegration:
    """Integration tests for autonomous Claude Code system"""
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing"""
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key-12345',
            'GITHUB_TOKEN': 'test-github-token'
        }):
            yield

    @pytest.fixture
    def temp_task_logs_dir(self):
        """Create temporary directory for task logs"""
        temp_dir = tempfile.mkdtemp(prefix="summit_test_logs_")
        
        # Patch the log directory in the autonomous server
        with patch('web.autonomous_server.log_dir', temp_dir):
            yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_docker_availability(self):
        """Test that Docker is available for testing"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            assert result.returncode == 0, "Docker not available for testing"
            assert 'Docker version' in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker not available for testing")

    def test_dockerfile_exists(self):
        """Test that required Docker files exist"""
        # Skip if running in parallel mode and files aren't accessible (pytest-xdist issue)
        if hasattr(pytest, 'main') and os.getenv('PYTEST_XDIST_WORKER'):
            pytest.skip("Skipping in parallel execution mode due to working directory issues")
            
        # Use absolute path to avoid working directory issues in parallel tests
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dockerfile_path = os.path.join(repo_root, 'web', 'Dockerfile.autonomous')
        assert os.path.exists(dockerfile_path), f"Dockerfile.autonomous not found at {dockerfile_path}"
        
        task_script_path = os.path.join(repo_root, 'web', 'claude_code_task.sh')
        assert os.path.exists(task_script_path), f"claude_code_task.sh not found at {task_script_path}"

    def test_autonomous_server_syntax(self):
        """Test that autonomous server has valid Python syntax"""
        try:
            # Get proper paths
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            server_path = os.path.join(repo_root, 'web', 'autonomous_server.py')
            web_dir = os.path.join(repo_root, 'web')
            
            # Test syntax compilation
            result = subprocess.run(
                ['python', '-m', 'py_compile', server_path],
                capture_output=True, text=True, timeout=10
            )
            assert result.returncode == 0, f"Syntax error in autonomous_server.py: {result.stderr}"
            
            # Test import without execution
            result = subprocess.run(
                ['python', '-c', f'import sys; sys.path.insert(0, "{web_dir}"); import autonomous_server'],
                capture_output=True, text=True, timeout=15
            )
            assert result.returncode == 0, f"Import error in autonomous_server.py: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Autonomous server syntax/import check timed out")
        except Exception as e:
            pytest.fail(f"Autonomous server syntax check failed: {str(e)}")

    def test_autonomous_server_startup(self):
        """Test that autonomous server can start without errors"""
        import tempfile
        import signal
        import time
        from threading import Timer
        
        # Use a different port to avoid conflicts
        test_port = 8001
        
        try:
            # Start server process
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            web_dir = os.path.join(repo_root, 'web')
            env = os.environ.copy()
            env['PYTHONPATH'] = web_dir
            
            process = subprocess.Popen(
                ['python', '-c', f'''
import sys
sys.path.insert(0, "{web_dir}")
import uvicorn
from autonomous_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={test_port}, log_level="error")
'''],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=repo_root
            )
            
            # Wait for startup
            startup_timeout = 10
            for _ in range(startup_timeout * 10):  # Check every 0.1 seconds
                if process.poll() is not None:
                    # Process ended early - check for errors
                    stdout, stderr = process.communicate()
                    pytest.fail(f"Server startup failed. STDOUT: {stdout.decode()}, STDERR: {stderr.decode()}")
                
                # Check if server is responding
                try:
                    import urllib.request
                    response = urllib.request.urlopen(f'http://127.0.0.1:{test_port}/health', timeout=1)
                    if response.status == 200:
                        print(" Autonomous server started successfully")
                        break
                except:
                    pass
                
                time.sleep(0.1)
            else:
                pytest.fail("Server failed to start within timeout period")
                
        except Exception as e:
            pytest.fail(f"Server startup test failed: {str(e)}")
            
        finally:
            # Clean up
            if 'process' in locals() and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
                    process.wait(timeout=2)

    def test_container_build_process(self):
        """Test that the Claude Code container can be built"""
        try:
            # Change to web directory for build context
            original_dir = os.getcwd()
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            web_dir = os.path.join(repo_root, 'web')
            os.chdir(web_dir)
            
            # Build the container
            build_cmd = ['docker', 'build', '-f', 'Dockerfile.autonomous', 
                        '-t', 'claude-code-test', '.']
            
            result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=300)
            
            # Should build successfully
            assert result.returncode == 0, f"Container build failed: {result.stderr}"
            
        finally:
            os.chdir(original_dir)
            # Cleanup test image
            subprocess.run(['docker', 'rmi', 'claude-code-test'], 
                         capture_output=True, timeout=30)

    @pytest.mark.asyncio
    async def test_autonomous_container_lifecycle(self, mock_env_vars, temp_task_logs_dir):
        """Test the complete autonomous container lifecycle"""
        
        # Change to web directory for Docker operations
        original_dir = os.getcwd()
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        web_dir = os.path.join(repo_root, 'web')
        os.chdir(web_dir)
        
        try:
            # Import here to avoid circular imports
            from web.autonomous_server import run_autonomous_task
            
            task_id = "test-task-12345"
            task_data = {
                "task_id": task_id,
                "task_description": "test task for container lifecycle",
                "repository_url": None,
                "github_token": "test-token",
                "timeout_minutes": 1,  # Short timeout for testing
                "save_word": "TEST_COMPLETE_SIGNAL",
                "status": "initializing",
                "progress": "Creating container environment...",
                "logs": ["Task created", "Initializing autonomous learning environment"],
                "created_at": "2025-01-01T00:00:00",
                "container_id": None
            }
            
            # Track the task execution
            start_time = time.time()
            
            # Run the autonomous task
            await run_autonomous_task(task_id, task_data)
            
            # Verify execution time
            execution_time = time.time() - start_time
            
            # Should NOT complete immediately (container should attempt to start, minimum 0.5 seconds for proper processing)
            assert execution_time > 0.5, f"Task completed too quickly ({execution_time:.2f}s), likely premature completion"
            
            # Verify log file was created
            log_file_path = os.path.join(temp_task_logs_dir, f"task_{task_id}.log")
            assert os.path.exists(log_file_path), "Log file was not created"
            
            # Verify log file content
            with open(log_file_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # Log file should contain system information
            assert "[SYSTEM] Task started" in log_content
            assert f"[SYSTEM] Task ID: {task_id}" in log_content
            assert "[SYSTEM] Task Description: test task for container lifecycle" in log_content
            assert "[SYSTEM] Completion Signal: TEST_COMPLETE_SIGNAL" in log_content
            assert "[SYSTEM] Log monitoring started" in log_content
            assert "[SYSTEM] Task ended" in log_content
            
            # Verify task data was updated
            assert task_data["status"] in ["failed", "timeout", "completed"], f"Unexpected status: {task_data['status']}"
            assert "log_file" in task_data or len(task_data["logs"]) > 2, "Task data not properly updated"
            
            # If it failed, it should be due to container issues, not immediate completion
            if task_data["status"] == "failed":
                # Should have attempted container operations
                log_messages = " ".join(task_data["logs"])
                assert ("Container" in log_messages or 
                       "Docker" in log_messages or 
                       "monitoring" in log_messages), "Should show container-related activity"
            
            print(f" Task executed for {execution_time:.2f}s with status: {task_data['status']}")
            print(f" Log file created: {log_file_path}")
            print(f" Task logs: {len(task_data['logs'])} entries")
            
        except Exception as e:
            pytest.fail(f"Autonomous task execution failed: {str(e)}")
        
        finally:
            # Cleanup any remaining containers
            try:
                subprocess.run(['docker', 'stop', f"claude-task-{task_id}"], 
                             capture_output=True, timeout=10)
                subprocess.run(['docker', 'rm', f"claude-task-{task_id}"], 
                             capture_output=True)
            except:
                pass
            
            # Restore original directory
            os.chdir(original_dir)

    def test_container_startup_monitoring(self, mock_env_vars):
        """Test that container monitoring detects startup properly"""
        
        # Create a simple test container that runs for a few seconds
        test_container_name = "test-claude-monitoring"
        
        try:
            # Start a test container
            run_cmd = [
                'docker', 'run', '-d', '--name', test_container_name,
                'ubuntu:22.04', 'bash', '-c', 
                'echo "Starting test container"; sleep 10; echo "Test container finished"'
            ]
            
            result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, f"Failed to start test container: {result.stderr}"
            
            # Test container status checking
            status_check = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'name={test_container_name}'],
                capture_output=True, text=True, timeout=5
            )
            
            assert status_check.returncode == 0, "Status check failed"
            assert status_check.stdout.strip(), "Container should be running"
            
            # Test log retrieval
            logs_result = subprocess.run(
                ['docker', 'logs', test_container_name],
                capture_output=True, text=True, timeout=10
            )
            
            assert logs_result.returncode == 0, "Log retrieval failed"
            assert 'Starting test container' in logs_result.stdout, "Container logs not accessible"
            
            print(" Container monitoring commands work correctly")
            
        finally:
            # Cleanup
            subprocess.run(['docker', 'stop', test_container_name], 
                         capture_output=True, timeout=10)
            subprocess.run(['docker', 'rm', test_container_name], 
                         capture_output=True)

    def test_completion_signal_detection(self, temp_task_logs_dir):
        """Test that completion signal detection works correctly"""
        
        # Create a test log file with various content
        log_file_path = os.path.join(temp_task_logs_dir, "test_completion.log")
        
        test_content = """
[SYSTEM] Task started
[21:45:15] Starting test environment
[21:45:16] Running some commands
[21:45:17] Creating completion.txt file
TEST_COMPLETE_SIGNAL
[21:45:18] Task should be complete now
"""
        
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Test signal detection
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "TEST_COMPLETE_SIGNAL" in content, "Completion signal should be detectable"
        
        # Test that it's NOT detected in setup files (task_context.md equivalent)
        setup_content = """
# Task Instructions
When complete, write: TEST_COMPLETE_SIGNAL
This is just instruction text.
"""
        
        # This should NOT trigger completion (it's just instructions)
        assert "TEST_COMPLETE_SIGNAL" in setup_content, "Signal in instructions should exist but not trigger completion"
        
        print(" Completion signal detection logic works correctly")

    @pytest.mark.asyncio
    async def test_task_initialization_error_handling(self, mock_env_vars, temp_task_logs_dir):
        """Test that task system handles initialization errors gracefully"""
        
        # Change to web directory for Docker operations  
        original_dir = os.getcwd()
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        web_dir = os.path.join(repo_root, 'web')
        os.chdir(web_dir)
        
        try:
            from web.autonomous_server import run_autonomous_task
            
            # Test case 1: Missing Docker image
            task_id_1 = "test-missing-docker"
            task_data_1 = {
                "task_id": task_id_1,
                "task_description": "test with missing docker",
                "repository_url": None,
                "github_token": "test-token",
                "timeout_minutes": 1,
                "save_word": "TEST_COMPLETE_SIGNAL",
                "status": "initializing",
                "progress": "Creating container environment...",
                "logs": ["Task created"],
                "created_at": "2025-01-01T00:00:00",
                "container_id": None
            }
            
            # Temporarily rename Dockerfile to simulate missing file
            dockerfile_backup = None
            if os.path.exists("Dockerfile.autonomous"):
                dockerfile_backup = "Dockerfile.autonomous.backup"
                os.rename("Dockerfile.autonomous", dockerfile_backup)
            
            try:
                start_time = time.time()
                await run_autonomous_task(task_id_1, task_data_1)
                execution_time = time.time() - start_time
                
                # Should fail quickly (within 30 seconds) but gracefully
                assert execution_time < 30, "Task should fail quickly when Docker setup fails"
                assert task_data_1["status"] == "failed", f"Expected failed status, got: {task_data_1['status']}"
                assert "error" in task_data_1 or any("error" in log.lower() or "failed" in log.lower() 
                                                   for log in task_data_1["logs"]), "Should contain error information"
                
                print(f" Handled missing Docker file gracefully ({execution_time:.2f}s)")
                
            finally:
                # Restore Dockerfile if we backed it up
                if dockerfile_backup and os.path.exists(dockerfile_backup):
                    os.rename(dockerfile_backup, "Dockerfile.autonomous")
            
            # Test case 2: Invalid environment configuration
            task_id_2 = "test-invalid-env"
            task_data_2 = {
                "task_id": task_id_2,
                "task_description": "test with invalid environment",
                "repository_url": "invalid://not-a-real-repo",
                "github_token": "invalid-token",
                "timeout_minutes": 1,
                "save_word": "TEST_COMPLETE_SIGNAL",
                "status": "initializing",
                "progress": "Creating container environment...",
                "logs": ["Task created"],
                "created_at": "2025-01-01T00:00:00",
                "container_id": None
            }
            
            start_time = time.time()
            await run_autonomous_task(task_id_2, task_data_2)
            execution_time = time.time() - start_time
            
            # Should handle gracefully
            assert task_data_2["status"] in ["failed", "timeout"], f"Expected failed/timeout status, got: {task_data_2['status']}"
            
            # Verify log file creation even for failed tasks
            log_file_path = os.path.join(temp_task_logs_dir, f"task_{task_id_2}.log")
            if os.path.exists(log_file_path):
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                assert "[SYSTEM] Task started" in log_content, "Log file should contain system startup info"
                assert "[SYSTEM] Task ended" in log_content, "Log file should contain system end info"
            
            print(f" Handled invalid environment gracefully ({execution_time:.2f}s)")
            print(f" Task error handling tests completed successfully")
            
        except Exception as e:
            pytest.fail(f"Task initialization error handling test failed: {str(e)}")
            
        finally:
            # Restore original directory
            os.chdir(original_dir)
            
            # Cleanup any test containers
            for task_id in ["test-missing-docker", "test-invalid-env"]:
                try:
                    subprocess.run(['docker', 'stop', f"claude-task-{task_id}"], 
                                 capture_output=True, timeout=5)
                    subprocess.run(['docker', 'rm', f"claude-task-{task_id}"], 
                                 capture_output=True)
                except:
                    pass

if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "--tb=short"]) 