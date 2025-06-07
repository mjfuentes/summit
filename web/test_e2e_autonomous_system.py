#!/usr/bin/env python3
"""
End-to-End Test for Summit Autonomous Claude Code System

This is a standalone E2E test that differs from the existing integration tests:
- tests/test_autonomous_integration.py: Unit/integration tests with pytest, mocks, component testing
- web/test_e2e_autonomous_system.py: End-to-end workflow test with real HTTP API calls

This script tests the complete user workflow:
1. Deploy the autonomous server
2. Setup a test git branch for safe testing
3. Make HTTP API calls to create tasks that require git operations
4. Monitor task progress and completion
5. Validate git commits and pushes were made correctly
6. Clean up test branch and artifacts
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import requests


class AutonomousSystemTest:
    def __init__(self):
        self.server_process = None
        self.server_url = "http://localhost:8000"
        self.task_id = None
        self.test_branch = "test/autonomous-claude-e2e"
        self.original_branch = None
        self.debug_mode = False  # Add debug mode for detailed output

    def set_debug_mode(self, enabled=True):
        """Enable/disable debug mode for verbose output"""
        self.debug_mode = enabled
        if enabled:
            self.log("Debug mode enabled - will show detailed output")

    def debug_log(self, message):
        """Log message only in debug mode"""
        if self.debug_mode:
            self.log(f"[DEBUG] {message}")

    def get_container_status(self, container_name):
        """Get current container status and basic info"""
        try:
            # Check if container exists and is running
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-f",
                    f"name={container_name}",
                    "--format",
                    "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:  # Skip header
                    return lines[1]  # Return status line
            return "Container not running"
        except:
            return "Status check failed"

    def stream_container_logs(self, container_name, duration_seconds=30):
        """Stream container logs for a short period to see what's happening"""
        self.log(f"Streaming container logs for {duration_seconds} seconds...")
        try:
            # Get recent logs first
            result = subprocess.run(
                ["docker", "logs", "--tail", "10", container_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                self.log("Recent container output:")
                for line in result.stdout.strip().split("\n")[-5:]:
                    if line.strip():
                        self.log(f"  | {line}")

            # Stream new logs
            process = subprocess.Popen(
                ["docker", "logs", "-f", "--since", "30s", container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                if process.poll() is not None:
                    break

                # Read available output
                try:
                    import select

                    if select.select(
                        [process.stdout], [], [], 1
                    ):  # 1 second timeout
                        line = process.stdout.readline()
                        if line:
                            self.log(f"  | {line.strip()}")
                except:
                    # Fallback for systems without select
                    time.sleep(1)

            process.terminate()

        except Exception as e:
            self.log(f"Error streaming logs: {e}")

    def list_claude_containers(self):
        """List all Claude-related containers"""
        self.log("Checking for Claude containers...")
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=claude"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                self.log("Found Claude containers:")
                for line in lines:
                    self.log(f"  {line}")
            else:
                self.log("No Claude containers found")

            # Also check for any containers created recently
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "since=2m"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    self.log("Recent containers (last 2 minutes):")
                    for line in lines:
                        self.log(f"  {line}")

        except Exception as e:
            self.log(f"Error listing containers: {e}")

    def check_docker_images(self):
        """Check if Claude Code Docker image exists"""
        self.log("Checking Docker images...")
        try:
            result = subprocess.run(
                ["docker", "images", "--filter", "reference=claude-code-task"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:  # Header + at least one image
                    self.log("Claude Code Docker image found:")
                    for line in lines:
                        self.log(f"  {line}")
                else:
                    self.log(
                        "Claude Code Docker image NOT found - container build may be in progress"
                    )

            # Check if any Docker build processes are running
            result = subprocess.run(
                ["docker", "ps"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "build" in result.stdout.lower():
                self.log("Docker build process may be running")

        except Exception as e:
            self.log(f"Error checking Docker images: {e}")

    def check_claude_in_container(self, container_name):
        """Check if Claude Code is properly installed and accessible in container"""
        self.log(
            f"Checking Claude Code installation in container: {container_name}"
        )

        # First check if container is actually running
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if container_name not in result.stdout:
                self.log(f"  Container {container_name} is not running!")
                self.list_claude_containers()
                return
        except Exception as e:
            self.log(f"  Error checking container status: {e}")
            return

        try:
            # Check if claude command exists
            result = subprocess.run(
                ["docker", "exec", container_name, "which", "claude"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.log("  Claude Code CLI found in container")

                # Check version
                result = subprocess.run(
                    ["docker", "exec", container_name, "claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self.log(f"  Claude version: {result.stdout.strip()}")
                else:
                    self.log(
                        "  Warning: Claude command found but version check failed"
                    )

                # Check if API key is available
                result = subprocess.run(
                    ["docker", "exec", container_name, "env"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if (
                    result.returncode == 0
                    and "ANTHROPIC_API_KEY" in result.stdout
                ):
                    self.log("  API key environment variable found")
                else:
                    self.log(
                        "  Warning: ANTHROPIC_API_KEY not found in environment"
                    )

            else:
                self.log("  Error: Claude Code CLI not found in container")

        except subprocess.TimeoutExpired:
            self.log("  Timeout checking Claude Code in container")
        except Exception as e:
            self.log(f"  Error checking Claude Code: {e}")

    def log(self, message):
        """Print timestamped log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def cleanup(self):
        """Clean up server process, Docker containers, and test branch"""
        self.log("Cleaning up...")

        if self.server_process:
            self.log("Stopping autonomous server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

        # Clean up any remaining Docker containers
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", "name=claude-task"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                container_ids = result.stdout.strip().split("\n")
                for container_id in container_ids:
                    if container_id:
                        self.log(f"Stopping Docker container: {container_id}")
                        subprocess.run(
                            ["docker", "stop", container_id],
                            capture_output=True,
                        )
                        subprocess.run(
                            ["docker", "rm", container_id], capture_output=True
                        )
        except Exception as e:
            self.log(f"Docker cleanup error: {e}")

        # Clean up test branch
        self.cleanup_test_branch()

    def setup_test_branch(self):
        """Create and switch to test branch for git operations"""
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.original_branch = result.stdout.strip()
                self.log(f"Current branch: {self.original_branch}")

            # Delete test branch if it exists
            subprocess.run(
                ["git", "branch", "-D", self.test_branch],
                capture_output=True,
                timeout=5,
            )

            # Create and switch to test branch
            result = subprocess.run(
                ["git", "checkout", "-b", self.test_branch],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.log(
                    f" Created and switched to test branch: {self.test_branch}"
                )
                return True
            else:
                self.log(f" Failed to create test branch: {result.stderr}")
                return False

        except Exception as e:
            self.log(f" Error setting up test branch: {e}")
            return False

    def validate_git_operations(self):
        """Validate that git commits and pushes were made"""
        try:
            # Check if we're on the test branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if (
                result.returncode != 0
                or result.stdout.strip() != self.test_branch
            ):
                self.log(
                    f" Not on test branch. Current: {result.stdout.strip()}"
                )
                return False

            # Check for recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                recent_commits = result.stdout.strip()
                self.log(f"Recent commits on {self.test_branch}:")
                for commit in recent_commits.split("\n")[:3]:
                    self.log(f"  {commit}")

                # Check if test file was created in workspace (container creates it, may not be local)
                # We'll check git history instead since the file is in the container

                # Check for commits with the specific message we requested
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        "--grep",
                        "Add autonomous Claude test script",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.log(" Found git commit with expected message")

                    # Check for commits that added the test file
                    result = subprocess.run(
                        [
                            "git",
                            "log",
                            "--oneline",
                            "--",
                            "test_autonomous_claude.py",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        self.log(" Found git commits that added test file")
                        return True
                    else:
                        self.log(" No git commits found for test file")
                        return False
                else:
                    self.log(" No git commit found with expected message")
                    return False
            else:
                self.log(" Failed to check git log")
                return False

        except Exception as e:
            self.log(f" Error validating git operations: {e}")
            return False

    def cleanup_test_branch(self):
        """Clean up test branch and return to original branch"""
        try:
            if self.original_branch:
                # Switch back to original branch
                result = subprocess.run(
                    ["git", "checkout", self.original_branch],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self.log(f" Switched back to {self.original_branch}")
                else:
                    self.log(
                        f" Failed to switch back to {self.original_branch}: {result.stderr}"
                    )

                # Delete test branch
                result = subprocess.run(
                    ["git", "branch", "-D", self.test_branch],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    self.log(f" Deleted test branch: {self.test_branch}")
                else:
                    self.log(f" Could not delete test branch: {result.stderr}")

                # Clean up test file if it exists (it may only exist in git history)
                if os.path.exists("test_autonomous_claude.py"):
                    os.remove("test_autonomous_claude.py")
                    self.log(" Cleaned up local test file")
                else:
                    self.log(
                        " Test file cleanup complete (file was only in container)"
                    )

        except Exception as e:
            self.log(f" Error during test branch cleanup: {e}")

    def start_server(self):
        """Start the autonomous server"""
        self.log("Starting autonomous server...")

        # Change to web directory if not already there
        if not os.path.basename(os.getcwd()) == "web":
            os.chdir("web")

        # Start server in background
        self.server_process = subprocess.Popen(
            ["python3", "autonomous_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for server to be ready
        self.log("Waiting for server to be ready...")
        max_wait = 30  # 30 seconds timeout
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.server_url}/health", timeout=2)
                if response.status_code == 200:
                    self.log(" Server is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)

        self.log(" Server failed to start within timeout")
        return False

    def create_task(self):
        """Create a test task via HTTP API"""
        self.log("Creating test task...")

        # Get current repository URL for testing git workflow
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            repo_url = (
                result.stdout.strip() if result.returncode == 0 else None
            )
        except:
            repo_url = None

        # Start with a simpler task for initial testing
        if self.debug_mode:
            task_description = "Create a simple Python script called 'test_autonomous_claude.py' that prints 'Hello from autonomous Claude Code!' and write the completion signal to completion.txt"
            save_word = "SIMPLE_TEST_COMPLETE"
        else:
            task_description = f"Create a simple Python script called 'test_autonomous_claude.py' that prints 'Hello from autonomous Claude Code!' then MUST: 1) git add the file, 2) commit with message 'Add autonomous Claude test script', 3) push to branch '{self.test_branch}'. The git workflow is MANDATORY for test completion."
            save_word = "AUTONOMOUS_GIT_TEST_COMPLETE"

        task_data = {
            "task_description": task_description,
            "repository_url": (
                repo_url if not self.debug_mode else None
            ),  # Use repo only for git testing
            "github_token": None,
            "timeout_minutes": 12,  # More time for operations
            "save_word": save_word,
        }

        try:
            response = requests.post(
                f"{self.server_url}/api/tasks", json=task_data, timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.task_id = result["task_id"]
                    self.log(f" Task created successfully! ID: {self.task_id}")
                    return True
                else:
                    self.log(f" Task creation failed: {result.get('message')}")
                    return False
            else:
                self.log(f" HTTP error: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.log(f" Request error: {e}")
            return False

    def monitor_task(self, max_wait_minutes=15):
        """Monitor task progress and check results with improved error handling"""
        if not self.task_id:
            self.log(" No task ID to monitor")
            return False

        self.log(
            f"Monitoring task {self.task_id} (timeout: {max_wait_minutes} minutes)..."
        )

        max_wait = max_wait_minutes * 60  # Convert to seconds
        start_time = time.time()
        last_status = None
        consecutive_errors = 0
        last_log_count = 0
        container_name = None
        logs_streamed = False

        while time.time() - start_time < max_wait:
            elapsed_time = time.time() - start_time

            try:
                # Use longer timeout for requests as container operations can be slow
                response = requests.get(
                    f"{self.server_url}/api/tasks/{self.task_id}", timeout=15
                )
                consecutive_errors = 0  # Reset error counter on success

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        task = result["task"]
                        status = task.get("status")
                        progress = task.get("progress", "")
                        logs = task.get("logs", [])

                        # Extract container name for monitoring
                        if not container_name and "container_id" in task:
                            container_name = task["container_id"]
                            self.debug_log(f"Container name: {container_name}")

                        # Show web terminal URL when available
                        if (
                            "claude_code_url" in task
                            and task["claude_code_url"]
                        ):
                            web_url = task["claude_code_url"]
                            if status == "running" and elapsed_time > 30:
                                self.log(f"Web terminal available: {web_url}")
                                self.log(
                                    "  You can open this URL to see Claude Code in action!"
                                )

                        # Log status changes
                        if status != last_status:
                            self.log(
                                f"Task status: {status} - {progress} ({elapsed_time:.1f}s elapsed)"
                            )
                            if container_name and status == "running":
                                container_status = self.get_container_status(
                                    container_name
                                )
                                self.log(
                                    f"Container status: {container_status}"
                                )
                            last_status = status

                        # Show new log entries (always show in debug mode, key ones otherwise)
                        if len(logs) > last_log_count:
                            new_logs = logs[last_log_count:]
                            for log_entry in new_logs:
                                if self.debug_mode:
                                    self.debug_log(f"Task log: {log_entry}")
                                elif any(
                                    keyword in log_entry.lower()
                                    for keyword in [
                                        "claude",
                                        "error",
                                        "failed",
                                        "completed",
                                        "terminal",
                                    ]
                                ):
                                    self.log(f"  > {log_entry}")
                            last_log_count = len(logs)

                        # Show periodic progress updates and stream logs if taking too long
                        if int(elapsed_time) % 60 == 0 and elapsed_time > 60:
                            self.log(
                                f"Still monitoring... {elapsed_time:.0f}s elapsed, status: {status}"
                            )

                            # Check container health if we haven't done it yet and container is running
                            if (
                                container_name
                                and status == "running"
                                and not logs_streamed
                                and elapsed_time > 90
                            ):
                                self.log(
                                    "Task taking longer than expected, checking container health..."
                                )
                                self.check_claude_in_container(container_name)
                                self.stream_container_logs(
                                    container_name, duration_seconds=20
                                )
                                logs_streamed = True

                        # For debug mode, show more frequent updates
                        elif (
                            self.debug_mode
                            and int(elapsed_time) % 30 == 0
                            and elapsed_time > 30
                        ):
                            self.log(
                                f"Still monitoring... {elapsed_time:.0f}s elapsed, status: {status}"
                            )
                            if container_name:
                                container_status = self.get_container_status(
                                    container_name
                                )
                                self.debug_log(
                                    f"Container status: {container_status}"
                                )

                        # Check for completion
                        if status == "completed":
                            self.log(" Task completed successfully!")
                            self.log("Final logs:")
                            for log_entry in logs[-3:]:
                                self.log(f"  {log_entry}")
                            return True

                        elif status == "failed":
                            self.log(" Task failed!")
                            self.log("Error logs:")
                            for log_entry in logs[-5:]:
                                self.log(f"  {log_entry}")
                            return False

                        elif status == "timeout":
                            self.log(" Task timed out!")
                            return False

                else:
                    self.log(
                        f" Error checking task status: {response.status_code}"
                    )
                    consecutive_errors += 1

            except requests.exceptions.Timeout:
                consecutive_errors += 1
                self.log(
                    f" Request timeout ({consecutive_errors}/3) - container may be building or busy..."
                )

            except requests.exceptions.RequestException as e:
                consecutive_errors += 1
                self.log(f" Connection error ({consecutive_errors}/3): {e}")

            # If too many consecutive errors, bail out
            if consecutive_errors >= 3:
                self.log(" Too many consecutive errors, stopping monitoring")
                return False

            time.sleep(10)  # Check every 10 seconds to reduce load

        self.log(
            f" Monitoring timeout reached after {max_wait_minutes} minutes"
        )
        return False

    def check_docker_availability(self):
        """Check if Docker is available"""
        self.log("Checking Docker availability...")

        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.log(f" Docker is available: {result.stdout.strip()}")
            else:
                self.log(" Docker is not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log(" Docker command not found")
            return False

        # Also check git availability for full test
        self.log("Checking Git availability...")
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.log(f" Git is available: {result.stdout.strip()}")
            else:
                self.log(" Git is not working properly")
                return False

            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "status"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.log(" Current directory is a git repository")
                return True
            else:
                self.log(" Current directory is not a git repository")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log(" Git command not found")
            return False

    def check_docker_only(self):
        """Check if Docker is available (for debug mode)"""
        self.log("Checking Docker availability...")

        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.log(f" Docker is available: {result.stdout.strip()}")
                return True
            else:
                self.log(" Docker is not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log(" Docker command not found")
            return False

    def run_full_test(self):
        """Run the complete test suite with git workflow validation"""
        self.log(" Starting Summit Autonomous Claude Code System Test")
        self.log("=" * 60)

        try:
            # Step 1: Check Docker
            if not self.check_docker_availability():
                self.log(" Test failed: Docker not available")
                return False

            # Step 2: Setup test branch for git operations
            if not self.setup_test_branch():
                self.log(" Test failed: Could not setup test branch")
                return False

            # Step 3: Start server
            if not self.start_server():
                self.log(" Test failed: Could not start server")
                return False

            # Step 4: Create task
            if not self.create_task():
                self.log(" Test failed: Could not create task")
                return False

            # Step 5: Monitor task
            if not self.monitor_task():
                self.log(" Test failed: Task did not complete successfully")
                return False

            # Step 6: Validate git operations
            if not self.validate_git_operations():
                self.log(" Test failed: Git workflow validation failed")
                return False

            # Success!
            self.log(
                " All tests passed! Autonomous Claude Code system with git workflow is working!"
            )
            return True

        except KeyboardInterrupt:
            self.log(" Test interrupted by user")
            return False

        except Exception as e:
            self.log(f" Unexpected error: {e}")
            return False

        finally:
            self.cleanup()

    def run_simple_debug_test(self):
        """Run a simplified test with Docker but without git complexity"""
        self.log(" Starting Simple Debug Test (Docker, no git)")
        self.log("=" * 50)

        try:
            # Step 1: Check Docker only (not git for debug test)
            if not self.check_docker_only():
                self.log(" Test failed: Docker not available")
                return False

            # Step 2: Start server
            if not self.start_server():
                self.log(" Test failed: Could not start server")
                return False

            # Step 3: Create simple task
            if not self.create_task():  # Will use simple task in debug mode
                self.log(" Test failed: Could not create task")
                return False

            # Step 4: Check container activity immediately
            self.log("Checking container creation immediately...")
            time.sleep(2)

            # Check Docker images first
            self.check_docker_images()

            # First check what containers exist
            self.list_claude_containers()

            # Get task status to see what's happening
            try:
                response = requests.get(
                    f"{self.server_url}/api/tasks/{self.task_id}", timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        task = result["task"]
                        self.log(f"Initial task status: {task.get('status')}")
                        self.log(f"Initial task logs: {task.get('logs', [])}")

                        container_name = task.get("container_id")
                        if container_name:
                            self.log(f"Container ID found: {container_name}")
                            time.sleep(3)  # Give container a moment to start
                            self.check_claude_in_container(container_name)
                            self.stream_container_logs(
                                container_name, duration_seconds=15
                            )
                        else:
                            self.log(
                                "No container ID found yet - container may still be starting"
                            )
                            # Wait a bit more and check again
                            time.sleep(10)
                            response = requests.get(
                                f"{self.server_url}/api/tasks/{self.task_id}",
                                timeout=10,
                            )
                            if response.status_code == 200:
                                updated_task = response.json().get("task", {})
                                self.log(
                                    f"Updated task status: {updated_task.get('status')}"
                                )
                                self.log(
                                    f"Updated task logs: {updated_task.get('logs', [])}"
                                )

                                updated_container = updated_task.get(
                                    "container_id"
                                )
                                if updated_container:
                                    self.log(
                                        f"Container now available: {updated_container}"
                                    )
                                    self.check_claude_in_container(
                                        updated_container
                                    )
                                else:
                                    self.log(
                                        "Still no container - checking what's happening..."
                                    )
                                    self.list_claude_containers()

            except Exception as e:
                self.log(f"Error getting immediate status: {e}")

            # Step 5: Monitor task with debug output
            if not self.monitor_task(max_wait_minutes=8):
                self.log(" Test failed: Task did not complete successfully")
                return False

            # Success!
            self.log(
                " Simple debug test passed! Docker and Claude Code are working!"
            )
            return True

        except KeyboardInterrupt:
            self.log(" Test interrupted by user")
            return False

        except Exception as e:
            self.log(f" Unexpected error: {e}")
            return False

        finally:
            self.cleanup()

    def run_quick_api_test(self):
        """Run a quick test of just the API without Docker"""
        self.log(" Running Quick API Test (No Docker)")
        self.log("=" * 50)

        try:
            # Start server
            if not self.start_server():
                return False

            # Test health endpoint
            self.log("Testing health endpoint...")
            response = requests.get(f"{self.server_url}/health")
            if response.status_code == 200:
                self.log(" Health endpoint working")
            else:
                self.log(" Health endpoint failed")
                return False

            # Test task creation endpoint (will fail at Docker step, but API should work)
            self.log("Testing task creation API...")
            task_data = {
                "task_description": "Test task",
                "timeout_minutes": 1,
                "save_word": "TEST_COMPLETE",
            }

            response = requests.post(
                f"{self.server_url}/api/tasks", json=task_data
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.log(" Task creation API working")
                    task_id = result["task_id"]

                    # Wait a moment then check task status
                    time.sleep(2)
                    response = requests.get(
                        f"{self.server_url}/api/tasks/{task_id}"
                    )
                    if response.status_code == 200:
                        self.log(" Task status API working")
                        return True

            self.log(" API test failed")
            return False

        except Exception as e:
            self.log(f" Quick test error: {e}")
            return False

        finally:
            self.cleanup()


def main():
    """Main test function"""
    test = AutonomousSystemTest()

    # Setup signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n")
        test.log("Received interrupt signal, cleaning up...")
        test.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Check command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--quick":
            success = test.run_quick_api_test()
        elif arg == "--debug":
            test.set_debug_mode(True)
            success = test.run_simple_debug_test()
        elif arg == "--help":
            print("\nUsage: python3 test_e2e_autonomous_system.py [option]")
            print("\nOptions:")
            print("  --quick    Quick API test (no Docker)")
            print("  --debug    Simple debug test (Docker, no git)")
            print("  --help     Show this help")
            print("  (no args)  Full test with git workflow")
            sys.exit(0)
        else:
            success = test.run_full_test()
    else:
        success = test.run_full_test()

    if success:
        print("\n TEST PASSED! The autonomous system is working correctly.")
        sys.exit(0)
    else:
        print("\n TEST FAILED! Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
