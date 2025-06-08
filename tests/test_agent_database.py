#!/usr/bin/env python3
"""
Tests for agent task functionality in the unified database.
"""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database_models import (
    Agent,
    AgentStatus,
    AgentTask,
    TaskPriority,
    TaskSource,
    TaskStatus,
)
from src.unified_database import UnifiedDatabaseManager


@pytest_asyncio.fixture
async def test_db():
    """Create a test database instance for agent functionality"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite+aiosqlite:///{tmp.name}"

    db = UnifiedDatabaseManager(db_url)
    await db.init_database()

    yield db

    await db.close()

    try:
        os.unlink(tmp.name)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_register_agent(test_db):
    """Test registering an agent"""
    agent_id = "test-agent-1"
    agent_info = {
        "name": "Test Agent",
        "roles": ["engineering"],
        "capabilities": ["code_analysis", "bug_fixing"],
        "version": "1.0.0",
        "max_concurrent_tasks": 2,
    }

    # Register agent
    await test_db.register_agent(agent_id, agent_info)

    # Verify agent was registered
    async with test_db.get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()

        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.roles == ["engineering"]
        assert agent.capabilities == ["code_analysis", "bug_fixing"]
        assert agent.version == "1.0.0"
        assert agent.status == AgentStatus.READY
        assert agent.max_concurrent_tasks == 2


@pytest.mark.asyncio
async def test_register_agent_update_existing(test_db):
    """Test updating an existing agent registration"""
    agent_id = "test-agent-2"

    # Initial registration
    initial_info = {
        "name": "Test Agent",
        "roles": ["product"],
        "capabilities": ["analysis"],
        "version": "1.0.0",
    }
    await test_db.register_agent(agent_id, initial_info)

    # Update registration
    updated_info = {
        "name": "Updated Test Agent",
        "roles": ["product", "engineering"],
        "capabilities": ["analysis", "implementation"],
        "version": "1.1.0",
    }
    await test_db.register_agent(agent_id, updated_info)

    # Verify agent was updated
    async with test_db.get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one_or_none()

        assert agent is not None
        assert agent.roles == ["product", "engineering"]
        assert agent.capabilities == ["analysis", "implementation"]
        assert agent.version == "1.1.0"


@pytest.mark.asyncio
async def test_create_agent_task(test_db):
    """Test creating agent tasks"""
    async with test_db.get_session() as session:
        # Create a test agent task
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="code_analysis",
            assigned_role="engineering",
            payload={"files": ["src/test.py"]},
            context={"repository": "test-repo"},
            priority=TaskPriority.HIGH,
            source=TaskSource.API,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        assert task.id is not None
        assert task.task_type == "code_analysis"
        assert task.assigned_role == "engineering"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_tasks_for_role(test_db):
    """Test getting tasks assigned to a specific role"""
    async with test_db.get_session() as session:
        # Create tasks for different roles
        engineering_task = AgentTask(
            id=uuid.uuid4(),
            task_type="bug_fix",
            assigned_role="engineering",
            payload={"issue": "memory leak"},
            priority=TaskPriority.HIGH,
            source=TaskSource.WEBHOOK,
            status=TaskStatus.PENDING,
        )

        product_task = AgentTask(
            id=uuid.uuid4(),
            task_type="requirements_analysis",
            assigned_role="product",
            payload={"feature": "user dashboard"},
            priority=TaskPriority.NORMAL,
            source=TaskSource.API,
            status=TaskStatus.PENDING,
        )

        completed_engineering_task = AgentTask(
            id=uuid.uuid4(),
            task_type="code_review",
            assigned_role="engineering",
            payload={"pr": "123"},
            priority=TaskPriority.LOW,
            source=TaskSource.WEBHOOK,
            status=TaskStatus.COMPLETED,
        )

        session.add_all(
            [engineering_task, product_task, completed_engineering_task]
        )
        await session.commit()

    # Get engineering tasks
    engineering_tasks = await test_db.get_tasks_for_role(
        "engineering", limit=10
    )
    assert len(engineering_tasks) == 1  # Only pending engineering task
    assert engineering_tasks[0].task_type == "bug_fix"
    assert engineering_tasks[0].priority == TaskPriority.HIGH

    # Get product tasks
    product_tasks = await test_db.get_tasks_for_role("product", limit=10)
    assert len(product_tasks) == 1
    assert product_tasks[0].task_type == "requirements_analysis"

    # Get tasks for non-existent role
    qa_tasks = await test_db.get_tasks_for_role("qa", limit=10)
    assert len(qa_tasks) == 0


@pytest.mark.asyncio
async def test_claim_agent_task(test_db):
    """Test atomic task claiming"""
    agent_id = "test-agent-claimer"

    async with test_db.get_session() as session:
        # Create a pending task
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="test_task",
            assigned_role="engineering",
            payload={"test": "data"},
            priority=TaskPriority.NORMAL,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    # Claim the task
    claim_result = await test_db.claim_agent_task(task_id, agent_id)
    assert claim_result is True

    # Verify task was claimed
    claimed_task = await test_db.get_agent_task(task_id)
    assert claimed_task is not None
    assert claimed_task.status == TaskStatus.RUNNING
    assert claimed_task.agent_id == agent_id
    assert claimed_task.started_at is not None

    # Try to claim the same task again (should fail)
    another_agent = "another-agent"
    second_claim = await test_db.claim_agent_task(task_id, another_agent)
    assert second_claim is False

    # Verify task is still claimed by original agent
    task_after_second_claim = await test_db.get_agent_task(task_id)
    assert task_after_second_claim.agent_id == agent_id


@pytest.mark.asyncio
async def test_claim_nonexistent_task(test_db):
    """Test claiming a non-existent task"""
    fake_task_id = str(uuid.uuid4())
    result = await test_db.claim_agent_task(fake_task_id, "test-agent")
    assert result is False


@pytest.mark.asyncio
async def test_get_agent_task(test_db):
    """Test retrieving agent task by ID"""
    async with test_db.get_session() as session:
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="retrieve_test",
            assigned_role="product",
            payload={"data": "test"},
            priority=TaskPriority.LOW,
            source=TaskSource.API,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    # Retrieve the task
    retrieved_task = await test_db.get_agent_task(task_id)
    assert retrieved_task is not None
    assert retrieved_task.id == task_id
    assert retrieved_task.task_type == "retrieve_test"
    assert retrieved_task.assigned_role == "product"

    # Try to retrieve non-existent task
    fake_id = str(uuid.uuid4())
    non_existent = await test_db.get_agent_task(fake_id)
    assert non_existent is None


@pytest.mark.asyncio
async def test_task_priority_ordering(test_db):
    """Test that tasks are returned in priority order"""
    async with test_db.get_session() as session:
        # Create tasks with different priorities
        low_task = AgentTask(
            id=uuid.uuid4(),
            task_type="low_priority",
            assigned_role="engineering",
            payload={},
            priority=TaskPriority.LOW,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )

        high_task = AgentTask(
            id=uuid.uuid4(),
            task_type="high_priority",
            assigned_role="engineering",
            payload={},
            priority=TaskPriority.HIGH,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )

        urgent_task = AgentTask(
            id=uuid.uuid4(),
            task_type="urgent_priority",
            assigned_role="engineering",
            payload={},
            priority=TaskPriority.URGENT,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )

        normal_task = AgentTask(
            id=uuid.uuid4(),
            task_type="normal_priority",
            assigned_role="engineering",
            payload={},
            priority=TaskPriority.NORMAL,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )

        # Add in random order
        session.add_all([low_task, high_task, urgent_task, normal_task])
        await session.commit()

    # Get tasks for engineering role
    tasks = await test_db.get_tasks_for_role("engineering", limit=10)

    # Verify priority ordering (URGENT > HIGH > NORMAL > LOW)
    assert len(tasks) == 4

    # Extract priorities and sort them to verify correct ordering
    priorities = [task.priority for task in tasks]
    expected_order = [
        TaskPriority.URGENT,
        TaskPriority.HIGH,
        TaskPriority.NORMAL,
        TaskPriority.LOW,
    ]

    # Check that we have all expected priorities
    assert set(priorities) == set(expected_order)

    # Verify that tasks are in priority order (descending)
    for i in range(len(tasks) - 1):
        assert tasks[i].priority.value >= tasks[i + 1].priority.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
