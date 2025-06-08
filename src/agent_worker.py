"""
Agent Worker for Summit System
Handles task execution from Cloud Tasks
"""

import asyncio
import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel

from cloud_task_manager import (
    CloudTaskManager,
    TaskPriority,
    TaskStatus,
    task_manager,
)

logger = logging.getLogger(__name__)


class TaskRequest(BaseModel):
    task_id: str
    type: str
    payload: Dict[str, Any]
    priority: int = 2


class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    agent_id: str
    execution_time: float


class AgentWorker:
    """Agent worker that processes tasks from Cloud Tasks"""

    def __init__(self):
        self.agent_id = self._generate_agent_id()
        self.task_manager = task_manager
        self.current_task = None
        self.start_time = datetime.utcnow()

    def _generate_agent_id(self) -> str:
        """Generate unique agent ID"""
        hostname = socket.gethostname()
        pod_name = os.environ.get("HOSTNAME", hostname)
        return f"agent-{pod_name}"

    async def initialize(self):
        """Initialize the agent worker"""
        try:
            # Register with task manager
            await self.task_manager.register_agent(
                self.agent_id,
                {
                    "hostname": socket.gethostname(),
                    "pod_name": os.environ.get("HOSTNAME", "unknown"),
                    "start_time": self.start_time.isoformat(),
                    "capabilities": ["code_analysis", "testing", "linting"],
                },
            )

            logger.info(f"Agent {self.agent_id} initialized and registered")

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

    async def execute_task(self, task_request: TaskRequest) -> TaskResult:
        """Execute a task and return result"""
        start_time = datetime.utcnow()
        task_id = task_request.task_id

        try:
            # Update task status to running
            await self.task_manager.update_task_status(
                task_id, TaskStatus.RUNNING, agent_id=self.agent_id
            )

            # Update agent status
            await self.task_manager.update_agent_status(
                self.agent_id, "busy", current_task=task_id
            )

            self.current_task = task_id
            logger.info(
                f"Agent {self.agent_id} executing task {task_id} of type {task_request.type}"
            )

            # Reset agent state before task execution
            await self._reset_agent_state()

            # Execute the task based on type
            result = await self._execute_task_by_type(task_request)

            # Update task status to completed
            await self.task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                agent_id=self.agent_id,
                result=result,
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Task {task_id} completed successfully in {execution_time:.2f}s"
            )

            return TaskResult(
                task_id=task_id,
                status="completed",
                result=result,
                agent_id=self.agent_id,
                execution_time=execution_time,
            )

        except Exception as e:
            # Update task status to failed
            await self.task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                agent_id=self.agent_id,
                error=str(e),
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            logger.error(
                f"Task {task_id} failed after {execution_time:.2f}s: {e}"
            )

            return TaskResult(
                task_id=task_id,
                status="failed",
                error=str(e),
                agent_id=self.agent_id,
                execution_time=execution_time,
            )

        finally:
            # Reset agent status
            self.current_task = None
            await self.task_manager.update_agent_status(self.agent_id, "ready")

    async def _reset_agent_state(self):
        """Reset agent state before executing a new task"""
        try:
            # Clear any temporary files
            temp_dirs = ["/tmp/summit_*", "/tmp/agent_*"]
            for pattern in temp_dirs:
                os.system(f"rm -rf {pattern}")

            # Reset environment variables if needed
            env_vars_to_reset = ["PYTHONPATH", "SUMMIT_TASK_ID"]
            for var in env_vars_to_reset:
                if var in os.environ:
                    del os.environ[var]

            # Clear any cached modules (if needed)
            # This is more aggressive and might not be needed
            # import sys
            # modules_to_clear = [m for m in sys.modules.keys() if m.startswith('summit_task_')]
            # for module in modules_to_clear:
            #     del sys.modules[module]

            logger.debug(f"Agent {self.agent_id} state reset completed")

        except Exception as e:
            logger.warning(f"Error during state reset: {e}")

    async def _execute_task_by_type(
        self, task_request: TaskRequest
    ) -> Dict[str, Any]:
        """Execute task based on its type"""
        task_type = task_request.type
        payload = task_request.payload

        if task_type == "code_analysis":
            return await self._execute_code_analysis(payload)
        elif task_type == "run_tests":
            return await self._execute_tests(payload)
        elif task_type == "lint_code":
            return await self._execute_linting(payload)
        elif task_type == "pr_review":
            return await self._execute_pr_review(payload)
        elif task_type == "deploy_code":
            return await self._execute_deployment(payload)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _execute_code_analysis(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute code analysis task"""
        # Simulate code analysis
        await asyncio.sleep(2)  # Simulate processing time

        return {
            "analysis_type": "code_quality",
            "files_analyzed": payload.get("files", []),
            "issues_found": 3,
            "complexity_score": 7.2,
            "recommendations": [
                "Reduce function complexity in module X",
                "Add more unit tests for edge cases",
                "Consider refactoring large classes",
            ],
        }

    async def _execute_tests(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test suite"""
        # Simulate test execution
        await asyncio.sleep(5)  # Simulate test time

        return {
            "test_type": "unit_tests",
            "tests_run": 45,
            "tests_passed": 43,
            "tests_failed": 2,
            "coverage_percentage": 78.5,
            "failed_tests": [
                "test_authentication_edge_case",
                "test_database_connection_timeout",
            ],
        }

    async def _execute_linting(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute code linting"""
        # Simulate linting
        await asyncio.sleep(1)  # Simulate linting time

        return {
            "linting_tool": "pylint",
            "files_checked": payload.get("files", []),
            "issues_found": 12,
            "issues_fixed": 8,
            "remaining_issues": [
                "Line too long (85/79) in file.py:42",
                "Unused import in module.py:5",
                "Missing docstring in function",
                "Variable name doesn't conform to snake_case",
            ],
        }

    async def _execute_pr_review(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute PR review"""
        # Simulate PR review
        await asyncio.sleep(3)  # Simulate review time

        return {
            "review_type": "automated_pr_review",
            "pr_number": payload.get("pr_number"),
            "files_reviewed": payload.get("files", []),
            "approval_status": "approved_with_suggestions",
            "comments": [
                "Consider adding error handling in line 45",
                "Great test coverage improvement",
                "Documentation looks good",
            ],
            "security_issues": 0,
            "performance_concerns": 1,
        }

    async def _execute_deployment(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute deployment task"""
        # Simulate deployment
        await asyncio.sleep(10)  # Simulate deployment time

        return {
            "deployment_type": "kubernetes",
            "environment": payload.get("environment", "staging"),
            "status": "success",
            "deployed_version": payload.get("version", "1.0.0"),
            "deployment_url": f"https://{payload.get('environment', 'staging')}.summit.ai",
            "health_check_passed": True,
        }

    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "agent_id": self.agent_id,
            "status": "busy" if self.current_task else "ready",
            "current_task": self.current_task,
            "uptime_seconds": uptime,
            "start_time": self.start_time.isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
        }


# Global agent instance
agent = AgentWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await agent.initialize()
    yield
    # Shutdown
    logger.info(f"Agent {agent.agent_id} shutting down")


# FastAPI app
app = FastAPI(
    title="Summit Agent Worker",
    description="Agent worker for processing Summit tasks",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/execute", response_model=TaskResult)
async def execute_task(
    task_request: TaskRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Execute a task from Cloud Tasks"""
    try:
        # Verify this is from Cloud Tasks (optional security check)
        user_agent = request.headers.get("user-agent", "")
        if not user_agent.startswith("Google-Cloud-Tasks"):
            logger.warning(
                f"Task request from non-Cloud Tasks source: {user_agent}"
            )

        # Execute task
        result = await agent.execute_task(task_request)
        return result

    except Exception as e:
        logger.error(f"Error executing task {task_request.task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        status = await agent.get_health_status()
        return {"status": "healthy", "agent": status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get detailed agent status"""
    try:
        return await agent.get_health_status()
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
async def reset_agent():
    """Reset agent state (for debugging)"""
    try:
        await agent._reset_agent_state()
        return {"status": "reset_complete", "agent_id": agent.agent_id}
    except Exception as e:
        logger.error(f"Agent reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the agent
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "agent_worker:app", host="0.0.0.0", port=port, log_level="info"
    )
