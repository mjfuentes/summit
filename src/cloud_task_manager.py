"""
Cloud Tasks Manager for Summit Agent System
Handles task distribution using Google Cloud Tasks
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from google.cloud import firestore, tasks_v2
from google.protobuf import timestamp_pb2

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    id: str
    type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class CloudTaskManager:
    """Manages task queue operations using Google Cloud Tasks"""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        queue_name: str = "summit-agent-queue",
        agent_service_url: str = None,
    ):
        self.project_id = project_id
        self.location = location
        self.queue_name = queue_name
        self.agent_service_url = (
            agent_service_url
            or "http://opencode-service.summit.svc.cluster.local"
        )

        # Initialize clients
        self.tasks_client = tasks_v2.CloudTasksClient()
        self.firestore_client = firestore.Client()

        # Queue path
        self.queue_path = self.tasks_client.queue_path(
            project_id, location, queue_name
        )

        # Firestore collections
        self.tasks_collection = "summit_tasks"
        self.agents_collection = "summit_agents"

    async def initialize(self):
        """Initialize the task queue and Firestore collections"""
        try:
            # Create queue if it doesn't exist
            await self._ensure_queue_exists()
            logger.info(f"Cloud Tasks queue initialized: {self.queue_path}")

        except Exception as e:
            logger.error(f"Failed to initialize Cloud Tasks: {e}")
            raise

    async def _ensure_queue_exists(self):
        """Ensure the Cloud Tasks queue exists"""
        try:
            # Try to get the queue
            self.tasks_client.get_queue(name=self.queue_path)
            logger.info(f"Queue {self.queue_name} already exists")

        except Exception:
            # Queue doesn't exist, create it
            logger.info(f"Creating queue {self.queue_name}")

            parent = self.tasks_client.location_path(
                self.project_id, self.location
            )
            queue = {
                "name": self.queue_path,
                "rate_limits": {
                    "max_dispatches_per_second": 10,
                    "max_burst_size": 100,
                    "max_concurrent_dispatches": 50,
                },
                "retry_config": {
                    "max_attempts": 3,
                    "max_retry_duration": {"seconds": 300},
                    "min_backoff": {"seconds": 1},
                    "max_backoff": {"seconds": 60},
                },
            }

            self.tasks_client.create_queue(parent=parent, queue=queue)
            logger.info(f"Queue {self.queue_name} created successfully")

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: int = 0,
    ) -> str:
        """Submit a new task to the queue"""
        task_id = str(uuid.uuid4())

        # Create task object
        task = Task(
            id=task_id, type=task_type, payload=payload, priority=priority
        )

        # Store task metadata in Firestore
        task_doc = self.firestore_client.collection(
            self.tasks_collection
        ).document(task_id)
        task_data = asdict(task)
        # Convert enums to their values for Firestore
        task_data["priority"] = task.priority.value
        task_data["status"] = task.status.value
        task_doc.set(
            {
                **task_data,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )

        # Create Cloud Task
        cloud_task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{self.agent_service_url}/execute",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Task-ID": task_id,
                    "X-Task-Type": task_type,
                    "X-Priority": str(priority.value),
                },
                "body": json.dumps(
                    {
                        "task_id": task_id,
                        "type": task_type,
                        "payload": payload,
                        "priority": priority.value,
                    }
                ).encode(),
            }
        }

        # Add delay if specified
        if delay_seconds > 0:
            schedule_time = timestamp_pb2.Timestamp()
            schedule_time.FromDatetime(
                datetime.utcnow() + timedelta(seconds=delay_seconds)
            )
            cloud_task["schedule_time"] = schedule_time

        # Submit to Cloud Tasks
        response = self.tasks_client.create_task(
            parent=self.queue_path, task=cloud_task
        )

        logger.info(
            f"Task {task_id} submitted to Cloud Tasks: {response.name}"
        )
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current task status from Firestore"""
        try:
            task_doc = (
                self.firestore_client.collection(self.tasks_collection)
                .document(task_id)
                .get()
            )

            if not task_doc.exists:
                return None

            task_data = task_doc.to_dict()

            # Remove Firestore-specific fields
            task_data.pop("updated_at", None)

            # Convert Firestore timestamps back to datetime
            if "created_at" in task_data and task_data["created_at"]:
                task_data["created_at"] = task_data["created_at"].replace(
                    tzinfo=None
                )
            if "started_at" in task_data and task_data["started_at"]:
                task_data["started_at"] = task_data["started_at"].replace(
                    tzinfo=None
                )
            if "completed_at" in task_data and task_data["completed_at"]:
                task_data["completed_at"] = task_data["completed_at"].replace(
                    tzinfo=None
                )

            # Convert enums
            if "priority" in task_data:
                task_data["priority"] = TaskPriority(task_data["priority"])
            if "status" in task_data:
                task_data["status"] = TaskStatus(task_data["status"])

            return Task(**task_data)

        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return None

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        agent_id: str = None,
        result: Dict[str, Any] = None,
        error: str = None,
    ):
        """Update task status in Firestore"""
        try:
            task_doc = self.firestore_client.collection(
                self.tasks_collection
            ).document(task_id)

            update_data = {
                "status": status.value,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }

            if agent_id:
                update_data["agent_id"] = agent_id

            if status == TaskStatus.RUNNING:
                update_data["started_at"] = firestore.SERVER_TIMESTAMP

            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                update_data["completed_at"] = firestore.SERVER_TIMESTAMP

                if result:
                    update_data["result"] = result

                if error:
                    update_data["error"] = error

            task_doc.update(update_data)
            logger.info(f"Task {task_id} status updated to {status.value}")

        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")
            raise

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            # Get queue info from Cloud Tasks
            queue = self.tasks_client.get_queue(name=self.queue_path)

            # Get task counts from Firestore
            tasks_ref = self.firestore_client.collection(self.tasks_collection)

            # Count by status
            stats = {}
            for status in TaskStatus:
                count_query = tasks_ref.where(
                    "status", "==", status.value
                ).count()
                result = count_query.get()
                stats[status.value] = result[0][0].value

            # Add queue info
            stats.update(
                {
                    "queue_name": self.queue_name,
                    "queue_state": (
                        queue.state.name if queue.state else "UNKNOWN"
                    ),
                    "max_dispatches_per_second": (
                        queue.rate_limits.max_dispatches_per_second
                        if queue.rate_limits
                        else 0
                    ),
                    "max_concurrent_dispatches": (
                        queue.rate_limits.max_concurrent_dispatches
                        if queue.rate_limits
                        else 0
                    ),
                }
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {"error": str(e)}

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register an agent in Firestore"""
        try:
            agent_doc = self.firestore_client.collection(
                self.agents_collection
            ).document(agent_id)
            agent_doc.set(
                {
                    **agent_info,
                    "registered_at": firestore.SERVER_TIMESTAMP,
                    "last_seen": firestore.SERVER_TIMESTAMP,
                    "status": "ready",
                }
            )

            logger.info(f"Agent {agent_id} registered")

        except Exception as e:
            logger.error(f"Error registering agent {agent_id}: {e}")
            raise

    async def update_agent_status(
        self, agent_id: str, status: str, current_task: str = None
    ):
        """Update agent status in Firestore"""
        try:
            agent_doc = self.firestore_client.collection(
                self.agents_collection
            ).document(agent_id)

            update_data = {
                "status": status,
                "last_seen": firestore.SERVER_TIMESTAMP,
            }

            if current_task:
                update_data["current_task"] = current_task
            elif status == "ready":
                update_data["current_task"] = None

            agent_doc.update(update_data)

        except Exception as e:
            logger.error(f"Error updating agent status for {agent_id}: {e}")

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status from Firestore"""
        try:
            agent_doc = (
                self.firestore_client.collection(self.agents_collection)
                .document(agent_id)
                .get()
            )

            if not agent_doc.exists:
                return {"status": "unknown", "agent_id": agent_id}

            return agent_doc.to_dict()

        except Exception as e:
            logger.error(f"Error getting agent status for {agent_id}: {e}")
            return {"status": "error", "agent_id": agent_id, "error": str(e)}

    async def list_active_agents(self) -> List[Dict[str, Any]]:
        """List all active agents"""
        try:
            # Get agents that have been seen in the last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)

            agents_ref = self.firestore_client.collection(
                self.agents_collection
            )
            query = agents_ref.where("last_seen", ">=", cutoff_time)

            agents = []
            for doc in query.stream():
                agent_data = doc.to_dict()
                agent_data["agent_id"] = doc.id
                agents.append(agent_data)

            return agents

        except Exception as e:
            logger.error(f"Error listing active agents: {e}")
            return []

    async def cleanup_old_tasks(self, days: int = 7):
        """Clean up old completed/failed tasks"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            tasks_ref = self.firestore_client.collection(self.tasks_collection)

            # Delete old completed tasks
            for status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                query = tasks_ref.where("status", "==", status.value).where(
                    "completed_at", "<=", cutoff_time
                )

                batch = self.firestore_client.batch()
                count = 0

                for doc in query.stream():
                    batch.delete(doc.reference)
                    count += 1

                    # Firestore batch limit is 500
                    if count >= 500:
                        batch.commit()
                        batch = self.firestore_client.batch()
                        count = 0

                if count > 0:
                    batch.commit()

                logger.info(f"Cleaned up {count} old {status.value} tasks")

        except Exception as e:
            logger.error(f"Error cleaning up old tasks: {e}")


# Global instance
task_manager = CloudTaskManager(
    project_id="summit-ai-platform",  # Will be configurable
    location="us-central1",
    queue_name="summit-agent-queue",
)
