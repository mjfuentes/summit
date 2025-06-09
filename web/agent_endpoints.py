#!/usr/bin/env python3
"""
Agent Endpoints - HTTP endpoints for receiving task assignments from Cloud Tasks
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Optional

from fastapi import (
    APIRouter,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database_models import TaskStatus
from src.task_queue_manager import get_task_queue_manager
from src.unified_database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api")


class TaskAssignment(BaseModel):
    """Task assignment model"""

    task_id: str
    additional_data: Optional[Dict] = None


@router.post("/task")
async def receive_task(
    request: Request,
    x_cloudtasks_taskname: Optional[str] = Header(None),
    x_cloudtasks_taskretrycount: Optional[int] = Header(None),
):
    """
    Receive task assignment from Cloud Tasks

    This endpoint receives task assignments from Cloud Tasks and
    notifies the appropriate agent.
    """
    # Validate Cloud Tasks headers if present
    if x_cloudtasks_taskname:
        logger.info(f"Received task from Cloud Tasks: {x_cloudtasks_taskname}")
        if x_cloudtasks_taskretrycount:
            logger.info(f"Retry count: {x_cloudtasks_taskretrycount}")

    # Parse request body
    try:
        body = await request.json()
        task_id = body.get("task_id")

        if not task_id:
            raise HTTPException(status_code=400, detail="Task ID is required")

        # Get task details from database
        db = await get_database()
        task = await db.get_agent_task(task_id)

        if not task:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found"
            )

        # Verify task is in the correct state
        if task.status != TaskStatus.PENDING:
            logger.warning(
                f"Task {task_id} is not in PENDING state (current: {task.status.name})"
            )
            return {"status": "skipped", "reason": "Task not in PENDING state"}

        # Log the task assignment
        logger.info(
            f"Task {task_id} of type {task.task_type} ready for role {task.assigned_role}"
        )

        # Here you would notify an agent to claim the task
        # This could be via:
        # 1. Agent polling (agents check for tasks regularly)
        # 2. WebSockets for immediate notification
        # 3. Message queue
        # 4. Webhook to agent endpoint

        # For now, just acknowledge receipt
        return {"status": "received", "task_id": task_id}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_app():
    """Create FastAPI application with agent endpoints"""
    app = FastAPI(title="Summit Agent Endpoints")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add router
    app.include_router(router)

    @app.on_event("startup")
    async def startup():
        """Initialize database and task queue manager on startup"""
        try:
            # Initialize database
            await get_database()

            # Initialize task queue manager
            await get_task_queue_manager()

            logger.info("Agent endpoints initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent endpoints: {e}")

    @app.on_event("shutdown")
    async def shutdown():
        """Close database connections on shutdown"""
        # Close database
        from src.unified_database import close_database

        await close_database()

        # Close task queue manager
        from src.task_queue_manager import close_task_queue_manager

        await close_task_queue_manager()

        logger.info("Agent endpoints shut down successfully")

    return app


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or default to 8081
    port = int(os.environ.get("AGENT_ENDPOINT_PORT", 8081))

    # Run server
    uvicorn.run(
        "agent_endpoints:create_app",
        host="0.0.0.0",
        port=port,
        reload=True,
        factory=True,
    )
