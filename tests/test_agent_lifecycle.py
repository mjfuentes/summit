#!/usr/bin/env python3
"""
Tests for the agent lifecycle manager.
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent_lifecycle import AgentLifecycleManager, AgentPodState
from src.agent_roles import AgentRole
from src.database_models import (
    AgentStatus,
    AgentTask,
    TaskPriority,
    TaskSource,
    TaskStatus,
)
from src.unified_database import UnifiedDatabaseManager


@pytest_asyncio.fixture
async def test_db():
    """Create a test database instance"""
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


@pytest_asyncio.fixture
async def lifecycle_manager(test_db):
    """Create an agent lifecycle manager for testing"""
    agent_id = "test-agent-lifecycle"
    role = AgentRole.ENGINEERING

    with tempfile.TemporaryDirectory() as workspace:
        # Set workspace environment variable
        os.environ["WORKSPACE_PATH"] = workspace

        manager = AgentLifecycleManager(agent_id=agent_id, role=role)
        # Mock the database for testing
        manager.db = test_db
        manager.workspace_path = workspace

        # Initialize pod_state for testing
        from src.agent_lifecycle import AgentPodState

        manager.pod_state = AgentPodState(
            agent_id=agent_id,
            role=role,
            status=AgentStatus.READY,
            current_task_id=None,
            filesystem_clean=True,
            last_heartbeat=datetime.utcnow(),
            context_loaded=False,
            pod_name="test-pod",
            workspace_path=workspace,
            environment_variables={},
        )

        yield manager


@pytest.mark.asyncio
async def test_agent_lifecycle_initialization(lifecycle_manager):
    """Test agent lifecycle manager initialization"""
    assert lifecycle_manager.agent_id == "test-agent-lifecycle"
    assert lifecycle_manager.role == AgentRole.ENGINEERING
    assert lifecycle_manager.pod_state.status == AgentStatus.READY
    assert lifecycle_manager.pod_state.filesystem_clean is True
    assert lifecycle_manager.pod_state.context_loaded is False


@pytest.mark.asyncio
async def test_agent_registration(lifecycle_manager):
    """Test agent registration with database"""
    await lifecycle_manager._register_agent()

    # Verify agent was registered in database
    async with lifecycle_manager.db.get_session() as session:
        from sqlalchemy import select

        from src.database_models import Agent

        result = await session.execute(
            select(Agent).where(Agent.id == lifecycle_manager.agent_id)
        )
        agent = result.scalar_one_or_none()

        assert agent is not None
        assert agent.id == "test-agent-lifecycle"
        assert AgentRole.ENGINEERING.value in agent.roles
        assert agent.status == AgentStatus.READY


@pytest.mark.asyncio
async def test_fetch_next_task(lifecycle_manager, test_db):
    """Test fetching next available task"""
    # Create a task for the engineering role
    async with test_db.get_session() as session:
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="code_analysis",
            assigned_role="engineering",
            payload={"files": ["src/test.py"]},
            priority=TaskPriority.HIGH,
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    # Mock the lifecycle manager methods to avoid full initialization
    with patch.object(
        lifecycle_manager, "_register_agent", new_callable=AsyncMock
    ):
        await lifecycle_manager._register_agent()

    # Fetch the task
    fetched_task = await lifecycle_manager._fetch_next_task()

    assert fetched_task is not None
    assert fetched_task.id == task_id
    assert fetched_task.task_type == "code_analysis"
    assert fetched_task.assigned_role == "engineering"


@pytest.mark.asyncio
async def test_fetch_no_tasks_available(lifecycle_manager):
    """Test fetching when no tasks are available"""
    with patch.object(
        lifecycle_manager, "_register_agent", new_callable=AsyncMock
    ):
        await lifecycle_manager._register_agent()

    # Should return None when no tasks available
    fetched_task = await lifecycle_manager._fetch_next_task()
    assert fetched_task is None


@pytest.mark.asyncio
async def test_task_environment_preparation(lifecycle_manager):
    """Test task environment preparation"""
    # Create a mock task
    task = AgentTask(
        id=uuid.uuid4(),
        task_type="test_task",
        assigned_role="engineering",
        payload={"test": "data"},
        context={"repo": "test-repo"},
        priority=TaskPriority.NORMAL,
        source=TaskSource.MANUAL,
        status=TaskStatus.RUNNING,
    )

    # Prepare environment
    await lifecycle_manager._prepare_task_environment(task)

    # Check that environment variables were set
    assert os.environ.get("TASK_ID") == str(task.id)
    assert os.environ.get("TASK_TYPE") == "test_task"

    # Check that task context file was created
    context_file = os.path.join(
        lifecycle_manager.workspace_path, ".current_task.json"
    )
    assert os.path.exists(context_file)

    with open(context_file, "r") as f:
        context_data = json.load(f)
        assert context_data["task_id"] == str(task.id)
        assert context_data["task_type"] == "test_task"
        assert context_data["payload"] == {"test": "data"}


@pytest.mark.asyncio
async def test_task_cleanup(lifecycle_manager):
    """Test task cleanup after execution"""
    task = AgentTask(
        id=uuid.uuid4(),
        task_type="cleanup_test",
        assigned_role="engineering",
        payload={},
        priority=TaskPriority.NORMAL,
        source=TaskSource.MANUAL,
        status=TaskStatus.RUNNING,
    )

    # Create task files that should be cleaned up
    context_file = os.path.join(
        lifecycle_manager.workspace_path, ".current_task.json"
    )
    output_file = os.path.join(
        lifecycle_manager.workspace_path, ".task_output.json"
    )

    with open(context_file, "w") as f:
        json.dump({"task_id": str(task.id)}, f)

    with open(output_file, "w") as f:
        json.dump({"result": "test"}, f)

    # Verify files exist before cleanup
    assert os.path.exists(context_file)
    assert os.path.exists(output_file)

    # Run cleanup
    await lifecycle_manager._cleanup_after_task(task)

    # Verify files were cleaned up
    assert not os.path.exists(context_file)
    assert not os.path.exists(output_file)

    # Verify filesystem is marked as dirty for engineering role
    assert lifecycle_manager.pod_state.filesystem_clean is False


@pytest.mark.asyncio
async def test_filesystem_reset(lifecycle_manager):
    """Test filesystem reset functionality"""
    # Create some test files
    test_file = os.path.join(lifecycle_manager.workspace_path, "test_file.txt")
    with open(test_file, "w") as f:
        f.write("test content")

    # Mark filesystem as dirty
    lifecycle_manager.pod_state.filesystem_clean = False

    # Mock git operations to avoid actual git commands
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        await lifecycle_manager._reset_filesystem()

    # Verify git commands were called
    assert mock_run.call_count >= 1

    # Verify filesystem is marked as clean
    assert lifecycle_manager.pod_state.filesystem_clean is True


@pytest.mark.asyncio
async def test_task_completion_success(lifecycle_manager, test_db):
    """Test successful task completion"""
    # Create a task
    async with test_db.get_session() as session:
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="completion_test",
            assigned_role="engineering",
            payload={"test": "data"},
            priority=TaskPriority.NORMAL,
            source=TaskSource.MANUAL,
            status=TaskStatus.RUNNING,
            agent_id=lifecycle_manager.agent_id,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    # Complete the task successfully
    result_data = {"success": True, "output": "test completed"}
    await lifecycle_manager._complete_task(task, True, result_data, None)

    # Verify task was marked as completed in database
    completed_task = await test_db.get_agent_task(task_id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.result is not None


@pytest.mark.asyncio
async def test_task_completion_failure(lifecycle_manager, test_db):
    """Test failed task completion"""
    # Create a task
    async with test_db.get_session() as session:
        task = AgentTask(
            id=uuid.uuid4(),
            task_type="failure_test",
            assigned_role="engineering",
            payload={"test": "data"},
            priority=TaskPriority.NORMAL,
            source=TaskSource.MANUAL,
            status=TaskStatus.RUNNING,
            agent_id=lifecycle_manager.agent_id,
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    # Complete the task with failure
    error_message = "Task failed due to test error"
    await lifecycle_manager._complete_task(task, False, None, error_message)

    # Verify task was marked as failed in database
    failed_task = await test_db.get_agent_task(task_id)
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.error == error_message


@pytest.mark.asyncio
async def test_agent_status_updates(lifecycle_manager):
    """Test agent status updates"""
    # Mock database operations
    with patch.object(
        lifecycle_manager.db, "update_agent_heartbeat", new_callable=AsyncMock
    ) as mock_update:
        # Update status to busy
        await lifecycle_manager._update_agent_status(AgentStatus.BUSY)
        assert lifecycle_manager.pod_state.status == AgentStatus.BUSY

        # Update status to ready
        await lifecycle_manager._update_agent_status(AgentStatus.READY)
        assert lifecycle_manager.pod_state.status == AgentStatus.READY

        # Update status to error
        await lifecycle_manager._update_agent_status(AgentStatus.ERROR)
        assert lifecycle_manager.pod_state.status == AgentStatus.ERROR

        # Verify database update was called
        assert mock_update.call_count >= 3


@pytest.mark.asyncio
async def test_heartbeat_functionality(lifecycle_manager):
    """Test agent heartbeat functionality"""
    initial_heartbeat = lifecycle_manager.pod_state.last_heartbeat

    with patch.object(
        lifecycle_manager, "_update_agent_status", new_callable=AsyncMock
    ) as mock_update:
        # Simulate time passing beyond heartbeat interval
        from datetime import timedelta

        lifecycle_manager.pod_state.last_heartbeat = (
            datetime.utcnow()
            - timedelta(seconds=lifecycle_manager.heartbeat_interval * 2)
        )

        await lifecycle_manager._send_heartbeat()

        # Verify status update was called
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_generic_task_handling(lifecycle_manager):
    """Test generic task handling"""
    payload = {"action": "test", "data": "sample"}
    context = "test context"

    success, result, error = await lifecycle_manager._handle_generic_task(
        payload, context
    )

    assert success is True
    assert result["task_completed"] is True
    assert result["agent_role"] == AgentRole.ENGINEERING.value
    assert result["payload_processed"] == payload
    assert error is None


@pytest.mark.asyncio
async def test_code_analysis_task_handling(lifecycle_manager):
    """Test code analysis task handling"""
    payload = {"files": ["src/test.py", "src/main.py"]}
    context = "analysis context"

    success, result, error = (
        await lifecycle_manager._handle_code_analysis_task(payload, context)
    )

    assert success is True
    assert result["files_analyzed"] == ["src/test.py", "src/main.py"]
    assert result["agent_role"] == AgentRole.ENGINEERING.value
    assert "issues_found" in result
    assert "recommendations" in result
    assert error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
