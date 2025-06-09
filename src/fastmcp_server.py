#!/usr/bin/env python3
"""
FastMCP Server - Modern MCP server for Summit
Simplified implementation with essential task management endpoints
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from task_queue_manager import get_task_queue_manager
from unified_database import get_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastMCP server with description and metadata
mcp = FastMCP(
    name="Summit MCP Server",
    description="MCP server for Summit task management system",
    version="1.0.0",
)


# Pydantic models for request validation
class GetNextTaskRequest(BaseModel):
    agent_id: str = Field(..., description="ID of the agent requesting a task")
    role: str = Field(..., description="Role the agent wants to fulfill")


class CompleteTaskRequest(BaseModel):
    task_id: str = Field(..., description="ID of the task being completed")
    agent_id: str = Field(..., description="ID of the agent completing the task")
    success: bool = Field(True, description="Whether the task completed successfully")
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


# Resources - provide static and dynamic data to clients
@mcp.resource(uri="resource://system-info")
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
            (datetime.utcnow() - mcp.start_time).total_seconds()
            if hasattr(mcp, "start_time")
            else 0
        ),
    }


@mcp.resource(uri="resource://docs/agent-guide")
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
    # Initialize database if needed
    await initialize_database()

    logger.info(f"Agent {request.agent_id} requesting task for role {request.role}")
    await ctx.info(f"Processing task request for role: {request.role}")

    try:
        # Report progress to client
        await ctx.report_progress(0.1, "Connecting to task queue")

        # Get task queue manager
        task_queue_manager = await get_task_queue_manager()

        # Get tasks available for the agent based on its role
        await ctx.report_progress(0.4, "Searching for available tasks")
        tasks = await task_queue_manager.get_next_available_task(
            agent_id=request.agent_id,
            roles=[request.role],  # Convert to list for compatibility
            limit=1,
        )

        await ctx.report_progress(0.8, "Processing results")

        # No tasks available
        if not tasks:
            await ctx.info(f"No available tasks found for role: {request.role}")
            return {
                "status": "no_tasks",
                "message": f"No available tasks found for role: {request.role}",
            }

        # Return the first task
        task = tasks[0]

        # Format response
        await ctx.report_progress(1.0, "Task assigned")
        await ctx.info(f"Assigned task {task.id} to agent {request.agent_id}")

        # Create structured response
        return {
            "status": "success",
            "task": TaskResponse(
                id=str(task.id),
                type=task.task_type,
                priority=task.priority.value,
                role=task.assigned_role,
                status=task.status.value,
                description=task.payload.get("description", ""),
                details=task.payload,
                context=task.context,
                created_at=(task.created_at.isoformat() if task.created_at else None),
                claimed_at=(task.claimed_at.isoformat() if task.claimed_at else None),
            ).model_dump(),
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
    # Initialize database if needed
    await initialize_database()

    logger.info(f"Agent {request.agent_id} completing task {request.task_id}")

    try:
        # Report progress to client
        await ctx.report_progress(0.2, "Processing task completion request")

        # Get task queue manager
        task_queue_manager = await get_task_queue_manager()

        # Update client with the files being processed
        if request.files_modified:
            await ctx.info(
                f"Task modified {len(request.files_modified)} files: {', '.join(request.files_modified[:5])}"
            )

        # Complete the task
        await ctx.report_progress(0.5, "Updating task status in database")
        completed = await task_queue_manager.complete_task(
            task_id=request.task_id,
            agent_id=request.agent_id,
            success=request.success,
            result=request.result,
            error_message=request.error_message,
        )

        await ctx.report_progress(0.9, "Finalizing task status")

        if not completed:
            await ctx.error(f"Failed to complete task {request.task_id}")
            return {
                "status": "error",
                "message": f"Failed to complete task {request.task_id}. It may not exist or may not be assigned to agent {request.agent_id}.",
            }

        # Format response
        await ctx.report_progress(1.0, "Task status updated")

        if request.success:
            await ctx.info(f"Task {request.task_id} completed successfully")
            return {
                "status": "success",
                "message": f"Task {request.task_id} completed successfully",
                "completed_at": datetime.utcnow().isoformat(),
            }
        else:
            await ctx.warning(f"Task {request.task_id} failed: {request.error_message}")
            return {
                "status": "error",
                "message": f"Task {request.task_id} failed: {request.error_message}",
                "failed_at": datetime.utcnow().isoformat(),
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
    # Initialize database if needed
    await initialize_database()

    logger.info(f"Registering agent {request.agent_id} with role {request.role}")

    try:
        # Report progress to client
        await ctx.report_progress(0.3, "Processing registration request")

        # Get database manager
        db = await get_database()

        # Register the agent
        await ctx.report_progress(0.6, "Registering agent in database")
        agent = await db.register_agent(
            agent_id=request.agent_id,
            agent_type=request.agent_type,
            role=request.role,
            capabilities=request.capabilities,
            model=request.model,
            system_info=request.system_info,
        )

        await ctx.report_progress(0.9, "Finalizing registration")

        if not agent:
            await ctx.error(f"Failed to register agent {request.agent_id}")
            return {
                "status": "error",
                "message": f"Failed to register agent {request.agent_id}",
            }

        await ctx.report_progress(1.0, "Registration complete")
        await ctx.info(f"Agent {request.agent_id} registered successfully")

        # Return structured response
        return {
            "status": "success",
            "message": f"Agent {request.agent_id} registered successfully",
            "agent": {
                "id": agent.id,
                "role": request.role,
                "type": request.agent_type,
                "capabilities": request.capabilities,
                "registered_at": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error registering agent: {str(e)}", exc_info=True)
        await ctx.error(f"Error registering agent: {str(e)}")
        return {
            "status": "error",
            "message": f"Error registering agent: {str(e)}",
        }


# Health check and misc tools
@mcp.tool()
async def summit_health(ctx: Context) -> Dict[str, Any]:
    """
    Check the health of the Summit MCP server

    Args:
        ctx: MCP context for logging and client interaction

    Returns:
        Health status information
    """
    # Initialize database if needed
    await initialize_database()

    # Get database status
    db_status = "unknown"
    try:
        db = await get_database()
        # Simple query to check database connectivity
        await db.get_all_agents()
        db_status = "connected"
    except Exception:
        db_status = "error"

    health_info = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "uptime": (
            str(datetime.utcnow() - mcp.start_time)
            if hasattr(mcp, "start_time")
            else "unknown"
        ),
    }

    await ctx.info("Health check completed")
    return health_info


# Server startup and shutdown event handlers
# Use FastMCP 2.0 lifecycle hooks
# We'll manually initialize services when server starts
mcp.start_time = datetime.utcnow()


# Initialize database on first request
async def initialize_database():
    """Initialize database if not already done"""
    if not hasattr(mcp, "db_initialized"):
        try:
            logger.info("Initializing database...")
            db = await get_database()
            await db.init_database()
            mcp.db_initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            # Continue even if DB initialization fails - may recover later


# Cleanup function for resource shutdown
# Will be called manually at server exit if possible
async def cleanup_resources():
    """Clean up resources"""
    logger.info("Shutting down Summit FastMCP server...")
    from task_queue_manager import close_task_queue_manager
    from unified_database import close_database

    try:
        await close_task_queue_manager()
        await close_database()
        logger.info("Resources cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


async def run_server():
    """Run the FastMCP server with proper setup and cleanup"""
    # Initialize database
    await initialize_database()

    # Log available resources and tools
    resources = await mcp.list_resources()
    logger.info(f"Registered resources: {[r.uri for r in resources]}")

    tools = await mcp.list_tools()
    logger.info(f"Registered tools: {[t.name for t in tools]}")

    logger.info("Server initialized and ready")


if __name__ == "__main__":
    # Determine transport method from environment
    transport = os.environ.get("MCP_TRANSPORT", "sse").lower()

    # Log startup information
    logger.info(f"Starting Summit FastMCP server with transport: {transport}")

    # Run initialization in async mode
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_server())

        # Then run the main server in blocking mode
        # The FastMCP 2.0 server run method is synchronous and blocking
        mcp.run(transport=transport)
    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logger.info("Server shutdown requested")
        try:
            # Run cleanup
            loop.run_until_complete(cleanup_resources())
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    except Exception as e:
        logger.error(f"Error running FastMCP server: {str(e)}", exc_info=True)
    finally:
        loop.close()
