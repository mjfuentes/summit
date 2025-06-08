"""
Tests for Cloud Tasks integration
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.cloud_task_manager import (
    CloudTaskManager,
    Task,
    TaskPriority,
    TaskStatus,
)


@pytest.fixture
def mock_tasks_client():
    """Mock Google Cloud Tasks client"""
    client = Mock()
    client.queue_path.return_value = (
        "projects/test/locations/us-central1/queues/test-queue"
    )
    client.location_path.return_value = "projects/test/locations/us-central1"
    client.get_queue.return_value = Mock()
    client.create_queue.return_value = Mock()
    client.create_task.return_value = Mock(name="test-task")
    return client


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    client = Mock()

    # Mock collection and document operations
    doc_mock = Mock()
    doc_mock.set = Mock()
    doc_mock.update = Mock()
    doc_mock.get.return_value = Mock(
        exists=True,
        to_dict=lambda: {
            "id": "test-task",
            "type": "test",
            "status": "pending",
            "created_at": datetime.utcnow(),
            "priority": 2,
            "payload": {"test": "data"},
        },
    )

    collection_mock = Mock()
    collection_mock.document.return_value = doc_mock

    client.collection.return_value = collection_mock
    return client


@pytest.fixture
def task_manager(mock_tasks_client, mock_firestore_client):
    """Create CloudTaskManager with mocked clients"""
    manager = CloudTaskManager(
        project_id="test-project",
        location="us-central1",
        queue_name="test-queue",
    )
    manager.tasks_client = mock_tasks_client
    manager.firestore_client = mock_firestore_client
    return manager


class TestCloudTaskManager:
    """Test CloudTaskManager functionality"""

    @pytest.mark.asyncio
    async def test_initialization(self, task_manager):
        """Test task manager initialization"""
        await task_manager.initialize()

        # Verify queue path is set correctly
        assert "test-project" in task_manager.queue_path
        assert "test-queue" in task_manager.queue_path

    @pytest.mark.asyncio
    async def test_submit_task(self, task_manager):
        """Test task submission"""
        task_id = await task_manager.submit_task(
            task_type="test_task",
            payload={"test": "data"},
            priority=TaskPriority.HIGH,
        )

        # Verify task ID is generated
        assert task_id is not None
        assert len(task_id) > 0

        # Verify Firestore document was created
        task_manager.firestore_client.collection.assert_called_with(
            "summit_tasks"
        )

        # Verify Cloud Task was created
        task_manager.tasks_client.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_task_with_delay(self, task_manager):
        """Test task submission with delay"""
        task_id = await task_manager.submit_task(
            task_type="delayed_task",
            payload={"test": "data"},
            delay_seconds=60,
        )

        assert task_id is not None

        # Verify create_task was called with schedule_time
        call_args = task_manager.tasks_client.create_task.call_args
        task_data = call_args[1]["task"]
        assert "schedule_time" in task_data

    @pytest.mark.asyncio
    async def test_get_task_status(self, task_manager):
        """Test getting task status"""
        task = await task_manager.get_task_status("test-task-id")

        assert task is not None
        assert task.id == "test-task"
        assert task.type == "test"
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, task_manager):
        """Test getting status for non-existent task"""
        # Mock document not found
        doc_mock = Mock()
        doc_mock.exists = False
        task_manager.firestore_client.collection().document().get.return_value = (
            doc_mock
        )

        task = await task_manager.get_task_status("non-existent")
        assert task is None

    @pytest.mark.asyncio
    async def test_update_task_status(self, task_manager):
        """Test updating task status"""
        await task_manager.update_task_status(
            task_id="test-task",
            status=TaskStatus.RUNNING,
            agent_id="test-agent",
        )

        # Verify update was called
        task_manager.firestore_client.collection().document().update.assert_called_once()

        # Check update data
        call_args = (
            task_manager.firestore_client.collection()
            .document()
            .update.call_args
        )
        update_data = call_args[0][0]
        assert update_data["status"] == "running"
        assert update_data["agent_id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_register_agent(self, task_manager):
        """Test agent registration"""
        agent_info = {"hostname": "test-host", "capabilities": ["test"]}

        await task_manager.register_agent("test-agent", agent_info)

        # Verify agent document was created
        task_manager.firestore_client.collection.assert_called_with(
            "summit_agents"
        )
        task_manager.firestore_client.collection().document().set.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_agent_status(self, task_manager):
        """Test updating agent status"""
        await task_manager.update_agent_status(
            agent_id="test-agent", status="busy", current_task="test-task"
        )

        # Verify update was called
        task_manager.firestore_client.collection().document().update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, task_manager):
        """Test getting queue statistics"""
        # Mock count queries
        count_result = Mock()
        count_result.get.return_value = [(Mock(value=5),)]

        task_manager.firestore_client.collection().where().count.return_value = (
            count_result
        )

        stats = await task_manager.get_queue_stats()

        assert "queue_name" in stats
        assert "pending" in stats
        assert stats["queue_name"] == "test-queue"

    @pytest.mark.asyncio
    async def test_list_active_agents(self, task_manager):
        """Test listing active agents"""
        # Mock query results
        agent_doc = Mock()
        agent_doc.id = "test-agent"
        agent_doc.to_dict.return_value = {
            "status": "ready",
            "last_seen": datetime.utcnow(),
        }

        task_manager.firestore_client.collection().where().stream.return_value = [
            agent_doc
        ]

        agents = await task_manager.list_active_agents()

        assert len(agents) == 1
        assert agents[0]["agent_id"] == "test-agent"
        assert agents[0]["status"] == "ready"


class TestTaskDataClass:
    """Test Task data class"""

    def test_task_creation(self):
        """Test creating a Task instance"""
        task = Task(id="test-id", type="test-type", payload={"key": "value"})

        assert task.id == "test-id"
        assert task.type == "test-type"
        assert task.payload == {"key": "value"}
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None

    def test_task_post_init(self):
        """Test Task post-initialization"""
        task = Task(id="test-id", type="test-type", payload={})

        # created_at should be set automatically
        assert task.created_at is not None
        assert isinstance(task.created_at, datetime)


class TestTaskEnums:
    """Test task-related enums"""

    def test_task_status_enum(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.TIMEOUT.value == "timeout"

    def test_task_priority_enum(self):
        """Test TaskPriority enum values"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.URGENT.value == 4


@pytest.mark.asyncio
async def test_task_manager_error_handling(task_manager):
    """Test error handling in task manager"""
    # Mock Firestore error
    task_manager.firestore_client.collection.side_effect = Exception(
        "Firestore error"
    )

    with pytest.raises(Exception):
        await task_manager.submit_task("test", {})


@pytest.mark.asyncio
async def test_cleanup_old_tasks(task_manager):
    """Test cleaning up old tasks"""
    # Mock query for old tasks
    old_task_doc = Mock()
    task_manager.firestore_client.collection().where().where().stream.return_value = [
        old_task_doc
    ]

    # Mock batch operations
    batch_mock = Mock()
    task_manager.firestore_client.batch.return_value = batch_mock

    await task_manager.cleanup_old_tasks(days=1)

    # Verify batch operations were called
    batch_mock.delete.assert_called()
    batch_mock.commit.assert_called()


class TestTaskManagerIntegration:
    """Integration tests for task manager"""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, task_manager):
        """Test complete task lifecycle"""
        # Submit task
        task_id = await task_manager.submit_task(
            task_type="integration_test", payload={"test": "data"}
        )

        # Update to running
        await task_manager.update_task_status(
            task_id=task_id, status=TaskStatus.RUNNING, agent_id="test-agent"
        )

        # Complete task
        await task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"success": True},
        )

        # Verify all operations were called
        assert task_manager.tasks_client.create_task.called
        assert task_manager.firestore_client.collection().document().set.called
        assert (
            task_manager.firestore_client.collection()
            .document()
            .update.call_count
            >= 2
        )


if __name__ == "__main__":
    pytest.main([__file__])
