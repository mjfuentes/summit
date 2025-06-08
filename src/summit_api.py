"""
Summit API - Main interface for task submission and monitoring
Integrates with Cloud Tasks for agent coordination
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cloud_task_manager import (
    CloudTaskManager,
    Task,
    TaskPriority,
    TaskStatus,
    task_manager,
)

logger = logging.getLogger(__name__)


class TaskSubmissionRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: str = "normal"
    delay_seconds: int = 0


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    agent_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class QueueStatsResponse(BaseModel):
    queue_name: str
    pending: int
    running: int
    completed: int
    failed: int
    total_agents: int
    active_agents: int


class AgentStatusResponse(BaseModel):
    agent_id: str
    status: str
    current_task: Optional[str] = None
    uptime_seconds: float
    last_seen: str


class SummitAPI:
    """Main Summit API for task management"""

    def __init__(self):
        self.task_manager = task_manager

    async def initialize(self):
        """Initialize the API"""
        try:
            await self.task_manager.initialize()
            logger.info("Summit API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Summit API: {e}")
            raise

    async def submit_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        delay_seconds: int = 0,
    ) -> str:
        """Submit a new task"""
        try:
            # Convert priority string to enum
            priority_map = {
                "low": TaskPriority.LOW,
                "normal": TaskPriority.NORMAL,
                "high": TaskPriority.HIGH,
                "urgent": TaskPriority.URGENT,
            }

            task_priority = priority_map.get(
                priority.lower(), TaskPriority.NORMAL
            )

            # Submit task
            task_id = await self.task_manager.submit_task(
                task_type=task_type,
                payload=payload,
                priority=task_priority,
                delay_seconds=delay_seconds,
            )

            logger.info(f"Task {task_id} submitted: {task_type}")
            return task_id

        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            raise

    async def get_task_status(
        self, task_id: str
    ) -> Optional[TaskStatusResponse]:
        """Get task status"""
        try:
            task = await self.task_manager.get_task_status(task_id)

            if not task:
                return None

            # Calculate execution time if completed
            execution_time = None
            if task.started_at and task.completed_at:
                execution_time = (
                    task.completed_at - task.started_at
                ).total_seconds()

            return TaskStatusResponse(
                task_id=task.id,
                status=task.status.value,
                created_at=(
                    task.created_at.isoformat() if task.created_at else ""
                ),
                started_at=(
                    task.started_at.isoformat() if task.started_at else None
                ),
                completed_at=(
                    task.completed_at.isoformat()
                    if task.completed_at
                    else None
                ),
                agent_id=task.agent_id,
                result=task.result,
                error=task.error,
                execution_time=execution_time,
            )

        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            raise

    async def get_queue_stats(self) -> QueueStatsResponse:
        """Get queue statistics"""
        try:
            stats = await self.task_manager.get_queue_stats()
            agents = await self.task_manager.list_active_agents()

            return QueueStatsResponse(
                queue_name=stats.get("queue_name", "unknown"),
                pending=stats.get("pending", 0),
                running=stats.get("running", 0),
                completed=stats.get("completed", 0),
                failed=stats.get("failed", 0),
                total_agents=len(agents),
                active_agents=len(
                    [a for a in agents if a.get("status") in ["ready", "busy"]]
                ),
            )

        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            raise

    async def list_agents(self) -> List[AgentStatusResponse]:
        """List all active agents"""
        try:
            agents = await self.task_manager.list_active_agents()

            result = []
            for agent in agents:
                # Calculate uptime
                uptime = 0
                if "registered_at" in agent and agent["registered_at"]:
                    uptime = (
                        datetime.utcnow() - agent["registered_at"]
                    ).total_seconds()

                result.append(
                    AgentStatusResponse(
                        agent_id=agent.get("agent_id", "unknown"),
                        status=agent.get("status", "unknown"),
                        current_task=agent.get("current_task"),
                        uptime_seconds=uptime,
                        last_seen=(
                            agent.get("last_seen", "").isoformat()
                            if agent.get("last_seen")
                            else ""
                        ),
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            raise


# Global API instance
summit_api = SummitAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await summit_api.initialize()
    yield
    # Shutdown
    logger.info("Summit API shutting down")


# FastAPI app
app = FastAPI(
    title="Summit AI Platform",
    description="Autonomous AI development system with Cloud Tasks integration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/tasks", response_model=Dict[str, str])
async def submit_task(request: TaskSubmissionRequest):
    """Submit a new task to the agent queue"""
    try:
        task_id = await summit_api.submit_task(
            task_type=request.type,
            payload=request.payload,
            priority=request.priority,
            delay_seconds=request.delay_seconds,
        )

        return {"task_id": task_id, "status": "submitted"}

    except Exception as e:
        logger.error(f"Error in submit_task endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        status = await summit_api.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="Task not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_task_status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """Get queue statistics"""
    try:
        return await summit_api.get_queue_stats()

    except Exception as e:
        logger.error(f"Error in get_queue_stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents", response_model=List[AgentStatusResponse])
async def list_agents():
    """List all active agents"""
    try:
        return await summit_api.list_agents()

    except Exception as e:
        logger.error(f"Error in list_agents endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = await summit_api.get_queue_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "queue_stats": stats.dict(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example task submission endpoints for common operations
@app.post("/tasks/code-analysis")
async def submit_code_analysis(files: List[str], priority: str = "normal"):
    """Submit a code analysis task"""
    try:
        task_id = await summit_api.submit_task(
            task_type="code_analysis",
            payload={"files": files},
            priority=priority,
        )

        return {"task_id": task_id, "type": "code_analysis"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/run-tests")
async def submit_test_run(
    test_files: List[str] = None, priority: str = "normal"
):
    """Submit a test execution task"""
    try:
        task_id = await summit_api.submit_task(
            task_type="run_tests",
            payload={"test_files": test_files or []},
            priority=priority,
        )

        return {"task_id": task_id, "type": "run_tests"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/pr-review")
async def submit_pr_review(
    pr_number: int, files: List[str], priority: str = "high"
):
    """Submit a PR review task"""
    try:
        task_id = await summit_api.submit_task(
            task_type="pr_review",
            payload={"pr_number": pr_number, "files": files},
            priority=priority,
        )

        return {"task_id": task_id, "type": "pr_review"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/deploy")
async def submit_deployment(
    environment: str, version: str, priority: str = "urgent"
):
    """Submit a deployment task"""
    try:
        task_id = await summit_api.submit_task(
            task_type="deploy_code",
            payload={"environment": environment, "version": version},
            priority=priority,
        )

        return {"task_id": task_id, "type": "deploy_code"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the API
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("summit_api:app", host="0.0.0.0", port=port, log_level="info")
