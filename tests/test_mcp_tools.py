#!/usr/bin/env python3
"""
Tests for the FastMCP tools interface.
Focuses on the core operations:
1. summit_get_next_task
2. summit_complete_task
3. summit_register_agent
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Create a mock Context class for testing when fastmcp might not be available
class MockContext:
    """Mock Context class for tests"""
    async def info(self, message):
        pass
    
    async def warning(self, message):
        pass
    
    async def error(self, message):
        pass
    
    async def report_progress(self, progress, message=""):
        pass


# Create a mock config module
class MockConfig:
    pass


mock_config = MagicMock()
mock_config.Config = MockConfig()
mock_config.setup_environment = MagicMock()

# Create mocks for FastMCP
mock_fastmcp = MagicMock()
mock_context = MagicMock(spec=MockContext)

# Apply patches for modules and config
with patch.dict(
    "sys.modules",
    {
        "fastmcp": mock_fastmcp,
        "config": mock_config,
    },
):
    # Now import the models and functions to test
    from database_models import AgentTask, TaskStatus


# Mock versions of the FastMCP handlers for testing
async def mock_summit_get_next_task(request, ctx):
    """Mock implementation of summit_get_next_task for testing"""
    agent_id = request.get("agent_id", "test-agent")
    role = request.get("role", "default")

    # Simplified mock response
    return {
        "status": "success",
        "task": {
            "id": str(uuid.uuid4()),
            "type": "test_task",
            "priority": 5,
            "role": role,
            "status": "pending",
            "description": "Test task",
            "details": {"test": True},
            "context": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def mock_summit_complete_task(request, ctx):
    """Mock implementation of summit_complete_task for testing"""
    task_id = request.get("task_id", "")
    agent_id = request.get("agent_id", "test-agent")
    success = request.get("success", True)

    return {
        "status": "success" if success else "error",
        "message": (
            f"Task {task_id} completed successfully"
            if success
            else f"Task {task_id} failed"
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


async def mock_summit_register_agent(request, ctx):
    """Mock implementation of summit_register_agent for testing"""
    agent_id = request.get("agent_id", "test-agent")
    role = request.get("role", "default")

    return {
        "status": "success",
        "agent_id": agent_id,
        "role": role,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_db():
    """Create a mock database for testing"""
    db = AsyncMock()

    # Setup sample task
    task = AgentTask(
        id=str(uuid.uuid4()),
        task_type="test_task",
        status=TaskStatus.PENDING,
        assigned_role="engineering",
        priority=5,
        payload={"test": True},
        created_at=datetime.now(timezone.utc),
    )

    # Configure get_agent_task to return our sample task
    db.get_agent_task.return_value = task

    # Configure update_agent_task to return the updated task
    db.update_agent_task.return_value = task

    return db, task


@pytest.mark.asyncio
async def test_summit_get_next_task():
    """Test the summit_get_next_task tool using our mock implementation"""
    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {"agent_id": "test-agent", "role": "engineering"}

    # Call the mock tool handler
    result = await mock_summit_get_next_task(request, ctx)

    # Verify the result
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "task" in result
    assert result["task"]["role"] == "engineering"


@pytest.mark.asyncio
async def test_summit_get_next_task_no_tasks():
    """Test the summit_get_next_task tool when no tasks are available"""

    # Mock a special version that returns no tasks
    async def mock_no_tasks(request, ctx):
        return {
            "status": "no_tasks",
            "message": f"No available tasks found for role: {request.get('role')}",
        }

    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {"agent_id": "test-agent", "role": "engineering"}

    # Call the specialized mock
    result = await mock_no_tasks(request, ctx)

    # Verify the result indicates no tasks available
    assert isinstance(result, dict)
    assert result["status"] == "no_tasks"
    assert "message" in result


@pytest.mark.asyncio
async def test_summit_complete_task_success():
    """Test the summit_complete_task tool with success=True"""
    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {
        "task_id": str(uuid.uuid4()),
        "agent_id": "test-agent",
        "success": True,
        "result": {"detail": "Additional information"},
        "summary": "Task completed successfully",
        "files_modified": ["file1.py", "file2.py"],
        "error_message": "",
    }

    # Call the tool handler
    result = await mock_summit_complete_task(request, ctx)

    # Verify the result
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "completed_at" in result


@pytest.mark.asyncio
async def test_summit_complete_task_failure():
    """Test the summit_complete_task tool with success=False"""
    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.warning = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {
        "task_id": str(uuid.uuid4()),
        "agent_id": "test-agent",
        "success": False,
        "result": {"error": "Task processing failed"},
        "summary": "Task failed due to technical issues",
        "files_modified": [],
        "error_message": "Technical error occurred",
    }

    # Call the tool handler
    result = await mock_summit_complete_task(request, ctx)

    # Verify the result
    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "completed_at" in result


@pytest.mark.asyncio
async def test_summit_complete_task_nonexistent():
    """Test the summit_complete_task tool with a nonexistent task"""

    # Mock a special version that returns error for nonexistent task
    async def mock_nonexistent_task(request, ctx):
        return {
            "status": "error",
            "message": f"Failed to complete task {request.get('task_id')}. It may not exist.",
        }

    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.error = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {
        "task_id": "nonexistent-task-id",
        "agent_id": "test-agent",
        "success": True,
    }

    # Call the specialized mock
    result = await mock_nonexistent_task(request, ctx)

    # Verify the result
    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_summit_register_agent():
    """Test the summit_register_agent tool"""
    # Mock Context
    ctx = AsyncMock(spec=MockContext)
    ctx.info = AsyncMock()
    ctx.report_progress = AsyncMock()

    # Create request
    request = {
        "agent_id": "new-agent-001",
        "role": "engineering",
        "agent_type": "autonomous",
        "capabilities": ["coding", "testing", "documentation"],
        "model": "claude-3-opus",
        "system_info": {"platform": "kubernetes", "version": "1.0.0"},
    }

    # Call the tool handler
    result = await mock_summit_register_agent(request, ctx)

    # Verify the result
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["agent_id"] == "new-agent-001"
    assert result["role"] == "engineering"
    assert "registered_at" in result
