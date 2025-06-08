"""
Agent Lifecycle Manager for Summit AI Platform
Manages the complete lifecycle of agent pods: startup, task execution, and reuse

TODO: Current implementation uses database polling which has limitations:
- Race conditions between agents
- No native backpressure handling
- Manual retry logic required
- No built-in priority queue management

Future: Migrate to Cloud Tasks HTTP endpoints or Pub/Sub pull subscriptions
for better task distribution, automatic retries, and backpressure control.
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

            # Initialize database connection
            self.db = await get_database()

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

            # Register agent in database
            await self._register_agent()

            # Load shared context
            await self._load_shared_context()

            # Set status to ready
            self.pod_state.status = AgentStatus.READY
            await self._update_agent_status(AgentStatus.READY)

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

    async def _register_agent(self):
        """Register agent in database"""
        agent_info = {
            "name": self.role_config.name,
            "roles": [self.role.value],
            "capabilities": self.role_config.capabilities,
            "version": "1.0.0",
            "max_concurrent_tasks": 1,
        }

        await self.db.register_agent(self.agent_id, agent_info)
        print(
            f"Agent {self.agent_id} registered with capabilities: {self.role_config.capabilities}"
        )

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
        """Update agent status in database"""
        try:
            await self.db.update_agent_heartbeat(self.agent_id, status)
            if self.pod_state:
                self.pod_state.status = status
                self.pod_state.last_heartbeat = datetime.utcnow()
        except Exception as e:
            print(f"Error updating agent status: {e}")

    async def start_lifecycle_loop(self):
        """Start the main agent lifecycle loop"""
        print(f"Starting lifecycle loop for agent {self.agent_id}")

        try:
            while True:
                # Send heartbeat
                await self._send_heartbeat()

                # Check for new tasks
                if self.pod_state.status == AgentStatus.READY:
                    task = await self._fetch_next_task()
                    if task:
                        await self._execute_task(task)

                # Wait before next iteration
                await asyncio.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            print(f"Agent {self.agent_id} shutting down")
            await self._update_agent_status(AgentStatus.OFFLINE)
        except Exception as e:
            print(f"Error in lifecycle loop: {e}")
            await self._update_agent_status(AgentStatus.ERROR)

    async def _send_heartbeat(self):
        """Send heartbeat to database"""
        try:
            if datetime.utcnow() - self.pod_state.last_heartbeat > timedelta(
                seconds=self.heartbeat_interval
            ):
                await self._update_agent_status(self.pod_state.status)
        except Exception as e:
            print(f"Error sending heartbeat: {e}")

    async def _fetch_next_task(self) -> Optional[AgentTask]:
        """Fetch the next task for this agent's role"""
        try:
            tasks = await self.db.get_tasks_for_role(self.role.value, limit=1)
            if tasks:
                task = tasks[0]

                # Claim the task
                await self.db.claim_agent_task(str(task.id), self.agent_id)

                print(f"Claimed task {task.id} for agent {self.agent_id}")
                return task

            return None

        except Exception as e:
            print(f"Error fetching next task: {e}")
            return None

    async def _execute_task(self, task: AgentTask):
        """Execute a task with full lifecycle management"""
        try:
            print(f"Executing task {task.id}: {task.task_type}")

            # Update status to busy
            self.pod_state.current_task_id = str(task.id)
            await self._update_agent_status(AgentStatus.BUSY)
            await update_task_status(
                str(task.id), "running", f"Started by agent {self.agent_id}"
            )

            # Prepare environment for task
            await self._prepare_task_environment(task)

            # Execute the actual task
            success, result, error = await self._run_task_logic(task)

            # Handle task completion
            await self._complete_task(task, success, result, error)

            # Clean up after task
            await self._cleanup_after_task(task)

            # Reset to ready state
            self.pod_state.current_task_id = None
            await self._update_agent_status(AgentStatus.READY)

        except Exception as e:
            print(f"Error executing task {task.id}: {e}")
            await self._complete_task(task, False, None, str(e))
            await self._update_agent_status(AgentStatus.READY)

    async def _prepare_task_environment(self, task: AgentTask):
        """Prepare the environment for task execution"""
        try:
            # Reset filesystem if required for this role
            if agent_role_manager.should_reset_filesystem(self.role):
                await self._reset_filesystem()

            # Set task-specific environment variables
            os.environ["TASK_ID"] = str(task.id)
            os.environ["TASK_TYPE"] = task.task_type

            # Create task context file
            task_context = {
                "task_id": str(task.id),
                "task_type": task.task_type,
                "payload": task.payload,
                "context": task.context,
                "priority": task.priority.value,
                "assigned_role": task.assigned_role,
            }

            context_file = os.path.join(
                self.workspace_path, ".current_task.json"
            )
            with open(context_file, "w") as f:
                json.dump(task_context, f, indent=2, default=str)

            print(f"Environment prepared for task {task.id}")

        except Exception as e:
            print(f"Error preparing task environment: {e}")
            raise

    async def _reset_filesystem(self):
        """Reset filesystem to clean state"""
        try:
            if not self.pod_state.filesystem_clean:
                print("Resetting filesystem to clean state")

                # Run the reset script if available
                reset_script = "/scripts/reset-agent.sh"
                if os.path.exists(reset_script):
                    result = subprocess.run(
                        ["/bin/bash", reset_script],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        print(f"Reset script failed: {result.stderr}")
                else:
                    # Manual cleanup
                    await self._manual_filesystem_cleanup()

                self.pod_state.filesystem_clean = True
                print("Filesystem reset completed")

        except Exception as e:
            print(f"Error resetting filesystem: {e}")

    async def _manual_filesystem_cleanup(self):
        """Manual filesystem cleanup when reset script not available"""
        try:
            # Clean temp directories
            temp_dirs = [
                "/tmp",
                f"{self.workspace_path}/temp",
                f"{self.workspace_path}/.cache",
            ]
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    subprocess.run(["rm", "-rf", f"{temp_dir}/*"], shell=True)

            # Reset git repository if it exists
            git_dir = os.path.join(self.workspace_path, ".git")
            if os.path.exists(git_dir):
                os.chdir(self.workspace_path)
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"], capture_output=True
                )
                subprocess.run(["git", "clean", "-fd"], capture_output=True)
                subprocess.run(
                    ["git", "checkout", "main"], capture_output=True
                )

            # Clear environment variables
            task_env_vars = ["TASK_ID", "TASK_TYPE", "CURRENT_BRANCH"]
            for var in task_env_vars:
                os.environ.pop(var, None)

        except Exception as e:
            print(f"Error in manual filesystem cleanup: {e}")

    async def _run_task_logic(
        self, task: AgentTask
    ) -> Tuple[bool, Optional[Any], Optional[str]]:
        """Run the actual task logic based on task type"""
        try:
            # This is where the task-specific logic would be implemented
            # For now, we'll have a basic framework

            task_type = task.task_type
            payload = task.payload

            print(f"Running task logic for type: {task_type}")

            # Load task-specific context
            full_context = agent_role_manager.get_context_for_role(
                self.role, task.context
            )

            # Different task execution based on type
            if task_type == "code_analysis":
                return await self._handle_code_analysis_task(
                    payload, full_context
                )
            elif task_type == "bug_fix":
                return await self._handle_bug_fix_task(payload, full_context)
            elif task_type == "feature_implementation":
                return await self._handle_feature_implementation_task(
                    payload, full_context
                )
            elif task_type == "infrastructure_update":
                return await self._handle_infrastructure_task(
                    payload, full_context
                )
            elif task_type == "test_creation":
                return await self._handle_test_creation_task(
                    payload, full_context
                )
            elif task_type == "documentation_update":
                return await self._handle_documentation_task(
                    payload, full_context
                )
            else:
                # Generic task handler
                return await self._handle_generic_task(payload, full_context)

        except Exception as e:
            return False, None, str(e)

    async def _handle_code_analysis_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle code analysis tasks"""
        # This would integrate with the existing analysis tools
        # For now, return a placeholder
        analysis_result = {
            "files_analyzed": payload.get("files", []),
            "issues_found": [],
            "recommendations": [],
            "agent_role": self.role.value,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return True, analysis_result, None

    async def _handle_generic_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle generic tasks"""
        # Basic task completion
        result = {
            "task_completed": True,
            "agent_role": self.role.value,
            "payload_processed": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return True, result, None

    async def _complete_task(
        self, task: AgentTask, success: bool, result: Any, error: Optional[str]
    ):
        """Complete task and update database"""
        try:
            # Update task status in database
            async with self.db.get_session() as session:
                from sqlalchemy import update

                from database_models import AgentTask as AgentTaskModel

                updates = {
                    "status": (
                        TaskStatus.COMPLETED if success else TaskStatus.FAILED
                    ),
                    "completed_at": datetime.utcnow(),
                    "result": result,
                    "error": error,
                }

                await session.execute(
                    update(AgentTaskModel)
                    .where(AgentTaskModel.id == task.id)
                    .values(**updates)
                )
                await session.commit()

            # Update agent metrics
            if success:
                await self.db.increment_agent_completed_tasks(self.agent_id)
                print(f"Task {task.id} completed successfully")
            else:
                await self.db.increment_agent_failed_tasks(self.agent_id)
                print(f"Task {task.id} failed: {error}")

        except Exception as e:
            print(f"Error completing task: {e}")

    async def _cleanup_after_task(self, task: AgentTask):
        """Clean up after task execution"""
        try:
            # Mark filesystem as dirty if task modified files
            if self.pod_state and self.role_config.requires_filesystem:
                self.pod_state.filesystem_clean = False

            # Clean up task-specific files
            task_files = [
                os.path.join(self.workspace_path, ".current_task.json"),
                os.path.join(self.workspace_path, ".task_output.json"),
            ]

            for task_file in task_files:
                if os.path.exists(task_file):
                    os.remove(task_file)

            print(f"Cleanup completed for task {task.id}")

        except Exception as e:
            print(f"Error in task cleanup: {e}")

    # Placeholder implementations for other task types
    async def _handle_bug_fix_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle bug fix tasks"""
        return True, {"bug_fixed": True, "agent_role": self.role.value}, None

    async def _handle_feature_implementation_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle feature implementation tasks"""
        return (
            True,
            {"feature_implemented": True, "agent_role": self.role.value},
            None,
        )

    async def _handle_infrastructure_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle infrastructure tasks"""
        return (
            True,
            {"infrastructure_updated": True, "agent_role": self.role.value},
            None,
        )

    async def _handle_test_creation_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle test creation tasks"""
        return (
            True,
            {"tests_created": True, "agent_role": self.role.value},
            None,
        )

    async def _handle_documentation_task(
        self, payload: Dict, context: str
    ) -> Tuple[bool, Any, Optional[str]]:
        """Handle documentation tasks"""
        return (
            True,
            {"documentation_updated": True, "agent_role": self.role.value},
            None,
        )


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
