#!/usr/bin/env python3
"""
FastMCP Server - Lightweight MCP server for Summit
Communicates with Summit app via HTTP API instead of direct database access
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(
    name="Summit MCP Server",
)

# Initialize startup time when module loads
mcp.start_time = datetime.now(timezone.utc)

# Summit app configuration
SUMMIT_API_BASE = os.environ.get("SUMMIT_API_BASE", "http://localhost:8000")
SUMMIT_API_TIMEOUT = float(os.environ.get("SUMMIT_API_TIMEOUT", "30.0"))


# Pydantic models for request validation
class GetNextTaskRequest(BaseModel):
    agent_id: str = Field(..., description="ID of the agent requesting a task")
    role: str = Field(..., description="Role the agent wants to fulfill")


class CompleteTaskRequest(BaseModel):
    task_id: str = Field(..., description="ID of the task being completed")
    agent_id: str = Field(
        ..., description="ID of the agent completing the task"
    )
    success: bool = Field(
        True, description="Whether the task completed successfully"
    )
    result: Dict[str, Any] = Field(
        default_factory=dict, description="Result data as a dictionary"
    )
    summary: str = Field("", description="Brief summary of work completed")
    files_modified: List[str] = Field(
        default_factory=list, description="List of files modified"
    )
    error_message: str = Field("", description="Error message if task failed")


class RegisterAgentRequest(BaseModel):
    agent_id: str = Field(..., description="Unique identifier for the agent")
    agent_type: str = Field("autonomous", description="Type of agent")
    role: str = Field(..., description="Role of the agent")
    capabilities: List[str] = Field(
        default_factory=list, description="Agent capabilities"
    )
    model: str = Field("unknown", description="Model used by the agent")
    system_info: Dict[str, Any] = Field(
        default_factory=dict, description="System information"
    )


class TaskResponse(BaseModel):
    """Schema for task response data"""

    id: str
    type: str
    priority: int
    role: str
    status: str
    description: str
    details: Dict[str, Any]
    context: Dict[str, Any]
    created_at: Optional[str] = None
    claimed_at: Optional[str] = None


# HTTP client for Summit API communication
async def get_http_client() -> httpx.AsyncClient:
    """Get HTTP client for Summit API communication"""
    return httpx.AsyncClient(
        base_url=SUMMIT_API_BASE,
        timeout=SUMMIT_API_TIMEOUT,
        headers={"Content-Type": "application/json"},
    )


# Resources - provide static and dynamic data to clients
@mcp.resource("resource://system-info")
async def system_info() -> Dict[str, Any]:
    """Provide system information about the Summit platform"""
    return {
        "name": "Summit MCP Server",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "start_time": (
            mcp.start_time.isoformat() if hasattr(mcp, "start_time") else None
        ),
        "uptime_seconds": (
            (datetime.now(timezone.utc) - mcp.start_time).total_seconds()
            if hasattr(mcp, "start_time")
            else 0
        ),
        "summit_api_base": SUMMIT_API_BASE,
    }


@mcp.resource("resource://docs/agent-guide")
async def agent_guide() -> str:
    """Provide documentation for agents interacting with the Summit platform"""
    return """# Summit Agent Guide

## Available Tools

* `summit_get_next_task`: Request a new task from the platform
* `summit_complete_task`: Mark a task as completed or failed
* `summit_register_agent`: Register a new agent with the platform

## Task Workflow

1. Register your agent using `summit_register_agent`
2. Request a task with `summit_get_next_task`
3. Perform the requested work
4. Report completion with `summit_complete_task`
5. Repeat steps 2-4

For more information, visit our documentation at https://summit-ai.example.com/docs
"""


# Task management tools
@mcp.tool()
async def summit_get_next_task(
    request: GetNextTaskRequest, ctx: Context
) -> Dict[str, Any]:
    """
    Get the next available task for an agent based on its role

    Args:
        request: Contains agent_id and role information
        ctx: MCP context for logging and client interaction

    Returns:
        Task information or status message
    """
    logger.info(
        f"Agent {request.agent_id} requesting task for role {request.role}"
    )
    await ctx.info(f"Processing task request for role: {request.role}")

    try:
        # Report progress to client
        await ctx.report_progress(0.1, "Connecting to Summit API")

        async with await get_http_client() as client:
            # Make request to Summit API
            await ctx.report_progress(0.4, "Searching for available tasks")

            response = await client.post(
                "/api/tasks/next",
                json={
                    "agent_id": request.agent_id,
                    "role": request.role,
                },
            )

            await ctx.report_progress(0.8, "Processing results")

            if response.status_code == 200:
                data = response.json()
                await ctx.report_progress(1.0, "Task assigned")
                await ctx.info(f"Assigned task to agent {request.agent_id}")
                return {"status": "success", "task": data}
            elif response.status_code == 404:
                await ctx.info(
                    f"No available tasks found for role: {request.role}"
                )
                return {
                    "status": "no_tasks",
                    "message": f"No available tasks found for role: {request.role}",
                }
            else:
                error_msg = f"Summit API error: {response.status_code}"
                await ctx.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                }

    except Exception as e:
        logger.error(f"Error getting next task: {str(e)}", exc_info=True)
        await ctx.error(f"Error getting next task: {str(e)}")
        return {
            "status": "error",
            "message": f"Error getting next task: {str(e)}",
        }


@mcp.tool()
async def summit_complete_task(
    request: CompleteTaskRequest, ctx: Context
) -> Dict[str, Any]:
    """
    Mark a task as completed or failed

    Args:
        request: Contains task_id, agent_id, success status, and other completion data
        ctx: MCP context for logging and client interaction

    Returns:
        Status message
    """
    logger.info(f"Agent {request.agent_id} completing task {request.task_id}")

    try:
        # Report progress to client
        await ctx.report_progress(0.2, "Processing task completion request")

        # Update client with the files being processed
        if request.files_modified:
            await ctx.info(
                f"Task modified {len(request.files_modified)} files: {', '.join(request.files_modified[:5])}"
            )

        async with await get_http_client() as client:
            # Complete the task via Summit API
            await ctx.report_progress(
                0.5, "Updating task status via Summit API"
            )

            response = await client.post(
                f"/api/tasks/{request.task_id}/complete",
                json={
                    "agent_id": request.agent_id,
                    "success": request.success,
                    "result": request.result,
                    "summary": request.summary,
                    "files_modified": request.files_modified,
                    "error_message": request.error_message,
                },
            )

            await ctx.report_progress(0.9, "Finalizing task status")

            if response.status_code == 200:
                await ctx.report_progress(1.0, "Task status updated")

                if request.success:
                    await ctx.info(
                        f"Task {request.task_id} completed successfully"
                    )
                    return {
                        "status": "success",
                        "message": f"Task {request.task_id} completed successfully",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    await ctx.warning(
                        f"Task {request.task_id} failed: {request.error_message}"
                    )
                    return {
                        "status": "error",
                        "message": f"Task {request.task_id} failed: {request.error_message}",
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                    }
            else:
                error_msg = f"Summit API error: {response.status_code}"
                await ctx.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                }

    except Exception as e:
        logger.error(f"Error completing task: {str(e)}", exc_info=True)
        await ctx.error(f"Error completing task: {str(e)}")
        return {
            "status": "error",
            "message": f"Error completing task: {str(e)}",
        }


@mcp.tool()
async def summit_register_agent(
    request: RegisterAgentRequest, ctx: Context
) -> Dict[str, Any]:
    """
    Register an agent with the platform

    Args:
        request: Contains agent_id, role, capabilities, and other registration data
        ctx: MCP context for logging and client interaction

    Returns:
        Registration status and agent information
    """
    logger.info(
        f"Registering agent {request.agent_id} with role {request.role}"
    )

    try:
        # Report progress to client
        await ctx.report_progress(0.3, "Processing registration request")

        async with await get_http_client() as client:
            # Register the agent via Summit API
            await ctx.report_progress(0.6, "Registering agent via Summit API")

            response = await client.post(
                "/api/agents/register",
                json={
                    "agent_id": request.agent_id,
                    "agent_type": request.agent_type,
                    "role": request.role,
                    "capabilities": request.capabilities,
                    "model": request.model,
                    "system_info": request.system_info,
                },
            )

            await ctx.report_progress(0.9, "Finalizing registration")

            if response.status_code == 200:
                data = response.json()
                await ctx.report_progress(1.0, "Registration complete")
                await ctx.info(
                    f"Agent {request.agent_id} registered successfully"
                )

                return {
                    "status": "success",
                    "message": f"Agent {request.agent_id} registered successfully",
                    "agent": data,
                }
            else:
                error_msg = f"Summit API error: {response.status_code}"
                await ctx.error(error_msg)
                return {
                    "status": "error",
                    "message": error_msg,
                }

    except Exception as e:
        logger.error(f"Error registering agent: {str(e)}", exc_info=True)
        await ctx.error(f"Error registering agent: {str(e)}")
        return {
            "status": "error",
            "message": f"Error registering agent: {str(e)}",
        }


# Health check tool
@mcp.tool()
async def summit_health(ctx: Context) -> Dict[str, Any]:
    """
    Check the health of the Summit MCP server and Summit API

    Args:
        ctx: MCP context for logging and client interaction

    Returns:
        Health status information
    """
    # Check Summit API connectivity
    summit_api_status = "unknown"
    try:
        async with await get_http_client() as client:
            response = await client.get("/api/health")
            if response.status_code == 200:
                summit_api_status = "connected"
            else:
                summit_api_status = f"error_{response.status_code}"
    except Exception as e:
        summit_api_status = f"error: {str(e)}"

    health_info = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summit_api": summit_api_status,
        "summit_api_base": SUMMIT_API_BASE,
        "uptime": (
            str(datetime.now(timezone.utc) - mcp.start_time)
            if hasattr(mcp, "start_time")
            else "unknown"
        ),
    }

    await ctx.info("Health check completed")
    return health_info


async def startup_initialization():
    """Initialize the server on startup"""
    logger.info("FastMCP server starting...")
    logger.info(f"Summit API base URL: {SUMMIT_API_BASE}")
    logger.info("FastMCP server started successfully")


if __name__ == "__main__":
    # Determine transport method from environment
    transport = os.environ.get("MCP_TRANSPORT", "sse").lower()

    # Get host and port from environment
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    # Log startup information
    logger.info(f"Starting Summit FastMCP server with transport: {transport}")
    logger.info(f"Server will bind to: {host}:{port}")

    # Initialize server
    import asyncio

    asyncio.run(startup_initialization())

    # Run the main server in blocking mode with the specified transport
    try:
        mcp.run(transport=transport, host=host, port=port)
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logger.info("Server shutdown requested by keyboard interrupt")
    except Exception as e:
        logger.error(f"Error running FastMCP server: {str(e)}", exc_info=True)
