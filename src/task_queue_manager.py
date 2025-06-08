"""
Task Queue Manager for Summit Agent System
Handles task distribution, status tracking, and agent coordination
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
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
    claimed_at: Optional[datetime] = None
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


class TaskQueueManager:
    """Manages task queue operations using Redis"""

    def __init__(self, redis_url: str = "redis://redis-service:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

        # Queue names
        self.pending_queue = "summit:tasks:pending"
        self.claimed_queue = "summit:tasks:claimed"
        self.running_queue = "summit:tasks:running"
        self.completed_queue = "summit:tasks:completed"
        self.failed_queue = "summit:tasks:failed"
        self.dead_letter_queue = "summit:tasks:dead_letter"

        # Task data storage
        self.task_data_prefix = "summit:task:data:"
        self.agent_status_prefix = "summit:agent:status:"

    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        logger.info("Connected to Redis task queue")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Submit a new task to the queue"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id, type=task_type, payload=payload, priority=priority
        )

        # Store task data
        await self.redis_client.hset(
            f"{self.task_data_prefix}{task_id}",
            mapping={
                "data": json.dumps(asdict(task), default=str),
                "created_at": task.created_at.isoformat(),
            },
        )

        # Add to pending queue with priority score
        await self.redis_client.zadd(
            self.pending_queue, {task_id: priority.value}
        )

        logger.info(f"Task {task_id} submitted with priority {priority.name}")
        return task_id

    async def claim_task(self, agent_id: str) -> Optional[Task]:
        """Claim the highest priority pending task"""
        # Get highest priority task (highest score)
        result = await self.redis_client.zpopmax(self.pending_queue)

        if not result:
            return None

        task_id, priority_score = result[0]
        task_id = task_id.decode() if isinstance(task_id, bytes) else task_id

        # Get task data
        task_data = await self.redis_client.hget(
            f"{self.task_data_prefix}{task_id}", "data"
        )

        if not task_data:
            logger.error(f"Task data not found for {task_id}")
            return None

        task_dict = json.loads(task_data)
        task = Task(**task_dict)

        # Update task status
        task.status = TaskStatus.CLAIMED
        task.claimed_at = datetime.utcnow()
        task.agent_id = agent_id

        # Store updated task
        await self.redis_client.hset(
            f"{self.task_data_prefix}{task_id}",
            "data",
            json.dumps(asdict(task), default=str),
        )

        # Move to claimed queue
        await self.redis_client.zadd(
            self.claimed_queue, {task_id: datetime.utcnow().timestamp()}
        )

        # Update agent status
        await self.redis_client.hset(
            f"{self.agent_status_prefix}{agent_id}",
            mapping={
                "status": "busy",
                "current_task": task_id,
                "claimed_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Task {task_id} claimed by agent {agent_id}")
        return task

    async def start_task(self, task_id: str, agent_id: str):
        """Mark task as started"""
        task_data = await self.redis_client.hget(
            f"{self.task_data_prefix}{task_id}", "data"
        )

        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        task_dict = json.loads(task_data)
        task = Task(**task_dict)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()

        # Update task data
        await self.redis_client.hset(
            f"{self.task_data_prefix}{task_id}",
            "data",
            json.dumps(asdict(task), default=str),
        )

        # Move from claimed to running
        await self.redis_client.zrem(self.claimed_queue, task_id)
        await self.redis_client.zadd(
            self.running_queue, {task_id: datetime.utcnow().timestamp()}
        )

        logger.info(f"Task {task_id} started by agent {agent_id}")

    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark task as completed with result"""
        task_data = await self.redis_client.hget(
            f"{self.task_data_prefix}{task_id}", "data"
        )

        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        task_dict = json.loads(task_data)
        task = Task(**task_dict)

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = result

        # Update task data
        await self.redis_client.hset(
            f"{self.task_data_prefix}{task_id}",
            "data",
            json.dumps(asdict(task), default=str),
        )

        # Move to completed queue
        await self.redis_client.zrem(self.running_queue, task_id)
        await self.redis_client.zadd(
            self.completed_queue, {task_id: datetime.utcnow().timestamp()}
        )

        # Update agent status
        if task.agent_id:
            await self.redis_client.hset(
                f"{self.agent_status_prefix}{task.agent_id}",
                mapping={
                    "status": "ready",
                    "current_task": "",
                    "last_completed": task_id,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            )

        logger.info(f"Task {task_id} completed successfully")

    async def fail_task(self, task_id: str, error: str, retry: bool = True):
        """Mark task as failed"""
        task_data = await self.redis_client.hget(
            f"{self.task_data_prefix}{task_id}", "data"
        )

        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        task_dict = json.loads(task_data)
        task = Task(**task_dict)

        task.retry_count += 1
        task.error = error

        # Check if we should retry
        if retry and task.retry_count <= task.max_retries:
            task.status = TaskStatus.PENDING
            task.claimed_at = None
            task.started_at = None
            task.agent_id = None

            # Re-queue for retry
            await self.redis_client.zadd(
                self.pending_queue, {task_id: task.priority.value}
            )

            logger.info(
                f"Task {task_id} failed, retry {task.retry_count}/{task.max_retries}"
            )
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()

            # Move to dead letter queue
            await self.redis_client.zadd(
                self.dead_letter_queue,
                {task_id: datetime.utcnow().timestamp()},
            )

            logger.error(f"Task {task_id} failed permanently: {error}")

        # Update task data
        await self.redis_client.hset(
            f"{self.task_data_prefix}{task_id}",
            "data",
            json.dumps(asdict(task), default=str),
        )

        # Remove from running queue
        await self.redis_client.zrem(self.running_queue, task_id)

        # Update agent status
        if task.agent_id:
            await self.redis_client.hset(
                f"{self.agent_status_prefix}{task.agent_id}",
                mapping={
                    "status": "ready",
                    "current_task": "",
                    "last_error": error,
                    "failed_at": datetime.utcnow().isoformat(),
                },
            )

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current task status"""
        task_data = await self.redis_client.hget(
            f"{self.task_data_prefix}{task_id}", "data"
        )

        if not task_data:
            return None

        task_dict = json.loads(task_data)
        return Task(**task_dict)

    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "pending": await self.redis_client.zcard(self.pending_queue),
            "claimed": await self.redis_client.zcard(self.claimed_queue),
            "running": await self.redis_client.zcard(self.running_queue),
            "completed": await self.redis_client.zcard(self.completed_queue),
            "failed": await self.redis_client.zcard(self.failed_queue),
            "dead_letter": await self.redis_client.zcard(
                self.dead_letter_queue
            ),
        }

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status"""
        status = await self.redis_client.hgetall(
            f"{self.agent_status_prefix}{agent_id}"
        )

        if not status:
            return {"status": "unknown", "agent_id": agent_id}

        # Decode bytes keys/values
        return {
            k.decode() if isinstance(k, bytes) else k: (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in status.items()
        }

    async def cleanup_stale_tasks(self, timeout_minutes: int = 30):
        """Clean up stale tasks that have been running too long"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        cutoff_timestamp = cutoff_time.timestamp()

        # Get stale running tasks
        stale_tasks = await self.redis_client.zrangebyscore(
            self.running_queue, 0, cutoff_timestamp
        )

        for task_id in stale_tasks:
            task_id = (
                task_id.decode() if isinstance(task_id, bytes) else task_id
            )
            await self.fail_task(task_id, "Task timeout", retry=True)
            logger.warning(f"Task {task_id} timed out and marked for retry")


# Global instance
task_queue = TaskQueueManager()
