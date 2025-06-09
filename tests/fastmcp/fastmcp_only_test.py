#!/usr/bin/env python3
"""
Standalone FastMCP 2.0 server test
This doesn't rely on external modules and can be used to verify the FastMCP 2.0 integration
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from fastmcp import Context, FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a FastMCP server
mcp = FastMCP(
    name="Summit Standalone Test Server",
    description="Test server for FastMCP 2.0 integration",
)


# Mock database - in memory structure
class MockDatabase:
    """Mock database for testing"""

    def __init__(self):
        self.agents = []
        self.tasks = []
        self.initialized = False

    async def init_database(self):
        """Initialize the database"""
        self.initialized = True
        logger.info("Mock database initialized")
        return True

    async def get_all_agents(self):
        """Get all agents"""
        return self.agents

    async def register_agent(
        self, agent_id, agent_type, role, capabilities, model, system_info
    ):
        """Register an agent"""
        agent = {
            "id": agent_id,
            "type": agent_type,
            "role": role,
            "capabilities": capabilities,
            "model": model,
            "system_info": system_info,
            "registered_at": datetime.utcnow().isoformat(),
        }
        self.agents.append(agent)
        logger.info(f"Registered agent {agent_id} with role {role}")
        return agent

    async def get_next_available_task(self, agent_id, roles, limit=1):
        """Get next available task"""
        available_tasks = [
            task
            for task in self.tasks
            if task["status"] == "pending" and task["assigned_role"] in roles
        ]

        if not available_tasks:
            return []

        # Return first available task and mark as claimed
        task = available_tasks[0]
        task["status"] = "claimed"
        task["claimed_by"] = agent_id
        task["claimed_at"] = datetime.utcnow().isoformat()

        return [task]

    async def complete_task(self, task_id, agent_id, success, result, error_message=""):
        """Complete a task"""
        for task in self.tasks:
            if task["id"] == task_id and task["claimed_by"] == agent_id:
                task["status"] = "completed" if success else "failed"
                task["result"] = result
                task["error_message"] = error_message
                task["completed_at"] = datetime.utcnow().isoformat()
                return True
        return False

    async def create_task(
        self, task_type, priority, assigned_role, payload, context=None
    ):
        """Create a new task"""
        task_id = f"task-{len(self.tasks) + 1}"
        task = {
            "id": task_id,
            "task_type": task_type,
            "priority": priority,
            "assigned_role": assigned_role,
            "status": "pending",
            "payload": payload,
            "context": context or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        self.tasks.append(task)
        return task


# Create mock database
mock_db = MockDatabase()


# Mock task queue
class MockTaskQueue:
    """Mock task queue that delegates to database"""

    def __init__(self, db):
        self.db = db

    async def get_next_available_task(self, agent_id, roles, limit=1):
        """Get next available task from database"""
        return await self.db.get_next_available_task(agent_id, roles, limit)

    async def complete_task(self, task_id, agent_id, success, result, error_message=""):
        """Complete a task in database"""
        return await self.db.complete_task(
            task_id, agent_id, success, result, error_message
        )

    async def create_task(
        self, task_type, priority, assigned_role, payload, context=None
    ):
        """Create a task in database"""
        return await self.db.create_task(
            task_type, priority, assigned_role, payload, context
        )


# Create mock task queue
mock_task_queue = MockTaskQueue(mock_db)


# Mock functions to return our mock instances
async def get_database():
    """Get the database instance"""
    return mock_db


async def get_task_queue_manager():
    """Get the task queue manager"""
    return mock_task_queue


# Add some pre-defined tasks
async def create_test_tasks():
    """Create some test tasks"""
    await mock_task_queue.create_task(
        task_type="code_review",
        priority="high",
        assigned_role="engineering",
        payload={
            "description": "Review pull request for FastMCP 2.0 migration",
            "pr_number": 123,
            "repository": "summit",
        },
    )
    await mock_task_queue.create_task(
        task_type="bug_fix",
        priority="medium",
        assigned_role="development",
        payload={
            "description": "Fix issue with FastMCP resource handling",
            "issue_number": 456,
            "repository": "summit",
        },
    )
    logger.info(f"Created {len(mock_db.tasks)} test tasks")


# Resources
@mcp.resource(uri="resource://system-info")
async def system_info():
    """Provide system information about the server"""
    return {
        "name": "Summit Test Server",
        "version": "2.0.0",
        "environment": "test",
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
async def agent_guide():
    """Provide documentation for agents"""
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
"""


# Simple test tool
@mcp.tool()
async def summit_test(message: str, ctx: Context) -> dict:
    """
    Simple test tool

    Args:
        message: Test message
        ctx: MCP context

    Returns:
        Test result
    """
    await ctx.info(f"Received test message: {message}")
    return {
        "status": "success",
        "message": f"Test successful: {message}",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Initialize server
async def initialize_server():
    """Initialize the server"""
    logger.info("Initializing test server...")

    # Set start time
    mcp.start_time = datetime.utcnow()

    # Initialize database
    await mock_db.init_database()

    # Create test tasks
    await create_test_tasks()

    # Log resources and tools
    resources = await mcp.list_resources()
    logger.info(f"Resources: {[r.uri for r in resources]}")

    tools = await mcp.list_tools()
    logger.info(f"Tools: {[t.name for t in tools]}")

    logger.info("Server initialization complete")


if __name__ == "__main__":
    # Run initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_server())

    # Just run the initialization test without actually starting the server
    # This avoids getting stuck in stdio mode
    logger.info("FastMCP 2.0 initialization test successful")
    logger.info("Server would normally start here (skipped for automated testing)")

    # Print summary
    logger.info("Summary:")
    logger.info(f"- Server name: {mcp.name}")
    logger.info(f"- Resources: {len(loop.run_until_complete(mcp.list_resources()))}")
    logger.info(f"- Tools: {len(loop.run_until_complete(mcp.list_tools()))}")
    logger.info(f"- Mock tasks: {len(mock_db.tasks)}")
    logger.info(f"- Mock agents: {len(mock_db.agents)}")
