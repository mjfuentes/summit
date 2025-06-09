#!/usr/bin/env python3
"""
OpenCode Integration for Summit AI

This module provides integration with OpenCode (https://github.com/opencode-ai/opencode)
as an alternative to Claude Code for autonomous development tasks.

Features:
- OpenCode CLI integration
- Session management
- Custom command execution
- Tool integration (bash, file operations, etc.)
- Support for multiple AI providers
- Self-hosted model support
- Cost tracking and optimization
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from cost_tracker import CostTracker


@dataclass
class OpenCodeConfig:
    """Configuration for OpenCode integration"""

    opencode_path: str = "opencode"  # Path to opencode binary
    model_provider: str = "anthropic"
    model_name: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    local_endpoint: Optional[str] = None  # For self-hosted models
    session_dir: Optional[str] = None
    custom_commands_dir: Optional[str] = None
    timeout: int = 300  # 5 minutes default timeout
    working_directory: str = "."


class OpenCodeManager:
    """Manager for OpenCode integration"""

    def __init__(self, config: OpenCodeConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cost_tracker = CostTracker()
        self.current_session_id: Optional[str] = None

    async def check_installation(self) -> bool:
        """Check if OpenCode is installed and accessible"""
        try:
            result = await self._run_command(
                [self.config.opencode_path, "--version"]
            )
            if result["success"]:
                self.logger.info(f"OpenCode found: {result['output']}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"OpenCode not found: {e}")
            return False

    async def install_opencode(self) -> bool:
        """Install OpenCode"""
        try:
            # Check if already installed
            if await self.check_installation():
                self.logger.info("OpenCode already installed")
                return True

            self.logger.info("Installing OpenCode...")

            # Use tempfile to generate secure temporary file path
            import os
            import tempfile

            # Create a secure temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".sh")
            os.close(temp_fd)  # Close the file descriptor

            try:
                # Create installation commands safely - avoid shell=True
                install_cmd = [
                    "curl",
                    "-s",
                    "https://raw.githubusercontent.com/opencode-ai/opencode/main/install.sh",
                    "-o",
                    temp_path,
                ]

                # Download the install script
                result = await self._run_command(install_cmd)
                if not result["success"]:
                    self.logger.error(
                        f"Failed to download installation script: {result['error']}"
                    )
                    return False

                # Make the script executable
                chmod_cmd = ["chmod", "+x", temp_path]
                result = await self._run_command(chmod_cmd)
                if not result["success"]:
                    self.logger.error(
                        f"Failed to make script executable: {result['error']}"
                    )
                    return False

                # Execute the script
                exec_cmd = [temp_path]
                result = await self._run_command(exec_cmd)

                if result["success"]:
                    self.logger.info("OpenCode installed successfully")
                    return await self.check_installation()
                else:
                    self.logger.error(
                        f"Failed to install OpenCode: {result['error']}"
                    )
                    return False
            finally:
                # Clean up the temporary file
                try:
                    os.remove(temp_path)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to remove temporary file {temp_path}: {e}"
                    )

        except Exception as e:
            self.logger.error(f"Error installing OpenCode: {e}")
            return False

    async def setup_configuration(self) -> bool:
        """Setup OpenCode configuration with MCP server integration"""
        try:
            config_dir = Path.home() / ".config" / "opencode"
            config_dir.mkdir(parents=True, exist_ok=True)

            config_file = config_dir / "config.json"

            # Create OpenCode configuration
            opencode_config = {
                "defaultAgent": "coder",
                "agents": {
                    "coder": {
                        "model": self.config.model_name,
                        "reasoningEffort": "high",
                    }
                },
            }

            # Add provider-specific configuration
            if (
                self.config.model_provider == "anthropic"
                and self.config.api_key
            ):
                opencode_config["anthropicApiKey"] = self.config.api_key
            elif self.config.local_endpoint:
                # For self-hosted models
                opencode_config["localEndpoint"] = self.config.local_endpoint

            # Configure MCP server integration for task management
            mcp_server_url = os.getenv(
                "MCP_SERVER_URL", "http://localhost:8080"
            )
            opencode_config["mcpServers"] = {
                "summit": {
                    "url": mcp_server_url,
                    "description": "Summit AI task management server",
                    "tools": [
                        "summit_update_task_status",
                        "summit_add_task_comment",
                        "summit_get_task",
                        "summit_list_tasks",
                    ],
                }
            }

            # Setup custom commands directory
            if self.config.custom_commands_dir:
                commands_dir = Path(self.config.custom_commands_dir)
                commands_dir.mkdir(parents=True, exist_ok=True)

            with open(config_file, "w") as f:
                json.dump(opencode_config, f, indent=2)

            self.logger.info(
                f"OpenCode configuration created with MCP integration: {config_file}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup OpenCode configuration: {e}")
            return False

    async def create_custom_command(self, name: str, content: str) -> bool:
        """Create a custom OpenCode command"""
        try:
            if not self.config.custom_commands_dir:
                commands_dir = (
                    Path.home() / ".config" / "opencode" / "commands"
                )
            else:
                commands_dir = Path(self.config.custom_commands_dir)

            commands_dir.mkdir(parents=True, exist_ok=True)

            command_file = commands_dir / f"{name}.md"

            with open(command_file, "w") as f:
                f.write(content)

            self.logger.info(f"Created custom command: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create custom command {name}: {e}")
            return False

    async def start_session(self, task_description: str) -> Optional[str]:
        """Start a new OpenCode session"""
        try:
            # Create session directory if specified
            if self.config.session_dir:
                session_dir = Path(self.config.session_dir)
                session_dir.mkdir(parents=True, exist_ok=True)

            # Generate session ID
            session_id = f"summit-{int(time.time())}"
            self.current_session_id = session_id

            # Create initial prompt for the session
            initial_prompt = f"""# Summit AI Autonomous Development Task

**Task:** {task_description}
**Session ID:** {session_id}
**Working Directory:** {self.config.working_directory}

## Context
You are working as part of Summit AI's autonomous development system.
Your goal is to complete the specified task efficiently and professionally.

## Available Tools
- bash: Execute shell commands
- read: Read file contents
- write: Write/modify files
- search: Search through files
- patch: Apply code patches
- diagnostics: Get code diagnostics

## Instructions
1. Analyze the task requirements
2. Explore the codebase to understand the current state
3. Implement the necessary changes
4. Test your implementation
5. Provide a summary of what was accomplished

Please start by exploring the current directory structure and understanding the codebase."""

            self.logger.info(f"Started OpenCode session: {session_id}")
            return session_id

        except Exception as e:
            self.logger.error(f"Failed to start OpenCode session: {e}")
            return None

    async def send_message(
        self, message: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a message to OpenCode"""
        try:
            start_time = time.time()

            # Prepare the command
            cmd = [self.config.opencode_path]

            # Add session management if supported
            if session_id:
                cmd.extend(["--session", session_id])

            # Set working directory
            if self.config.working_directory != ".":
                cmd.extend(["--cwd", self.config.working_directory])

            # Create temporary file for the message
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            ) as f:
                f.write(message)
                temp_file = f.name

            try:
                # Execute OpenCode with the message
                cmd.extend(["--file", temp_file])

                result = await self._run_command(
                    cmd, timeout=self.config.timeout
                )

                processing_time = time.time() - start_time

                # Track cost (estimate based on processing time)
                estimated_cost = processing_time * 0.001  # Rough estimate

                self.cost_tracker.record_call(
                    input_tokens=len(message.split()) * 1.3,  # Rough estimate
                    output_tokens=len(result.get("output", "").split()) * 1.3,
                    model=f"opencode_{self.config.model_name}",
                    call_type="autonomous_development",
                )

                return {
                    "success": result["success"],
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "processing_time": processing_time,
                    "estimated_cost": estimated_cost,
                    "session_id": session_id,
                }

            finally:
                # Clean up temporary file
                os.unlink(temp_file)

        except Exception as e:
            self.logger.error(f"Failed to send message to OpenCode: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
            }

    async def execute_task(
        self,
        task_description: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a development task using OpenCode with MCP integration"""
        try:
            start_time = time.time()

            # Get task ID and agent ID from environment if not provided
            if not task_id:
                task_id = os.getenv("TASK_ID")
            if not agent_id:
                agent_id = os.getenv("AGENT_ID", "opencode-agent")

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            ) as f:
                task_prompt = f"""# Summit AI Development Task

{task_description}

**Task ID:** {task_id}
**Agent ID:** {agent_id}

Please analyze the codebase and implement the requested changes following Summit's standards:
- Maintain >70% test coverage
- Follow existing code patterns
- Apply proper formatting (Black, isort)
- Add comprehensive error handling
- Use professional coding standards

**IMPORTANT - Task Completion:**
When you finish this task, you MUST use the MCP tool to update the task status:

For success:
```
summit_update_task_status({{
  "task_id": "{task_id}",
  "status": "completed",
  "agent_id": "{agent_id}",
  "result": {{
    "success": true,
    "summary": "Description of what was accomplished",
    "files_modified": ["list", "of", "files"],
    "tests_run": true,
    "coverage": percentage,
    "quality_checks": true
  }}
}})
```

For failure:
```
summit_update_task_status({{
  "task_id": "{task_id}",
  "status": "failed",
  "agent_id": "{agent_id}",
  "error": "Clear error message"
}})
```

Use the available tools to read, write, and test code as needed."""
                f.write(task_prompt)
                temp_file = f.name

            try:
                cmd = [self.config.opencode_path, "--file", temp_file]
                result = await self._run_command(
                    cmd, timeout=self.config.timeout
                )

                processing_time = time.time() - start_time

                self.cost_tracker.record_call(
                    input_tokens=len(task_description.split()) * 1.3,
                    output_tokens=len(result.get("output", "").split()) * 1.3,
                    model=f"opencode_{self.config.model_name}",
                    call_type="autonomous_development",
                )

                return {
                    "success": result["success"],
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "processing_time": processing_time,
                    "task_id": task_id,
                    "agent_id": agent_id,
                }

            finally:
                os.unlink(temp_file)

        except Exception as e:
            self.logger.error(f"Failed to execute task: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "task_id": task_id,
                "agent_id": agent_id,
            }

    async def get_session_history(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """Get the history of a session"""
        try:
            # OpenCode session history would be implementation-specific
            # This is a placeholder for future implementation
            return []
        except Exception as e:
            self.logger.error(f"Failed to get session history: {e}")
            return []

    async def list_sessions(self) -> List[str]:
        """List available sessions"""
        try:
            # Implementation would depend on OpenCode's session management
            return []
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []

    async def _run_command(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        shell: bool = False,
    ) -> Dict[str, Any]:
        """Run a command and return the result"""
        try:
            # Never use shell=True for security
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.working_directory,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout or self.config.timeout,
                )

                return {
                    "success": process.returncode == 0,
                    "output": stdout.decode("utf-8", errors="ignore"),
                    "error": stderr.decode("utf-8", errors="ignore"),
                    "returncode": process.returncode,
                }

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Command timed out after {
                        timeout or self.config.timeout} seconds",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}


class SummitOpenCodeIntegration:
    """Integration layer between Summit and OpenCode"""

    def __init__(self, config: Optional[OpenCodeConfig] = None):
        if config is None:
            # Create default configuration
            config = OpenCodeConfig(
                model_provider="anthropic",
                model_name="claude-3-5-sonnet-20241022",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                working_directory=os.getcwd(),
                custom_commands_dir=os.path.join(
                    os.getcwd(), ".opencode", "commands"
                ),
            )

        self.opencode = OpenCodeManager(config)
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize OpenCode integration"""
        try:
            # Check if OpenCode is installed
            if not await self.opencode.check_installation():
                self.logger.info(
                    "OpenCode not found, attempting installation..."
                )
                if not await self.opencode.install_opencode():
                    return False

            # Setup configuration
            if not await self.opencode.setup_configuration():
                return False

            # Create Summit-specific custom commands
            await self._create_summit_commands()

            self.logger.info("OpenCode integration initialized successfully")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to initialize OpenCode integration: {e}"
            )
            return False

    async def _create_summit_commands(self):
        """Create Summit-specific custom commands"""

        # Command for code analysis
        await self.opencode.create_custom_command(
            "summit-analyze",
            """# Summit Code Analysis

RUN find . -name "*.py" -type f | head -20
READ README.md
READ requirements.txt

Analyze the codebase structure and provide:
1. Architecture overview
2. Key components and their purposes
3. Dependencies and integrations
4. Potential improvements
5. Code quality assessment""",
        )

        # Command for implementing features
        await self.opencode.create_custom_command(
            "summit-implement",
            """# Summit Feature Implementation

Please implement the requested feature following these guidelines:

1. **Analysis Phase:**
   - Use summit_get_task to understand requirements
   - Explore existing codebase patterns
   - Identify integration points

2. **Implementation Phase:**
   - Follow existing code patterns
   - Maintain code quality standards
   - Add comprehensive tests
   - Update documentation

3. **Quality Assurance:**
   - Run tests and ensure >70% coverage
   - Apply code formatting (Black, isort)
   - Fix any linting issues
   - Verify functionality

4. **Task Completion:**
   - When finished, use summit_update_task_status tool to mark task as "completed"
   - Include task result data with implementation details
   - If task fails, use summit_update_task_status with "failed" status and error message

5. **Integration:**
   - Ensure proper error handling
   - Add logging where appropriate
   - Follow Summit's professional standards

**Important:** Always use the summit_update_task_status MCP tool to update task status instead of manual database calls.

Use the available tools to read, write, and test code as needed.""",
        )

        # Command for task completion
        await self.opencode.create_custom_command(
            "summit-finish-task",
            """# Summit Task Completion

When you have completed a task, use this command structure:

**For Successful Completion:**
Use the summit_update_task_status MCP tool with:
- task_id: The ID of the task you completed
- status: "completed" 
- agent_id: Your agent identifier
- result: Object containing:
  - success: true
  - summary: Brief description of what was accomplished
  - files_modified: List of files changed
  - tests_run: Whether tests were executed
  - coverage: Test coverage percentage if available
  - quality_checks: Whether linting/formatting was applied

**For Failed Tasks:**
Use the summit_update_task_status MCP tool with:
- task_id: The ID of the task that failed
- status: "failed"
- agent_id: Your agent identifier  
- error: Clear error message explaining what went wrong

**Example Usage:**
```
summit_update_task_status({
  "task_id": "task-123",
  "status": "completed",
  "agent_id": "opencode-agent-1",
  "result": {
    "success": true,
    "summary": "Implemented authentication system with JWT tokens",
    "files_modified": ["src/auth.py", "tests/test_auth.py"],
    "tests_run": true,
    "coverage": 85.3,
    "quality_checks": true
  }
})
```

**Never use manual database calls or direct API endpoints for task completion.**""",
        )

        # Command for debugging
        await self.opencode.create_custom_command(
            "summit-debug",
            """# Summit Debugging Session

RUN python -m pytest --tb=short -v
RUN python -m pylint src/ --errors-only

Analyze any errors or failures and:
1. Identify the root cause
2. Propose solutions
3. Implement fixes
4. Verify the fixes work
5. Run tests to ensure no regressions""",
        )

    async def execute_development_task(
        self, task_description: str
    ) -> Dict[str, Any]:
        """Execute a development task using OpenCode"""
        return await self.opencode.execute_task(task_description)

    async def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze the current codebase"""
        return await self.opencode.send_message("user:summit-analyze")

    async def implement_feature(
        self, feature_description: str
    ) -> Dict[str, Any]:
        """Implement a new feature"""
        message = f"user:summit-implement\n\nFeature to implement: {feature_description}"
        return await self.opencode.send_message(message)

    async def debug_issues(self) -> Dict[str, Any]:
        """Debug current issues in the codebase"""
        return await self.opencode.send_message("user:summit-debug")


# Convenience functions for easy integration
async def initialize_opencode_integration(
    model_provider: str = "local",
    model_name: str = "codellama/CodeLlama-13b-Instruct-hf",
    api_key: Optional[str] = None,
    local_endpoint: Optional[str] = None,
) -> SummitOpenCodeIntegration:
    """Initialize OpenCode integration with Summit

    For RunPod deployment:
    - Set model_provider="local"
    - Set local_endpoint to your RunPod endpoint URL
    - model_name should match your deployed model
    """

    # Auto-detect RunPod endpoint from environment
    if not local_endpoint:
        local_endpoint = os.getenv("RUNPOD_ENDPOINT_URL")

    config = OpenCodeConfig(
        model_provider=model_provider,
        model_name=model_name,
        api_key=api_key,
        local_endpoint=local_endpoint,
        working_directory=os.getcwd(),
    )

    integration = SummitOpenCodeIntegration(config)

    if await integration.initialize():
        return integration
    else:
        raise Exception("Failed to initialize OpenCode integration")


if __name__ == "__main__":
    # Example usage
    async def main():
        print("Summit AI - OpenCode Integration")
        print("=" * 50)

        try:
            # Initialize integration
            integration = await initialize_opencode_integration()

            # Test codebase analysis
            print("Analyzing codebase...")
            result = await integration.analyze_codebase()

            if result["success"]:
                print("Analysis completed successfully!")
                print(f"Output: {result['output'][:500]}...")
            else:
                print(f"Analysis failed: {result['error']}")

        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
