#!/usr/bin/env python3
"""
Tests for the simplified MCP tools interface.
Focuses on the two core operations:
1. summit_start_task
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
@patch("unified_database.get_database")
async def test_summit_start_task(mock_unified_db, mock_get_db, mock_db):
    """Test the summit_start_task tool"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call the tool handler
    result = await handle_call_tool(
        "summit_start_task", {"task_id": task.id, "agent_id": "test-agent"}
    )

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    # Check that database was called correctly
    db.get_agent_task.assert_called_once()
    db.update_agent_task.assert_called_once()


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_summit_start_task_missing_params(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_start_task tool with missing parameters"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call without required parameters should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_start_task", {})

    # Call with only task_id should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_start_task", {"task_id": task.id})

    # Call with only agent_id should raise ValueError
    with pytest.raises(ValueError):
        await handle_call_tool("summit_start_task", {"agent_id": "test-agent"})


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_summit_start_task_nonexistent(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_start_task tool with a task that doesn't exist"""
    db, _ = mock_db
    # Configure get_agent_task to return None (task not found)
    db.get_agent_task.return_value = None
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call the tool handler
    result = await handle_call_tool(
        "summit_start_task",
        {"task_id": "nonexistent-task", "agent_id": "test-agent"},
    )

    # Verify the result indicates task not found or some error
    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_summit_complete_task_success(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with success=True"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call arguments
    args = {
        "task_id": task.id,
        "agent_id": "test-agent",
        "success": True,
        "summary": "Task completed successfully",
        "files_modified": ["file1.py", "file2.py"],
        "result": {"detail": "Additional information"},
    }

    # Call the tool handler
    result = await handle_call_tool("summit_complete_task", args)

    # Verify the result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)

    # Verify the database was called correctly
    db.update_agent_task.assert_called_once()
    call_args = db.update_agent_task.call_args[0]
    assert call_args[0] == task.id

    # Check the updates
    updates = db.update_agent_task.call_args[0][1]
    assert updates["status"] == TaskStatus.COMPLETED
    assert updates["agent_id"] == "test-agent"
    assert "completed_at" in updates
    assert "result" in updates
    assert updates["result"]["summary"] == "Task completed successfully"
    assert updates["result"]["files_modified"] == ["file1.py", "file2.py"]
    assert updates["result"]["detail"] == "Additional information"


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_summit_complete_task_failure(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with success=False"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call arguments
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

    # Verify the database was called correctly
    db.update_agent_task.assert_called_once()

    # Check the updates
    updates = db.update_agent_task.call_args[0][1]
    assert updates["status"] == TaskStatus.FAILED
    assert updates["error"] == "Task failed due to XYZ"
    assert "completed_at" in updates


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_summit_complete_task_missing_params(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with missing parameters"""
    db, task = mock_db
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

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
@patch("unified_database.get_database")
async def test_summit_complete_task_nonexistent(
    mock_unified_db, mock_get_db, mock_db
):
    """Test the summit_complete_task tool with a task that doesn't exist"""
    db, _ = mock_db
    # Configure update_agent_task to return None (task not found/updated)
    db.update_agent_task.return_value = None
    mock_get_db.return_value = db
    mock_unified_db.return_value = db

    # Call the tool handler
    result = await handle_call_tool(
        "summit_complete_task",
        {
            "task_id": "nonexistent-task",
            "agent_id": "test-agent",
            "success": True,
        },
    )

    # Verify the result indicates task not found or an error
    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_tools_available_in_list(mock_unified_db, mock_get_db):
    """Test that our core tools are available in the tool list"""
    # Get the list of available tools
    tools = await handle_list_tools()

    # Extract tool names
    tool_names = [tool.name for tool in tools]

    # Verify our core tools are available
    assert "summit_start_task" in tool_names
    assert "summit_complete_task" in tool_names

    # Find the summit_complete_task tool
    complete_task_tool = next(
        tool for tool in tools if tool.name == "summit_complete_task"
    )

    # Verify the required parameters
    required_props = complete_task_tool.inputSchema["required"]
    assert "task_id" in required_props
    assert "agent_id" in required_props


@pytest.mark.asyncio
@patch("summit.get_database")
@patch("unified_database.get_database")
async def test_invalid_tool_name(mock_unified_db, mock_get_db):
    """Test calling a non-existent tool"""
    with pytest.raises(ValueError, match="Summit doesn't know tool"):
        await handle_call_tool("invalid_tool_name", {})
