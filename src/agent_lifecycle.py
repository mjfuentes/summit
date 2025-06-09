"""
Agent Lifecycle Manager for Summit AI Platform
Manages the complete lifecycle of agent pods: startup, registration, and monitoring

Architecture:
- MCP-based task execution: OpenCode containers use MCP tools (summit_update_task_status,
  summit_get_task, etc.) to interact with Summit's task management system
- Agent registration: Agents register via MCP server for coordination
- Monitoring: Lifecycle manager handles heartbeats and status updates

Task Execution Flow:
1. OpenCode containers are instantiated with MCP server configuration
2. Containers use summit_get_task MCP tool to fetch work
3. Containers execute tasks using their AI capabilities
4. Containers use summit_update_task_status MCP tool to report completion
5. No manual database polling or direct API calls needed

Legacy Support:
- Backward compatibility methods for existing tests
- Direct database access maintained for testing scenarios
- Will be phased out as MCP adoption completes

This eliminates the previous limitations:
- No race conditions (MCP handles coordination)
- Built-in backpressure via MCP protocol
- Automatic retry logic through MCP tools
- Native priority queue management
"""

import asyncio
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from agent_roles import AgentRole, RoleContext, agent_role_manager
from database_models import AgentStatus, AgentTask, TaskStatus
from task_manager import mark_task_completed, update_task_status
from unified_database import get_database

# Import MCP client for registration
try:
    from summit_mcp_client import (
        MCPAgentLifecycleManager,
        SummitMCPClient,
        register_agent_with_summit,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@dataclass
class AgentPodState:
    """Represents the current state of an agent pod"""

    agent_id: str
    role: AgentRole
    status: AgentStatus
    current_task_id: Optional[str]
    filesystem_clean: bool
    last_heartbeat: datetime
    context_loaded: bool
    pod_name: Optional[str]
    workspace_path: str
    environment_variables: Dict[str, str]


class AgentLifecycleManager:
    """Manages the complete lifecycle of agent pods"""

    def __init__(
        self, agent_id: Optional[str] = None, role: Optional[AgentRole] = None
    ):
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.role = role or self._detect_role_from_environment()
        self.pod_state = None
        self.db = None
        self.mcp_client = None  # Add MCP client support

        # Configuration from role
        self.role_config = agent_role_manager.get_role_config(self.role)
        if not self.role_config:
            raise ValueError(f"Unsupported role: {self.role}")

        # Workspace and environment setup
        self.workspace_path = os.environ.get("WORKSPACE_PATH", "/workspace")
        self.heartbeat_interval = int(
            os.environ.get("AGENT_HEARTBEAT_INTERVAL", "60")
        )

    def _detect_role_from_environment(self) -> AgentRole:
        """Detect agent role from environment variables"""
        role_str = os.environ.get("AGENT_ROLE", "engineering").lower()

        # Map environment strings to roles
        role_mapping = {
            "product": AgentRole.PRODUCT,
            "pm": AgentRole.PRODUCT,
            "engineering": AgentRole.ENGINEERING,
            "engineer": AgentRole.ENGINEERING,
            "quality_control": AgentRole.QUALITY_CONTROL,
            "qc": AgentRole.QUALITY_CONTROL,
            "qa": AgentRole.QUALITY_CONTROL,
            "quality": AgentRole.QUALITY_CONTROL,
        }

        return role_mapping.get(role_str, AgentRole.PRODUCT)

    async def initialize_pod(self) -> bool:
        """Initialize agent pod on startup"""
        try:
            print(
                f"Initializing agent pod: {self.agent_id} with role: {self.role.value}"
            )

            # Try MCP registration (primary method for agent communication)
            if MCP_AVAILABLE:
                try:
                    self.mcp_client = await register_agent_with_summit(
                        self.agent_id,
                        self.role.value,
                        self.role_config.capabilities,
                    )
                    if self.mcp_client:
                        print("MCP registration successful")
                    else:
                        print(
                            "MCP registration failed, running in standalone mode"
                        )
                except Exception as e:
                    print(
                        f"MCP registration failed: {e}, running in standalone mode"
                    )
                    self.mcp_client = None
            else:
                print("MCP client not available, running in standalone mode")

            # Set up environment variables
            self._setup_environment_variables()

            # Initialize pod state
            self.pod_state = AgentPodState(
                agent_id=self.agent_id,
                role=self.role,
                status=AgentStatus.OFFLINE,
                current_task_id=None,
                filesystem_clean=True,
                last_heartbeat=datetime.utcnow(),
                context_loaded=False,
                pod_name=os.environ.get("HOSTNAME"),
                workspace_path=self.workspace_path,
                environment_variables=self.role_config.environment_variables,
            )

            # Agent registration via MCP only
            if self.mcp_client:
                print(f"Agent {self.agent_id} registered via MCP")
            else:
                print(
                    f"Agent {self.agent_id} running in standalone mode - no registration"
                )

            # Load shared context
            await self._load_shared_context()

            # Set status to ready
            self.pod_state.status = AgentStatus.READY
            if self.mcp_client:
                await self.mcp_client.update_status("active")

            # Create readiness file for Kubernetes readiness probe
            with open("/tmp/agent-ready", "w") as f:
                f.write(
                    f"Agent {self.agent_id} ready at {datetime.utcnow().isoformat()}"
                )

            print(f"Agent {self.agent_id} initialized successfully")
            return True

        except Exception as e:
            print(f"Error initializing agent pod: {e}")
            return False

    def _setup_environment_variables(self):
        """Set up role-specific environment variables"""
        for key, value in self.role_config.environment_variables.items():
            os.environ[key] = str(value)

        # Add agent-specific variables
        os.environ["AGENT_ID"] = self.agent_id
        os.environ["AGENT_ROLE"] = self.role.value
        os.environ["WORKSPACE_PATH"] = self.workspace_path

    async def _load_shared_context(self):
        """Load shared context for the agent role"""
        try:
            # Get role-specific context
            context = agent_role_manager.get_context_for_role(self.role)

            # Store context in a file for easy access
            context_file = os.path.join(
                self.workspace_path, ".agent_context.md"
            )
            with open(context_file, "w") as f:
                f.write(context)

            self.pod_state.context_loaded = True
            print(f"Shared context loaded for role: {self.role.value}")

        except Exception as e:
            print(f"Error loading shared context: {e}")

    async def _update_agent_status(self, status: AgentStatus):
        """Update agent status via MCP and database"""
        try:
            if self.mcp_client:
                await self.mcp_client.update_status(status.value.lower())

            # Update database heartbeat for test compatibility
            if self.db:
                await self.db.update_agent_heartbeat(self.agent_id, status)

            if self.pod_state:
                self.pod_state.status = status
                self.pod_state.last_heartbeat = datetime.utcnow()
        except Exception as e:
            print(f"Error updating agent status: {e}")

    async def start_lifecycle_loop(self):
        """Start the main agent lifecycle loop with MCP-based task management"""
        print(f"Starting lifecycle loop for agent {self.agent_id}")
        print(
            "Note: Task execution is now handled by OpenCode containers using MCP tools"
        )
        print(
            "This lifecycle manager primarily handles agent registration and monitoring"
        )

        try:
            while True:
                # Send heartbeat
                await self._send_heartbeat()

                # Agent status monitoring
                if self.pod_state.status == AgentStatus.READY:
                    if self.mcp_client:
                        # MCP-based agents are ready to receive tasks via OpenCode containers
                        # The containers will use summit_get_task and summit_update_task_status tools
                        pass
                    else:
                        print(
                            f"Agent {self.agent_id} running in standalone mode - monitoring only"
                        )

                # Wait before next iteration
                await asyncio.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            print(f"Agent {self.agent_id} shutting down")
            if self.mcp_client:
                await self.mcp_client.update_status("offline")
        except Exception as e:
            print(f"Error in lifecycle loop: {e}")
            if self.mcp_client:
                await self.mcp_client.update_status("error")

    async def _send_heartbeat(self):
        """Send heartbeat via MCP"""
        try:
            if datetime.utcnow() - self.pod_state.last_heartbeat > timedelta(
                seconds=self.heartbeat_interval
            ):
                await self._update_agent_status(self.pod_state.status)
        except Exception as e:
            print(f"Error sending heartbeat: {e}")

    # Legacy methods for backward compatibility with tests
    # NOTE: In production, OpenCode containers use MCP tools instead of these methods
    async def _register_agent(self):
        """Register agent with database (legacy method for tests)"""
        try:
            if not self.db:
                self.db = await get_database()

            agent_info = {
                "roles": [self.role.value],
                "capabilities": self.role_config.capabilities,
                "status": AgentStatus.READY.value,
            }
            await self.db.register_agent(self.agent_id, agent_info)
        except Exception as e:
            print(f"Error registering agent: {e}")

    async def _fetch_next_task(self) -> Optional[AgentTask]:
        """Fetch next available task (legacy method for tests)"""
        try:
            if not self.db:
                self.db = await get_database()

            tasks = await self.db.get_tasks_for_role(self.role.value, limit=1)
            if tasks:
                task = tasks[0]
                await self.db.claim_agent_task(task.id, self.agent_id)
                return task
            return None
        except Exception as e:
            print(f"Error fetching task: {e}")
            return None

    async def _prepare_task_environment(self, task: AgentTask):
        """Prepare environment for task execution"""
        try:
            # Set environment variables
            os.environ["TASK_ID"] = str(task.id)
            os.environ["TASK_TYPE"] = task.task_type

            # Create task context file
            context_file = os.path.join(
                self.workspace_path, ".current_task.json"
            )
            context_data = {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "payload": task.payload,
                "context": task.context,
            }

            with open(context_file, "w") as f:
                json.dump(context_data, f, indent=2)

        except Exception as e:
            print(f"Error preparing task environment: {e}")

    async def _cleanup_after_task(self, task: AgentTask):
        """Clean up after task execution"""
        try:
            # Remove task files
            context_file = os.path.join(
                self.workspace_path, ".current_task.json"
            )
            output_file = os.path.join(
                self.workspace_path, ".task_output.json"
            )

            for file_path in [context_file, output_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Mark filesystem as dirty for engineering role
            if self.role == AgentRole.ENGINEERING:
                self.pod_state.filesystem_clean = False

        except Exception as e:
            print(f"Error cleaning up after task: {e}")

    async def _reset_filesystem(self):
        """Reset filesystem to clean state"""
        try:
            # Reset git state (mock for tests)
            result = subprocess.run(
                ["git", "clean", "-fd"],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.pod_state.filesystem_clean = True

        except Exception as e:
            print(f"Error resetting filesystem: {e}")

    async def _complete_task(
        self,
        task: AgentTask,
        success: bool,
        result_data: Optional[Dict],
        error_message: Optional[str],
    ):
        """Complete a task using MCP tools (for compatibility with tests)"""
        try:
            # For new MCP-based workflow, tasks are completed by OpenCode containers
            # using the summit_update_task_status MCP tool. This method is maintained
            # for backward compatibility with existing tests.

            if self.mcp_client:
                # Use MCP client to update task status
                if success:
                    await self.mcp_client.call_tool(
                        "summit_update_task_status",
                        {
                            "task_id": str(task.id),
                            "status": "completed",
                            "agent_id": self.agent_id,
                            "result": result_data,
                        },
                    )
                else:
                    await self.mcp_client.call_tool(
                        "summit_update_task_status",
                        {
                            "task_id": str(task.id),
                            "status": "failed",
                            "agent_id": self.agent_id,
                            "error": error_message,
                        },
                    )
                return

            # Fallback to direct database access for tests (legacy compatibility)
            db_to_use = self.db
            if not db_to_use:
                db_to_use = await get_database()

            if success:
                result_json = json.dumps(result_data) if result_data else None
                updates = {
                    "status": TaskStatus.COMPLETED,
                    "result": result_json,
                    "completed_at": datetime.utcnow(),
                }
                await db_to_use.update_agent_task(str(task.id), updates)
            else:
                updates = {
                    "status": TaskStatus.FAILED,
                    "error": error_message,
                    "completed_at": datetime.utcnow(),
                }
                await db_to_use.update_agent_task(str(task.id), updates)

        except Exception as e:
            print(f"Error completing task: {e}")

    async def _handle_generic_task(
        self, payload: Dict[str, Any], context: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Handle generic task execution"""
        try:
            result = {
                "task_completed": True,
                "agent_role": self.role.value,
                "payload_processed": payload,
            }
            return True, result, None
        except Exception as e:
            return False, {}, str(e)

    async def _handle_code_analysis_task(
        self, payload: Dict[str, Any], context: str
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """Handle code analysis task execution"""
        try:
            files = payload.get("files", [])
            result = {
                "files_analyzed": files,
                "agent_role": self.role.value,
                "issues_found": [],
                "recommendations": [],
            }
            return True, result, None
        except Exception as e:
            return False, {}, str(e)


async def main():
    """Main entry point for agent pod"""
    # Get role from environment or command line
    role_str = os.environ.get("AGENT_ROLE", "engineering")
    try:
        role = AgentRole(role_str.lower())
    except ValueError:
        print(f"Invalid role: {role_str}, defaulting to engineering")
        role = AgentRole.ENGINEERING

    # Create and initialize agent
    agent = AgentLifecycleManager(role=role)

    # Initialize pod
    if await agent.initialize_pod():
        # Start lifecycle loop
        await agent.start_lifecycle_loop()
    else:
        print("Failed to initialize agent pod")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
