#!/usr/bin/env python3
"""
Task Queue Manager - Hybrid PostgreSQL and Cloud Tasks implementation
for Summit task distribution and management.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from database_models import (
    AgentTask,
    TaskLifecycleStage,
    TaskPriority,
    TaskStatus,
)
from unified_database import UnifiedDatabaseManager, get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskQueueManager:
    """
    Manages task distribution using a hybrid approach:
    - PostgreSQL for task storage and state management
    - Cloud Tasks for distribution and delivery
    """

    def __init__(
        self,
        project_id: str = None,
        location: str = None,
        base_url: str = None,
        database: UnifiedDatabaseManager = None,
    ):
        """
        Initialize the task queue manager

        Args:
            project_id: GCP project ID
            location: GCP region
            base_url: Base URL for agent endpoints
            database: Database manager instance
        """
        self.project_id = project_id or os.environ.get(
            "GCP_PROJECT_ID", "summit-ai-platform"
        )
        self.location = location or os.environ.get(
            "GCP_LOCATION", "us-central1"
        )
        self.base_url = base_url or os.environ.get(
            "AGENT_ENDPOINT_URL", "https://agent.summit.ai"
        )
        self.db = database
        self.task_client = None
        self.initialized = False
        self.queue_cache = {}  # Cache for queue existence checks

    async def initialize(self):
        """Initialize the task queue manager"""
        if not self.db:
            self.db = await get_database()

        # Initialize Cloud Tasks client
        self.task_client = tasks_v2.CloudTasksClient()
        self.initialized = True

        logger.info(
            f"Task Queue Manager initialized for project {self.project_id} in {self.location}"
        )
        return self

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        assigned_role: str = "engineering",
        delay_seconds: int = 0,
    ) -> str:
        """
        Submit a new task to the system

        Args:
            task_type: Type of task
            payload: Task data
            priority: Task priority
            assigned_role: Role assigned to the task
            delay_seconds: Delay before task execution

        Returns:
            Task ID
        """
        if not self.initialized:
            await self.initialize()

        # 1. Create task in database with PENDING status
        task_data = {
            "task_type": task_type,
            "payload": payload,
            "priority": priority,
            "assigned_role": assigned_role,
            "status": TaskStatus.PENDING,
        }

        task = await self.db.create_agent_task(task_data)
        task_id = str(task.id)

        # 2. Create Cloud Tasks queue for the role if it doesn't exist
        queue_name = f"{assigned_role}-tasks"
        await self._ensure_queue_exists(queue_name)

        # 3. Submit task to Cloud Tasks
        await self._create_cloud_task(
            queue_name=queue_name,
            task_id=task_id,
            payload={"task_id": task_id},
            delay_seconds=delay_seconds,
        )

        logger.info(
            f"Task {task_id} ({task_type}) submitted to {queue_name} with priority {priority.name}"
        )
        return task_id

    async def claim_task(
        self, task_id: str, agent_id: str
    ) -> Optional[AgentTask]:
        """
        Claim a task for an agent

        Args:
            task_id: Task ID
            agent_id: Agent ID

        Returns:
            Claimed task or None if claim failed
        """
        if not self.initialized:
            await self.initialize()

        # Attempt to claim the task atomically in the database
        claimed = await self.db.claim_agent_task(task_id, agent_id)

        if claimed:
            # Get the task data after successful claim
            task = await self.db.get_agent_task(task_id)

            # Start the design stage in lifecycle
            await self.db.start_stage_work(
                task_id=task_id,
                agent_id=agent_id,
                stage=TaskLifecycleStage.DESIGN,
            )

            logger.info(f"Task {task_id} claimed by agent {agent_id}")
            return task

        logger.info(f"Task {task_id} claim by agent {agent_id} failed")
        return None

    async def complete_task(
        self,
        task_id: str,
        agent_id: str,
        success: bool = True,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Complete a task

        Args:
            task_id: Task ID
            agent_id: Agent ID
            success: Whether the task was successful
            result: Task result data
            error_message: Error message if task failed

        Returns:
            True if task was completed successfully
        """
        if not self.initialized:
            await self.initialize()

        # Get the task
        task = await self.db.get_agent_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for completion")
            return False

        # Verify agent owns this task
        if task.agent_id != agent_id:
            logger.warning(
                f"Task {task_id} is assigned to {task.agent_id}, not {agent_id}"
            )
            return False

        # Update task status
        final_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        updates = {
            "status": final_status,
            "completed_at": datetime.utcnow(),
        }

        if success:
            updates["result"] = result or {}
            # Mark as completed
            await self.db.transition_task_stage(
                task_id=task_id,
                agent_id=agent_id,
                to_stage=TaskLifecycleStage.COMPLETED,
                stage_output=result or {},
                stage_summary="Task completed",
                files_modified=[],
                quality_score=5.0,
                completion_status="completed",
                transition_reason="Task completed successfully",
            )
        else:
            updates["error"] = error_message or "Task failed"
            await self.db.transition_task_stage(
                task_id=task_id,
                agent_id=agent_id,
                to_stage=TaskLifecycleStage.DESIGN,
                stage_output={"error": error_message or "Task failed"},
                stage_summary=f"Task failed: {error_message or 'Unknown error'}",
                files_modified=[],
                quality_score=2.0,
                completion_status="failed",
                transition_reason="Task execution failed",
            )

        updated_task = await self.db.update_agent_task(task_id, updates)

        if updated_task:
            logger.info(
                f"Task {task_id} completed with status {final_status.name} by agent {agent_id}"
            )
            return True

        logger.warning(f"Failed to update task {task_id} for completion")
        return False

    async def get_next_available_task(
        self,
        agent_id: str,
        roles: List[str],
        limit: int = 1,
        auto_claim: bool = True,
    ) -> List[AgentTask]:
        """
        Get next available task for an agent based on role

        Note: Current implementation uses database polling for task distribution.
        For better scalability with many concurrent agents, consider migrating
        to Redis pub/sub or Cloud Pub/Sub for real-time task notifications.
        See docs/TASK_QUEUE_USAGE.md for performance characteristics.

        Args:
            agent_id: Agent ID
            roles: List of roles the agent can fulfill (usually just one role)
            limit: Maximum number of tasks to return
            auto_claim: Whether to automatically claim the task (default: True)

        Returns:
            List containing the claimed task or empty list if no task available
        """
        if not self.initialized:
            await self.initialize()

        if not roles:
            logger.warning(
                f"Agent {agent_id} requested tasks but provided no roles"
            )
            return []

        role = roles[0]  # Just use the first role (simplified approach)

        # Get tasks for this role
        available_tasks = await self.db.get_tasks_for_role(
            role, limit=limit * 2
        )

        if not available_tasks:
            logger.debug(
                f"No available tasks found for agent {agent_id} with role {role}"
            )
            return []

        # Sort by priority and creation date
        available_tasks.sort(
            key=lambda t: (
                # Sort by priority value (URGENT=4, HIGH=3, NORMAL=2, LOW=1)
                (
                    4
                    if t.priority.name == "URGENT"
                    else (
                        3
                        if t.priority.name == "HIGH"
                        else 2 if t.priority.name == "NORMAL" else 1
                    )
                ),
                # Then by creation time (oldest first)
                t.created_at,
            ),
            reverse=True,  # Higher priority first
        )

        # Auto-claim the highest priority task (default behavior)
        if auto_claim and available_tasks:
            for task in available_tasks[
                :3
            ]:  # Try up to 3 tasks in case of race conditions
                claimed_task = await self.claim_task(
                    task_id=str(task.id), agent_id=agent_id
                )

                if claimed_task:
                    logger.info(
                        f"Agent {agent_id} claimed task {task.id} of type {task.task_type} for role {role}"
                    )
                    return [claimed_task]
                else:
                    logger.debug(
                        f"Agent {agent_id} failed to claim task {task.id} (likely claimed by another agent)"
                    )

            # If we couldn't claim any task, return empty list
            logger.info(
                f"Agent {agent_id} could not claim any tasks from {len(available_tasks)} available tasks"
            )
            return []

        # Return available tasks (limited to requested amount) - only used if auto_claim=False
        result = available_tasks[:limit]
        logger.info(
            f"Found {len(result)} available tasks for agent {agent_id} with role {role}"
        )
        return result

    async def _ensure_queue_exists(self, queue_name: str) -> bool:
        """
        Ensure a Cloud Tasks queue exists

        Args:
            queue_name: Name of the queue

        Returns:
            True if queue exists or was created
        """
        if queue_name in self.queue_cache:
            return True

        try:
            # Check if queue exists
            parent = f"projects/{self.project_id}/locations/{self.location}"
            queue_path = f"{parent}/queues/{queue_name}"

            try:
                self.task_client.get_queue(name=queue_path)
                self.queue_cache[queue_name] = True
                return True
            except Exception:
                # Queue doesn't exist, create it
                queue = {
                    "name": queue_path,
                    "rate_limits": {
                        "max_dispatches_per_second": 5,
                        "max_concurrent_dispatches": 10,
                    },
                    "retry_config": {
                        "max_attempts": 5,
                        "max_retry_duration": "3600s",
                        "max_backoff": "60s",
                        "min_backoff": "5s",
                        "max_doublings": 3,
                    },
                }

                self.task_client.create_queue(parent=parent, queue=queue)
                self.queue_cache[queue_name] = True
                logger.info(f"Created Cloud Tasks queue: {queue_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to ensure queue {queue_name} exists: {e}")
            return False

    async def _create_cloud_task(
        self,
        queue_name: str,
        task_id: str,
        payload: Dict[str, Any],
        delay_seconds: int = 0,
    ) -> bool:
        """
        Create a task in Cloud Tasks

        Args:
            queue_name: Name of the queue
            task_id: Task ID to use
            payload: Task payload
            delay_seconds: Delay before task execution

        Returns:
            True if task was created successfully
        """
        try:
            # Create task
            parent = self.task_client.queue_path(
                self.project_id, self.location, queue_name
            )

            # Convert payload to JSON string and encode as bytes
            payload_bytes = json.dumps(payload).encode()

            # Create task object
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{self.base_url}/api/task",
                    "headers": {"Content-Type": "application/json"},
                    "body": payload_bytes,
                },
                "name": f"{parent}/tasks/{task_id}",
            }

            # Add schedule time if there's a delay
            if delay_seconds > 0:
                # Create Timestamp protobuf
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(
                    datetime.utcnow() + timedelta(seconds=delay_seconds)
                )
                task["schedule_time"] = timestamp

            # Create the task in Cloud Tasks
            response = self.task_client.create_task(parent=parent, task=task)
            logger.info(f"Created Cloud Task: {response.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create Cloud Task: {e}")
            return False


# Singleton instance
_task_queue_manager = None


async def get_task_queue_manager() -> TaskQueueManager:
    """Get or create the task queue manager singleton"""
    global _task_queue_manager

    if _task_queue_manager is None:
        _task_queue_manager = TaskQueueManager()
        await _task_queue_manager.initialize()

    return _task_queue_manager


async def close_task_queue_manager():
    """Close the task queue manager"""
    global _task_queue_manager

    if _task_queue_manager is not None:
        _task_queue_manager = None
