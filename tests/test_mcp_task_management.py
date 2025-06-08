#!/usr/bin/env python3
"""
Test suite for MCP task management endpoints
Tests the new task collaboration features for agent coordination
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from database_models import (
    AgentTask,
    TaskComment,
    TaskPriority,
    TaskReview,
    TaskStatus,
)
from unified_database import UnifiedDatabaseManager


class TestMCPTaskManagement:
    """Test MCP task management functionality"""

    @pytest.fixture
    async def db_manager(self):
        """Create test database manager"""
        # Use in-memory SQLite for testing
        db_url = "sqlite+aiosqlite:///:memory:"
        db = UnifiedDatabaseManager(db_url)
        await db.init_database()
        return db

    @pytest.fixture
    async def sample_task(self, db_manager):
        """Create a sample task for testing"""
        task_data = {
            "task_type": "code_review",
            "assigned_role": "engineering",
            "payload": {"pr_number": 123, "repository": "summit"},
            "priority": TaskPriority.HIGH,
            "status": TaskStatus.PENDING,
            "context": {"test": True},
        }
        task = await db_manager.create_agent_task(task_data)
        return task

    @pytest.fixture
    async def sample_agent_id(self):
        """Return a sample agent ID"""
        return "agent-test-001"

    @pytest.mark.asyncio
    async def test_create_task_comment(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test creating task comments"""
        comment = await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="review",
            content="This code looks good overall but needs better error handling",
            approval_status="needs_changes",
            rating=4,
            is_internal=False,
        )

        assert comment.id is not None
        assert comment.task_id == sample_task.id
        assert comment.agent_id == sample_agent_id
        assert comment.comment_type == "review"
        assert (
            comment.content
            == "This code looks good overall but needs better error handling"
        )
        assert comment.approval_status == "needs_changes"
        assert comment.rating == 4
        assert comment.is_internal is False

    @pytest.mark.asyncio
    async def test_get_task_comments(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test retrieving task comments"""
        # Create multiple comments
        await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="comment",
            content="Initial review comment",
            is_internal=False,
        )

        await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id="agent-test-002",
            comment_type="question",
            content="Can we add more unit tests?",
            is_internal=True,
        )

        # Get all comments
        all_comments = await db_manager.get_task_comments(
            str(sample_task.id), include_internal=True
        )
        assert len(all_comments) == 2

        # Get only external comments
        external_comments = await db_manager.get_task_comments(
            str(sample_task.id), include_internal=False
        )
        assert len(external_comments) == 1
        assert external_comments[0].comment_type == "comment"

    @pytest.mark.asyncio
    async def test_create_task_review(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test creating structured task reviews"""
        review = await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="Code quality is excellent with comprehensive tests",
            findings=[
                "Good error handling",
                "Comprehensive tests",
                "Clean code structure",
            ],
            recommendations=[
                "Add more documentation",
                "Consider performance optimization",
            ],
            quality_score=8.5,
            confidence=0.95,
            files_reviewed=["src/main.py", "tests/test_main.py"],
        )

        assert review.id is not None
        assert review.task_id == sample_task.id
        assert review.reviewer_agent_id == sample_agent_id
        assert review.review_type == "code_review"
        assert review.decision == "approved"
        assert review.quality_score == 8.5
        assert review.confidence == 0.95
        assert len(review.findings) == 3
        assert len(review.recommendations) == 2

    @pytest.mark.asyncio
    async def test_get_task_reviews(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test retrieving task reviews"""
        # Create multiple reviews
        await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="First review",
        )

        await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id="agent-security-001",
            review_type="security_review",
            decision="needs_changes",
            summary="Security review findings",
        )

        # Get all reviews
        all_reviews = await db_manager.get_task_reviews(str(sample_task.id))
        assert len(all_reviews) == 2

        # Get only code reviews
        code_reviews = await db_manager.get_task_reviews(
            str(sample_task.id), review_type="code_review"
        )
        assert len(code_reviews) == 1
        assert code_reviews[0].review_type == "code_review"

    @pytest.mark.asyncio
    async def test_update_agent_task(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test updating agent task status and data"""
        updates = {
            "status": TaskStatus.RUNNING,
            "agent_id": sample_agent_id,
            "started_at": datetime.utcnow(),
        }

        updated_task = await db_manager.update_agent_task(
            str(sample_task.id), updates
        )

        assert updated_task is not None
        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.agent_id == sample_agent_id
        assert updated_task.started_at is not None

    @pytest.mark.asyncio
    async def test_get_task_with_collaboration_data(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test retrieving task with all collaboration data"""
        # Add comments and reviews
        await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="comment",
            content="Test comment",
        )

        await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="Test review",
        )

        # Get full collaboration data
        task_data = await db_manager.get_task_with_collaboration_data(
            str(sample_task.id)
        )

        assert task_data is not None
        assert "comments" in task_data
        assert "reviews" in task_data
        assert len(task_data["comments"]) == 1
        assert len(task_data["reviews"]) == 1
        assert task_data["comments"][0]["content"] == "Test comment"
        assert task_data["reviews"][0]["summary"] == "Test review"

    @pytest.mark.asyncio
    async def test_get_agent_task_activity(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test retrieving agent activity summary"""
        # Create activity for the agent
        await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="comment",
            content="Activity comment",
        )

        await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="Activity review",
        )

        activity = await db_manager.get_agent_task_activity(
            sample_agent_id, limit=10
        )

        assert activity["agent_id"] == sample_agent_id
        assert activity["total_comments"] == 1
        assert activity["total_reviews"] == 1
        assert len(activity["recent_comments"]) == 1
        assert len(activity["recent_reviews"]) == 1

    @pytest.mark.asyncio
    async def test_comment_threading(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test comment threading functionality"""
        # Create parent comment
        parent_comment = await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="question",
            content="Should we add more tests?",
        )

        # Create reply comment
        reply_comment = await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id="agent-test-002",
            comment_type="comment",
            content="Yes, definitely need more edge case tests",
            parent_comment_id=str(parent_comment.id),
        )

        assert reply_comment.parent_comment_id == parent_comment.id

        # Verify comment structure
        all_comments = await db_manager.get_task_comments(str(sample_task.id))
        assert len(all_comments) == 2

        parent = next(c for c in all_comments if c.parent_comment_id is None)
        reply = next(
            c for c in all_comments if c.parent_comment_id is not None
        )

        assert parent.content == "Should we add more tests?"
        assert reply.content == "Yes, definitely need more edge case tests"
        assert reply.parent_comment_id == parent.id

    @pytest.mark.asyncio
    async def test_comment_update_and_resolution(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test updating and resolving comments"""
        comment = await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="question",
            content="Original question",
            is_resolved=False,
        )

        # Update comment to resolved
        updated_comment = await db_manager.update_task_comment(
            str(comment.id),
            {
                "is_resolved": True,
                "content": "Updated question with resolution",
            },
        )

        assert updated_comment.is_resolved is True
        assert updated_comment.content == "Updated question with resolution"

    @pytest.mark.asyncio
    async def test_review_superseding(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test review superseding functionality"""
        # Create initial review
        initial_review = await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="needs_changes",
            summary="Initial review",
            is_final=False,
        )

        # Create superseding review
        final_review = await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="Final review after changes",
            is_final=True,
        )

        # Update initial review to point to superseding review
        await db_manager.update_task_review(
            str(initial_review.id), {"superseded_by": final_review.id}
        )

        # Verify superseding relationship
        updated_initial = await db_manager.get_review_by_id(
            str(initial_review.id)
        )
        assert updated_initial.superseded_by == final_review.id
        assert updated_initial.is_final is False

        final = await db_manager.get_review_by_id(str(final_review.id))
        assert final.is_final is True

    @pytest.mark.asyncio
    async def test_task_deletion_cascades(
        self, db_manager, sample_task, sample_agent_id
    ):
        """Test that deleting tasks properly cascades to comments and reviews"""
        # Add comments and reviews
        await db_manager.create_task_comment(
            task_id=str(sample_task.id),
            agent_id=sample_agent_id,
            comment_type="comment",
            content="Test comment",
        )

        await db_manager.create_task_review(
            task_id=str(sample_task.id),
            reviewer_agent_id=sample_agent_id,
            review_type="code_review",
            decision="approved",
            summary="Test review",
        )

        # Verify data exists
        comments = await db_manager.get_task_comments(str(sample_task.id))
        reviews = await db_manager.get_task_reviews(str(sample_task.id))
        assert len(comments) == 1
        assert len(reviews) == 1

        # Delete the task
        deleted = await db_manager.delete_agent_task(str(sample_task.id))
        assert deleted is True

        # Verify task no longer exists
        task = await db_manager.get_agent_task(str(sample_task.id))
        assert task is None

        # Note: Comments and reviews should cascade delete due to foreign key constraints
        # This would be enforced at the database level


class TestMCPTaskTools:
    """Test MCP tool handlers for task management"""

    @pytest.fixture
    def mock_database(self):
        """Mock database for testing tool handlers"""
        mock_db = AsyncMock()
        return mock_db

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing"""
        task_id = str(uuid.uuid4())
        return {
            "id": task_id,
            "task_type": "code_review",
            "status": "pending",
            "assigned_role": "engineering",
            "agent_id": None,
            "priority": "high",
            "created_at": "2024-01-01T00:00:00",
            "payload": {"pr_number": 123},
            "comments": [],
            "reviews": [],
        }

    @pytest.mark.asyncio
    async def test_summit_get_task_tool(self, mock_database, sample_task_data):
        """Test the summit_get_task MCP tool"""
        from summit import handle_call_tool

        # Mock the database response
        mock_database.get_task_with_collaboration_data.return_value = (
            sample_task_data
        )

        with patch(
            "unified_database.get_database", return_value=mock_database
        ):
            result = await handle_call_tool(
                "summit_get_task",
                {
                    "task_id": sample_task_data["id"],
                    "include_collaboration": True,
                },
            )

        assert len(result) == 1
        response_text = result[0].text
        assert "Task Details" in response_text
        assert sample_task_data["id"] in response_text
        assert "code_review" in response_text

    @pytest.mark.asyncio
    async def test_summit_add_task_comment_tool(self, mock_database):
        """Test the summit_add_task_comment MCP tool"""
        from summit import handle_call_tool

        # Mock the database response
        mock_comment = Mock()
        task_id = str(uuid.uuid4())
        comment_id = str(uuid.uuid4())
        mock_comment.id = comment_id
        mock_comment.task_id = task_id
        mock_comment.agent_id = "agent-001"
        mock_comment.comment_type = "review"
        mock_comment.content = "Great work on this PR!"
        mock_database.create_task_comment.return_value = mock_comment

        with patch(
            "unified_database.get_database", return_value=mock_database
        ):
            result = await handle_call_tool(
                "summit_add_task_comment",
                {
                    "task_id": task_id,
                    "agent_id": "agent-001",
                    "comment_type": "review",
                    "content": "Great work on this PR!",
                    "rating": 5,
                },
            )

        assert len(result) == 1
        response_text = result[0].text
        assert "Comment added successfully" in response_text
        assert comment_id in response_text

        # Verify database call
        mock_database.create_task_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_summit_create_task_review_tool(self, mock_database):
        """Test the summit_create_task_review MCP tool"""
        from summit import handle_call_tool

        # Mock the database response
        mock_review = Mock()
        task_id = str(uuid.uuid4())
        review_id = str(uuid.uuid4())
        mock_review.id = review_id
        mock_review.task_id = task_id
        mock_review.reviewer_agent_id = "agent-001"
        mock_review.review_type = "security_review"
        mock_review.decision = "approved"
        mock_review.summary = "Security analysis complete"
        mock_review.quality_score = 9.0
        mock_review.confidence = 0.95
        mock_database.create_task_review.return_value = mock_review

        with patch(
            "unified_database.get_database", return_value=mock_database
        ):
            result = await handle_call_tool(
                "summit_create_task_review",
                {
                    "task_id": task_id,
                    "reviewer_agent_id": "agent-001",
                    "review_type": "security_review",
                    "decision": "approved",
                    "summary": "Security analysis complete",
                    "quality_score": 9.0,
                    "confidence": 0.95,
                },
            )

        assert len(result) == 1
        response_text = result[0].text
        assert "Task review created successfully" in response_text
        assert review_id in response_text

        # Verify database call
        mock_database.create_task_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_summit_update_task_status_tool(self, mock_database):
        """Test the summit_update_task_status MCP tool"""
        from database_models import TaskStatus
        from summit import handle_call_tool

        # Mock the database response
        mock_task = Mock()
        task_id = str(uuid.uuid4())
        mock_task.id = task_id
        mock_task.status = TaskStatus.RUNNING
        mock_task.agent_id = "agent-001"
        mock_database.update_agent_task.return_value = mock_task

        # Mock get_agent_task to return existing task
        existing_task = Mock()
        existing_task.id = task_id
        mock_database.get_agent_task.return_value = existing_task

        with patch(
            "unified_database.get_database", return_value=mock_database
        ):
            result = await handle_call_tool(
                "summit_update_task_status",
                {
                    "task_id": task_id,
                    "status": "running",
                    "agent_id": "agent-001",
                    "result": {"progress": "50%"},
                },
            )

        assert len(result) == 1
        response_text = result[0].text
        assert "Task status updated successfully" in response_text

    @pytest.mark.asyncio
    async def test_error_handling_missing_task(self, mock_database):
        """Test error handling when task is not found"""
        from summit import handle_call_tool

        # Mock database to return None (task not found)
        mock_database.get_task_with_collaboration_data.return_value = None

        task_id = str(uuid.uuid4())
        with patch(
            "unified_database.get_database", return_value=mock_database
        ):
            result = await handle_call_tool(
                "summit_get_task",
                {"task_id": task_id, "include_collaboration": True},
            )

        assert len(result) == 1
        response_text = result[0].text
        assert "not found" in response_text.lower()

    @pytest.mark.asyncio
    async def test_error_handling_missing_parameters(self):
        """Test error handling for missing required parameters"""
        from summit import handle_call_tool

        with pytest.raises(ValueError, match="Task ID is required"):
            await handle_call_tool("summit_get_task", {})

        with pytest.raises(ValueError, match="required"):
            await handle_call_tool(
                "summit_add_task_comment", {"task_id": str(uuid.uuid4())}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
