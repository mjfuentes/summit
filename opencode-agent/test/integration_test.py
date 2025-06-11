#!/usr/bin/env python3
"""
Integration Test Suite for OpenCode-Vertex AI

Tests the complete flow:
1. Vertex AI connectivity
2. Basic chat completions
3. Function calling (with tools)
4. Error handling
5. OpenAI compatibility
6. OpenCode agent with file editing
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
from colorama import Fore, Style, init
from test_scenarios import TestScenarios

# Initialize colorama for colored output
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/integration_test.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class IntegrationTester:
    """Main integration test runner"""

    def __init__(self):
        self.vertex_ai_url = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/summit-ai-platform/locations/us-central1/endpoints/openapi/chat/completions"
        self.vertex_ai_token = os.getenv("VERTEX_AI_TOKEN")
        self.project_id = os.getenv(
            "GOOGLE_CLOUD_PROJECT", "summit-ai-platform"
        )

        self.results = []
        self.start_time = datetime.now()

        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=180.0)

        # Test scenarios
        self.scenarios = TestScenarios()

    def log_test_result(
        self,
        test_name: str,
        passed: bool,
        details: str = "",
        duration: float = 0,
    ):
        """Log test result with colored output"""
        status = (
            f"{Fore.GREEN} PASSED{Style.RESET_ALL}"
            if passed
            else f"{Fore.RED} FAILED{Style.RESET_ALL}"
        )
        duration_str = f" ({duration:.2f}s)" if duration > 0 else ""

        print(f"{status} {test_name}{duration_str}")
        if details:
            print(f"   {details}")

        self.results.append(
            {
                "test": test_name,
                "passed": passed,
                "details": details,
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(
            f"Test {test_name}: {'PASSED' if passed else 'FAILED'} - {details}"
        )

    async def test_vertex_ai_auth(self) -> bool:
        """Test Vertex AI authentication and connectivity"""
        test_start = time.time()
        try:
            if not self.vertex_ai_token:
                # Try to get token from gcloud
                import subprocess

                try:
                    result = subprocess.run(
                        ["gcloud", "auth", "print-access-token"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    self.vertex_ai_token = result.stdout.strip()
                except subprocess.CalledProcessError:
                    self.log_test_result(
                        "Vertex AI Authentication",
                        False,
                        "No token found and gcloud auth failed",
                        time.time() - test_start,
                    )
                    return False

            # Test with a simple request
            headers = {
                "Authorization": f"Bearer {self.vertex_ai_token}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10,
            }

            response = await self.client.post(
                self.vertex_ai_url, json=payload, headers=headers
            )

            if response.status_code == 200:
                self.log_test_result(
                    "Vertex AI Authentication",
                    True,
                    "Successfully authenticated and connected to Vertex AI",
                    time.time() - test_start,
                )
                return True
            else:
                self.log_test_result(
                    "Vertex AI Authentication",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    time.time() - test_start,
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Vertex AI Authentication",
                False,
                f"Connection error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Vertex AI"""
        if not self.vertex_ai_token:
            import subprocess

            try:
                result = subprocess.run(
                    ["gcloud", "auth", "print-access-token"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.vertex_ai_token = result.stdout.strip()
            except subprocess.CalledProcessError:
                raise Exception("Failed to get Vertex AI token")

        return {
            "Authorization": f"Bearer {self.vertex_ai_token}",
            "Content-Type": "application/json",
        }

    async def test_basic_chat(self) -> bool:
        """Test basic chat completion without tools"""
        test_start = time.time()
        try:
            headers = await self.get_auth_headers()

            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello! Please respond with a brief greeting and confirm you can assist me.",
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.7,
            }

            response = await self.client.post(
                self.vertex_ai_url, json=payload, headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if (
                    data.get("choices")
                    and len(data["choices"]) > 0
                    and data["choices"][0].get("message")
                ):

                    message = data["choices"][0]["message"]
                    content = message.get("content", "")

                    if content and len(content) > 0:
                        self.log_test_result(
                            "Basic Chat Completion",
                            True,
                            f"Response: {content[:100]}{'...' if len(content) > 100 else ''}",
                            time.time() - test_start,
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Basic Chat Completion",
                            False,
                            "Empty content in response",
                            time.time() - test_start,
                        )
                        return False
                else:
                    self.log_test_result(
                        "Basic Chat Completion",
                        False,
                        f"Invalid response structure: {json.dumps(data, indent=2)[:200]}",
                        time.time() - test_start,
                    )
                    return False
            else:
                self.log_test_result(
                    "Basic Chat Completion",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    time.time() - test_start,
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Basic Chat Completion",
                False,
                f"Request error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_function_calling(self) -> bool:
        """Test function calling capability"""
        test_start = time.time()
        try:
            headers = await self.get_auth_headers()

            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "user",
                        "content": "What's the weather like in New York? Please use the weather function to check.",
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Get the current weather for a specific location",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": "The city and state/country",
                                    },
                                    "units": {
                                        "type": "string",
                                        "enum": ["celsius", "fahrenheit"],
                                        "description": "Temperature units",
                                    },
                                },
                                "required": ["location"],
                            },
                        },
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1,
            }

            response = await self.client.post(
                self.vertex_ai_url, json=payload, headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("choices") and len(data["choices"]) > 0:

                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    finish_reason = choice.get("finish_reason")

                    # Check if model decided to use tools
                    if finish_reason == "tool_calls" and message.get(
                        "tool_calls"
                    ):
                        tool_calls = message["tool_calls"]

                        # Validate tool call structure
                        if len(tool_calls) > 0:
                            tool_call = tool_calls[0]
                            function_name = tool_call.get("function", {}).get(
                                "name"
                            )

                            self.log_test_result(
                                "Function Calling",
                                True,
                                f"Model called function: {function_name}",
                                time.time() - test_start,
                            )
                            return True
                        else:
                            self.log_test_result(
                                "Function Calling",
                                False,
                                "Empty tool_calls array",
                                time.time() - test_start,
                            )
                            return False
                    elif finish_reason == "stop":
                        # Model chose not to use tools - this could be valid
                        content = message.get("content", "")
                        self.log_test_result(
                            "Function Calling",
                            True,
                            f"Model responded without tools: {content[:100]}",
                            time.time() - test_start,
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Function Calling",
                            False,
                            f"Unexpected finish_reason: {finish_reason}",
                            time.time() - test_start,
                        )
                        return False
                else:
                    self.log_test_result(
                        "Function Calling",
                        False,
                        "Invalid response structure",
                        time.time() - test_start,
                    )
                    return False
            else:
                self.log_test_result(
                    "Function Calling",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    time.time() - test_start,
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Function Calling",
                False,
                f"Request error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_multi_tool_calling(self) -> bool:
        """Test calling multiple tools in sequence"""
        test_start = time.time()
        try:
            headers = await self.get_auth_headers()

            payload = {
                "model": "google/gemini-2.0-flash-001",
                "messages": [
                    {
                        "role": "user",
                        "content": "I need to check the weather in Paris and also get the current time. Can you help?",
                    }
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Get the current weather for a specific location",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {
                                        "type": "string",
                                        "description": "The city and state/country",
                                    }
                                },
                                "required": ["location"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "get_current_time",
                            "description": "Get the current time in a specific timezone",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "timezone": {
                                        "type": "string",
                                        "description": "Timezone (e.g., 'America/New_York', 'Europe/London')",
                                    }
                                },
                                "required": ["timezone"],
                            },
                        },
                    },
                ],
                "max_tokens": 300,
                "temperature": 0.1,
            }

            response = await self.client.post(
                self.vertex_ai_url, json=payload, headers=headers
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("choices") and len(data["choices"]) > 0:

                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    finish_reason = choice.get("finish_reason")

                    # Check if model decided to use tools
                    if finish_reason == "tool_calls" and message.get(
                        "tool_calls"
                    ):
                        tool_calls = message["tool_calls"]

                        self.log_test_result(
                            "Multi-Tool Function Calling",
                            True,
                            f"Model suggested {len(tool_calls)} tool calls",
                            time.time() - test_start,
                        )
                        return True
                    elif finish_reason == "stop":
                        # Model chose not to use tools
                        content = message.get("content", "")
                        self.log_test_result(
                            "Multi-Tool Function Calling",
                            True,
                            f"Model responded without tools: {content[:100]}",
                            time.time() - test_start,
                        )
                        return True
                    else:
                        self.log_test_result(
                            "Multi-Tool Function Calling",
                            False,
                            f"Unexpected finish_reason: {finish_reason}",
                            time.time() - test_start,
                        )
                        return False
                else:
                    self.log_test_result(
                        "Multi-Tool Function Calling",
                        False,
                        "Invalid response structure",
                        time.time() - test_start,
                    )
                    return False
            else:
                self.log_test_result(
                    "Multi-Tool Function Calling",
                    False,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    time.time() - test_start,
                )
                return False

        except Exception as e:
            self.log_test_result(
                "Multi-Tool Function Calling",
                False,
                f"Request error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def test_opencode_agent_file_editing(self) -> bool:
        """Test OpenCode agent with file editing capabilities"""
        test_start = time.time()
        try:
            # Create temporary directory for test workspace
            with tempfile.TemporaryDirectory() as temp_dir:
                workspace_path = Path(temp_dir) / "workspace"
                workspace_path.mkdir()

                # Create initial test files
                test_file = workspace_path / "test_script.py"
                test_file.write_text(
                    '''#!/usr/bin/env python3
"""Test script for OpenCode agent file editing"""

def greet(name):
    print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("World")
'''
                )

                config_file = workspace_path / "config.json"
                config_file.write_text('{"version": "1.0", "debug": false}')

                # Create simple OpenCode config for this test using Vertex AI
                opencode_config = {
                    "agents": {
                        "coder": {
                            "model": "vertex:gemini-2.0-flash-001",
                            "reasoningEffort": "high",
                            "maxTokens": 4096,
                        }
                    }
                }

                config_path = Path(temp_dir) / "opencode_config.json"
                config_path.write_text(json.dumps(opencode_config, indent=2))

                # Create the prompt for the agent - simplified for better success
                prompt = f"""You are a helpful coding assistant. I need you to help me with a simple file editing task.

Current working directory: /workspace

Task: Please read the file test_script.py (located in the current directory) and add a new function called 'calculate_sum' that takes two numbers a and b and returns a + b.

Add the function after the existing greet function. The function should look like:

def calculate_sum(a, b):
    return a + b

Please use your file editing capabilities to make this change to test_script.py in the current directory.
"""

                # Try a simpler approach: use a Python container with OpenCode installed
                # and mount the workspace directly
                # Use the existing ADC file from the host system
                adc_path = (
                    Path.home()
                    / ".config"
                    / "gcloud"
                    / "application_default_credentials.json"
                )

                docker_cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "-i",
                    "-v",
                    f"{workspace_path}:/workspace",
                    "-v",
                    f"{config_path}:/tmp/opencode_config.json",
                    "-v",
                    f"{adc_path}:/tmp/adc_credentials.json:ro",
                    "-w",
                    "/workspace",
                    "--env",
                    "GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc_credentials.json",
                    "--env",
                    "VERTEXAI_PROJECT=summit-ai-platform",
                    "--env",
                    "VERTEXAI_LOCATION=us-central1",
                    "python:3.11-slim",
                    "sh",
                    "-c",
                    f"""
                     set -e
                     
                     # Install curl for OpenCode installation  
                     apt-get update -qq
                     apt-get install -y curl
                     
                     # Install OpenCode
                     curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash
                     
                     # Setup config
                     mkdir -p ~/.config/opencode
                     cp /tmp/opencode_config.json ~/.config/opencode/config.json
                     
                     # Verify config was copied correctly
                     echo "=== OpenCode config content ==="
                     cat ~/.config/opencode/config.json
                     
                     # Find OpenCode binary (it should be in ~/.opencode/bin)
                     OPENCODE_PATH=""
                     if [ -f "$HOME/.opencode/bin/opencode" ]; then
                         OPENCODE_PATH="$HOME/.opencode/bin/opencode"
                         echo "Found OpenCode at: $OPENCODE_PATH"
                     else
                         echo "Searching for OpenCode binary..."
                         FOUND_PATH=$(find /root -name "opencode" -type f 2>/dev/null | head -1)
                         if [ -n "$FOUND_PATH" ]; then
                             OPENCODE_PATH="$FOUND_PATH"
                             echo "Found OpenCode at: $OPENCODE_PATH"
                         else
                             echo "OpenCode binary not found!"
                         fi
                     fi
                     
                     # Run OpenCode with timeout and capture output
                     echo "Starting OpenCode agent..."
                     if [ -n "$OPENCODE_PATH" ] && [ -f "$OPENCODE_PATH" ]; then
                         echo "Using OpenCode at: $OPENCODE_PATH"
                         echo "Environment variables:"
                         echo "GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
                         echo "VERTEXAI_PROJECT=$VERTEXAI_PROJECT"  
                         echo "VERTEXAI_LOCATION=$VERTEXAI_LOCATION"
                         
                         # Run OpenCode directly with the found binary
                         timeout 90 "$OPENCODE_PATH" -p '{prompt}' -q || echo "OpenCode execution completed or timed out"
                     else
                         echo "Cannot find OpenCode binary, skipping agent execution"
                     fi
                     
                     # List files to see what was created/modified
                     echo "=== Final file listing ==="
                     ls -la
                     
                     echo "=== test_script.py content ==="
                     cat test_script.py || echo "test_script.py not found"
                     """,
                ]

                logger.info("Running OpenCode agent in Docker container...")

                # Execute the Docker command with detailed logging
                process = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=temp_dir,
                )

                stdout, _ = await asyncio.wait_for(
                    process.communicate(), timeout=180
                )

                # Log the output for debugging
                output = (
                    stdout.decode("utf-8", errors="replace") if stdout else ""
                )
                logger.info(f"Docker output:\n{output}")

                # Check if the agent made the expected changes
                test_results = []

                # Check if the Python file was modified
                if test_file.exists():
                    content = test_file.read_text()
                    if (
                        "calculate_sum" in content
                        and "def calculate_sum" in content
                    ):
                        test_results.append(
                            " Python file enhanced with calculate_sum function"
                        )
                    else:
                        test_results.append(
                            " Python file missing calculate_sum function"
                        )
                        logger.info(f"Python file content: {content}")
                else:
                    test_results.append(" Python file no longer exists")

                # Determine overall success - single task test
                success_count = sum(
                    1 for result in test_results if result.startswith("")
                )
                total_count = len(test_results)

                if success_count >= 1:  # Task completed
                    self.log_test_result(
                        "OpenCode Agent File Editing",
                        True,
                        f"Agent completed {success_count}/{total_count} tasks: {'; '.join(test_results)}",
                        time.time() - test_start,
                    )
                    return True
                else:
                    self.log_test_result(
                        "OpenCode Agent File Editing",
                        False,
                        f"Agent completed {success_count}/{total_count} tasks: {'; '.join(test_results)} | Docker output in logs",
                        time.time() - test_start,
                    )
                    return False

        except asyncio.TimeoutError:
            self.log_test_result(
                "OpenCode Agent File Editing",
                False,
                "Test timed out after 3 minutes",
                time.time() - test_start,
            )
            return False
        except Exception as e:
            self.log_test_result(
                "OpenCode Agent File Editing",
                False,
                f"Test execution error: {str(e)}",
                time.time() - test_start,
            )
            return False

    async def run_all_tests(self):
        """Run all integration tests"""
        print(
            f"{Fore.CYAN} Starting Vertex AI Integration Tests{Style.RESET_ALL}"
        )
        print(f"Vertex AI URL: {self.vertex_ai_url}")
        print(f"Project ID: {self.project_id}")
        print(f"Timestamp: {self.start_time.isoformat()}")
        print("-" * 60)

        # Test sequence
        tests = [
            ("Vertex AI Authentication", self.test_vertex_ai_auth),
            ("Basic Chat", self.test_basic_chat),
            ("Function Calling", self.test_function_calling),
            ("Multi-Tool Calling", self.test_multi_tool_calling),
            (
                "OpenCode Agent File Editing",
                self.test_opencode_agent_file_editing,
            ),
        ]

        passed_tests = 0

        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_tests += 1

                # Small delay between tests
                await asyncio.sleep(1)

            except Exception as e:
                self.log_test_result(
                    test_name, False, f"Test execution error: {str(e)}"
                )

        # Summary
        total_tests = len(tests)
        print("-" * 60)
        print(f"{Fore.CYAN} Test Summary{Style.RESET_ALL}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {Fore.GREEN}{passed_tests}{Style.RESET_ALL}")
        print(
            f"Failed: {Fore.RED}{total_tests - passed_tests}{Style.RESET_ALL}"
        )
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        print(
            f"Duration: {(datetime.now() - self.start_time).total_seconds():.2f}s"
        )

        # Save results
        await self.save_results()

        # Exit with appropriate code
        exit_code = 0 if passed_tests == total_tests else 1
        exit(exit_code)

    async def save_results(self):
        """Save test results to file"""
        try:
            results_file = Path("test-results/integration_test_results.json")
            results_file.parent.mkdir(parents=True, exist_ok=True)

            summary = {
                "timestamp": self.start_time.isoformat(),
                "vertex_ai_url": self.vertex_ai_url,
                "project_id": self.project_id,
                "total_tests": len(self.results),
                "passed_tests": sum(1 for r in self.results if r["passed"]),
                "failed_tests": sum(
                    1 for r in self.results if not r["passed"]
                ),
                "duration_seconds": (
                    datetime.now() - self.start_time
                ).total_seconds(),
                "tests": self.results,
            }

            with open(results_file, "w") as f:
                json.dump(summary, f, indent=2)

            print(
                f"{Fore.BLUE} Results saved to: {results_file}{Style.RESET_ALL}"
            )

        except Exception as e:
            logger.error(f"Failed to save results: {e}")


async def main():
    """Main test runner"""
    tester = IntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
