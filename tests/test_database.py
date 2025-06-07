#!/usr/bin/env python3
"""
Tests for the database functionality.
"""

# Import database components
import os
import sys
import unittest
import tempfile
from unittest.mock import patch
import sqlite3
import pytest
import pytest_asyncio

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import DatabaseManager, Task


@pytest_asyncio.fixture

async def test_db():

    """Create a test database instance"""

    # Use a temporary database for testing

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:

        db_url = f"sqlite+aiosqlite:///{tmp.name}"



    db = DatabaseManager(db_url)

    await db.init_database()

    yield db

    await db.close()



    # Clean up

    try:

        os.unlink(tmp.name)

    except Exception:

        pass





@pytest.mark.asyncio

async def test_task_creation(test_db):

    """Test creating a task in the database"""

    task_data = {

        "task_id": "test-task-1",

        "task_description": "Test task for database",

        "status": "pending",

        "logs": ["Task created"],

        "is_active": True,

    }



    task = await test_db.create_task(task_data)

    assert task.task_id == "test-task-1"

    assert task.task_description == "Test task for database"

    assert task.status == "pending"

    assert task.is_active is True





@pytest.mark.asyncio

async def test_task_retrieval(test_db):

    """Test retrieving a task from the database"""

    # Create a task firs

    task_data = {

        "task_id": "test-task-2",

        "task_description": "Another test task",

        "status": "running",

        "logs": ["Task started"],

        "is_active": True,

    }



    await test_db.create_task(task_data)



    # Retrieve the task

    retrieved_task = await test_db.get_task("test-task-2")

    assert retrieved_task is not None

    assert retrieved_task.task_id == "test-task-2"

    assert retrieved_task.task_description == "Another test task"

    assert retrieved_task.status == "running"





@pytest.mark.asyncio

async def test_task_update(test_db):

    """Test updating a task in the database"""

    # Create a task firs

    task_data = {

        "task_id": "test-task-3",

        "task_description": "Task to be updated",

        "status": "pending",

        "logs": ["Initial log"],

        "is_active": True,

    }



    await test_db.create_task(task_data)



    # Update the task

    updates = {

        "status": "completed",

        "progress": "Task finished",

        "logs": ["Initial log", "Task completed"],

    }



    updated_task = await test_db.update_task("test-task-3", updates)

    assert updated_task.status == "completed"

    assert updated_task.progress == "Task finished"

    assert len(updated_task.logs) == 2





@pytest.mark.asyncio

async def test_active_tasks_retrieval(test_db):

    """Test retrieving active tasks"""

    # Create some tasks

    for i in range(3):

        task_data = {

            "task_id": f"active-task-{i}",

            "task_description": f"Active task {i}",

            "status": "running",

            "is_active": True,

        }

        await test_db.create_task(task_data)



    # Create an inactive task

    inactive_task_data = {

        "task_id": "inactive-task",

        "task_description": "Inactive task",

        "status": "completed",

        "is_active": False,

    }

    await test_db.create_task(inactive_task_data)



    # Get active tasks

    active_tasks = await test_db.get_active_tasks()

    assert len(active_tasks) == 3

    for task in active_tasks:

        assert task.is_active is True





@pytest.mark.asyncio

async def test_task_statistics(test_db):

    """Test getting task statistics"""

    # Create various tasks

    tasks_data = [

        {"task_id": "stat-1", "status": "pending", "is_active": True},

        {"task_id": "stat-2", "status": "running", "is_active": True},

        {"task_id": "stat-3", "status": "completed", "is_active": False},

        {"task_id": "stat-4", "status": "failed", "is_active": False},

    ]



    for task_data in tasks_data:

        task_data.update(

            {"task_description": "Statistics test task", "logs": []}

        )

        await test_db.create_task(task_data)



    stats = await test_db.get_task_statistics()

    assert stats["total_tasks"] == 4

    assert stats["active_tasks"] == 2

    assert stats["completed_tasks"] == 2

    assert "pending" in stats["status_distribution"]

    assert "running" in stats["status_distribution"]

    assert "completed" in stats["status_distribution"]

    assert "failed" in stats["status_distribution"]





@pytest.mark.asyncio

async def test_task_to_dict(test_db):

    """Test converting task to dictionary"""

    task_data = {

        "task_id": "dict-test",

        "task_description": "Dictionary conversion test",

        "status": "pending",

        "logs": ["Log entry 1", "Log entry 2"],

        "is_active": True,

        "repository_url": "https://github.com/test/repo",

        "timeout_minutes": 30,

    }



    task = await test_db.create_task(task_data)

    task_dict = task.to_dict()



    assert task_dict["task_id"] == "dict-test"

    assert task_dict["task_description"] == "Dictionary conversion test"

    assert task_dict["status"] == "pending"

    assert task_dict["logs"] == ["Log entry 1", "Log entry 2"]

    assert task_dict["is_active"] is True

    assert task_dict["repository_url"] == "https://github.com/test/repo"

    assert task_dict["timeout_minutes"] == 30



    # Check that datetime fields are properly converted to ISO forma

    assert isinstance(task_dict["created_at"], str)

    assert isinstance(task_dict["updated_at"], str)





if __name__ == "__main__":

    pytest.main([__file__, "-v"])

