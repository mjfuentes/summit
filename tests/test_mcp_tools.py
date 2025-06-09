#!/usr/bin/env python3
"""
Tests for the simplified MCP tools interface.
Focuses on the two core operations:
1. summit_get_next_task
2. summit_complete_task
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from database_models import AgentTask, TaskStatus

# Import the functions to test from summit.py
from summit import handle_call_tool, handle_list_tools


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
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_get_next_task(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_get_next_task tool"""
    db, task = mock_db
    mock_get_db.return_value = db

    # Mock task queue manager
    task_queue_manager = AsyncMock()
    task_queue_manager.get_next_available_task.return_value = [task]
    mock_get_task_manager.return_value = task_queue_manager

    # Call the tool handler
    result = await handle_call_tool(
        "summit_get_next_task",
        {"agent_id": "test-agent", "role": "engineering"},
    )

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    response_text = result[0].text
    assert "Task assigned" in response_text

    # Check that task queue manager was called correctly
    task_queue_manager.get_next_available_task.assert_called_once()
    call_args = task_queue_manager.get_next_available_task.call_args[1]
    assert call_args["agent_id"] == "test-agent"
    assert call_args["roles"] == ["engineering"]


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_get_next_task_missing_params(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_get_next_task tool with missing parameters"""
    db, task = mock_db
    mock_get_db.return_value = db

    # Mock task queue manager
    task_queue_manager = AsyncMock()
    mock_get_task_manager.return_value = task_queue_manager

    # Call without required parameters should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_get_next_task", {})

    # Call with only agent_id should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool(
            "summit_get_next_task", {"agent_id": "test-agent"}
        )

    # Call with only role should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_get_next_task", {"role": "engineering"})


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_get_next_task_no_tasks(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_get_next_task tool when no tasks are available"""
    db, _ = mock_db
    # Configure task queue manager to return empty list (no tasks)
    task_queue_manager = AsyncMock()
    task_queue_manager.get_next_available_task.return_value = []
    mock_get_task_manager.return_value = task_queue_manager

    mock_get_db.return_value = db

    # Call the tool handler
    result = await handle_call_tool(
        "summit_get_next_task",
        {"agent_id": "test-agent", "role": "engineering"},
    )

    # Verify the result indicates no tasks available
    assert isinstance(result, list)
    assert len(result) == 1
    response_text = result[0].text
    assert "No available tasks found for role: engineering" in response_text


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_complete_task_success(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with success=True"""
    db, task = mock_db
    mock_get_db.return_value = db

    # Mock task queue manager
    task_queue_manager = AsyncMock()
    task_queue_manager.complete_task.return_value = True
    mock_get_task_manager.return_value = task_queue_manager

    # Call arguments - simplified for new API
    args = {
        "task_id": task.id,
        "agent_id": "test-agent",
        "success": True,
        "result": {"detail": "Additional information"},
    }

    # Call the tool handler
    result = await handle_call_tool("summit_complete_task", args)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    # Verify the task queue manager was called correctly
    task_queue_manager.complete_task.assert_called_once()
    call_kwargs = task_queue_manager.complete_task.call_args[1]
    assert call_kwargs["task_id"] == task.id
    assert call_kwargs["agent_id"] == "test-agent"
    assert call_kwargs["success"] == True  # success


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_complete_task_failure(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with success=False"""
    db, task = mock_db
    mock_get_db.return_value = db

    # Mock task queue manager
    task_queue_manager = AsyncMock()
    task_queue_manager.complete_task.return_value = True
    mock_get_task_manager.return_value = task_queue_manager

    # Call arguments - simplified for new API
    args = {
        "task_id": task.id,
        "agent_id": "test-agent",
        "success": False,
        "error_message": "Task failed due to XYZ",
    }

    # Call the tool handler
    result = await handle_call_tool("summit_complete_task", args)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    # Verify the task queue manager was called correctly
    task_queue_manager.complete_task.assert_called_once()
    call_kwargs = task_queue_manager.complete_task.call_args[1]
    assert call_kwargs["task_id"] == task.id
    assert call_kwargs["agent_id"] == "test-agent"
    assert call_kwargs["success"] == False  # success


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_complete_task_missing_params(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with missing parameters"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_get_task_manager.return_value = AsyncMock()

    # Call without required parameters should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_complete_task", {})

    # Call with only task_id should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_complete_task", {"task_id": task.id})

    # Call with only agent_id should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool(
            "summit_complete_task", {"agent_id": "test-agent"}
        )


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_summit_complete_task_nonexistent(
    mock_get_task_manager, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with a task that doesn't exist"""
    db, _ = mock_db

    # Set up task queue manager to return False (task completion failed)
    task_queue_manager = AsyncMock()
    task_queue_manager.complete_task.return_value = False
    mock_get_task_manager.return_value = task_queue_manager

    mock_get_db.return_value = db

    # Call the tool handler
    result = await handle_call_tool(
        "summit_complete_task",
        {
            "task_id": "nonexistent-task",
            "agent_id": "test-agent",
            "success": True,
        },
    )

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    response_text = result[0].text
    assert "Failed to complete task" in response_text


@pytest.mark.asyncio
async def test_tools_available_in_list():
    """Test that our task tools are listed in the available tools"""
    # Get the list of tools
    tools = await handle_list_tools()

    # Find our task tools
    get_next_task = None
    complete_task = None

    for tool in tools:
        if tool.name == "summit_get_next_task":
            get_next_task = tool
        elif tool.name == "summit_complete_task":
            complete_task = tool

    # Verify get_next_task tool
    assert get_next_task is not None
    assert get_next_task.description
    assert get_next_task.inputSchema
    assert "role" in get_next_task.inputSchema["properties"]
    assert "agent_id" in get_next_task.inputSchema["properties"]

    # Verify complete_task tool
    assert complete_task is not None
    assert complete_task.description
    assert complete_task.inputSchema
    assert "success" in complete_task.inputSchema["properties"]
    assert "agent_id" in complete_task.inputSchema["properties"]
    assert "task_id" in complete_task.inputSchema["properties"]
    assert "result" in complete_task.inputSchema["properties"]


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("summit.get_task_queue_manager")
async def test_invalid_tool_name(mock_get_task_manager, mock_get_db):
    """Test calling a tool that doesn't exist"""
    with pytest.raises(ValueError):
        await handle_call_tool("nonexistent_tool", {})
