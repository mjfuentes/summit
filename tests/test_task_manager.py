#!/usr/bin/env python3

import os
import sys
import unittest
import pytest
from unittest.mock import patch, Mock, AsyncMock

# Add src to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.task_manager import (
    update_task_status,
    add_task_log,
    mark_task_completed,
    get_task_data,
    update_task_container_info,
    update_task_log_file,
)


class TestTaskManager:
    """Test task manager utility functions"""

    @pytest.mark.asyncio
    async def test_update_task_status_basic(self):
        """Test updating task status"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_status("test-123", "running")

            mock_db.update_task.assert_called_once_with(
                "test-123", {"status": "running"}
            )

    @pytest.mark.asyncio
    async def test_update_task_status_with_progress(self):
        """Test updating task status with progress"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_status("test-123", "running", progress="50%")

            mock_db.update_task.assert_called_once_with(
                "test-123", {"status": "running", "progress": "50%"}
            )

    @pytest.mark.asyncio
    async def test_update_task_status_with_error(self):
        """Test updating task status with error"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_status("test-123", "failed", error="Test error")

            mock_db.update_task.assert_called_once_with(
                "test-123", {"status": "failed", "error": "Test error"}
            )

    @pytest.mark.asyncio
    async def test_update_task_status_with_all_params(self):
        """Test updating task status with all parameters"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_status(
                "test-123", "failed", progress="75%", error="Test error"
            )

            mock_db.update_task.assert_called_once_with(
                "test-123",
                {"status": "failed", "progress": "75%", "error": "Test error"},
            )

    @pytest.mark.asyncio
    async def test_add_task_log_new_log(self):
        """Test adding a log message to a task with no existing logs"""
        mock_task = Mock()
        mock_task.logs = None

        mock_db = AsyncMock()
        mock_db.get_task = AsyncMock(return_value=mock_task)
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await add_task_log("test-123", "Test log message")

            mock_db.get_task.assert_called_once_with("test-123")
            mock_db.update_task.assert_called_once_with(
                "test-123", {"logs": ["Test log message"]}
            )

    @pytest.mark.asyncio
    async def test_add_task_log_existing_logs(self):
        """Test adding a log message to a task with existing logs"""
        mock_task = Mock()
        mock_task.logs = ["Previous log"]

        mock_db = AsyncMock()
        mock_db.get_task = AsyncMock(return_value=mock_task)
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await add_task_log("test-123", "New log message")

            mock_db.get_task.assert_called_once_with("test-123")
            mock_db.update_task.assert_called_once_with(
                "test-123", {"logs": ["Previous log", "New log message"]}
            )

    @pytest.mark.asyncio
    async def test_add_task_log_no_task(self):
        """Test adding a log message when task doesn't exist"""
        mock_db = AsyncMock()
        mock_db.get_task = AsyncMock(return_value=None)
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await add_task_log("test-123", "Test log message")

            mock_db.get_task.assert_called_once_with("test-123")
            mock_db.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_container_info(self):
        """Test updating task with container information"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_container_info(
                "test-123", "container-456", "https://test.url"
            )

            mock_db.update_task.assert_called_once_with(
                "test-123",
                {
                    "container_id": "container-456",
                    "claude_code_url": "https://test.url",
                },
            )

    @pytest.mark.asyncio
    async def test_update_task_log_file(self):
        """Test updating task with log file path"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await update_task_log_file("test-123", "/path/to/log.txt")

            mock_db.update_task.assert_called_once_with(
                "test-123", {"log_file": "/path/to/log.txt"}
            )

    @pytest.mark.asyncio
    async def test_mark_task_completed_success(self):
        """Test marking task as completed successfully"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await mark_task_completed("test-123", True)

            mock_db.update_task.assert_called_once_with(
                "test-123", {"status": "completed", "is_active": False}
            )

    @pytest.mark.asyncio
    async def test_mark_task_completed_failed(self):
        """Test marking task as failed"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await mark_task_completed("test-123", False)

            mock_db.update_task.assert_called_once_with(
                "test-123", {"status": "failed", "is_active": False}
            )

    @pytest.mark.asyncio
    async def test_mark_task_completed_with_logs(self):
        """Test marking task as completed with full logs"""
        mock_db = AsyncMock()
        mock_db.update_task = AsyncMock()

        with patch("src.task_manager.get_database", return_value=mock_db):
            await mark_task_completed("test-123", True, "Full log content")

            mock_db.update_task.assert_called_once_with(
                "test-123",
                {
                    "status": "completed",
                    "is_active": False,
                    "full_logs": "Full log content",
                },
            )

    @pytest.mark.asyncio
    async def test_get_task_data_exists(self):
        """Test getting task data when task exists"""
        mock_task = Mock()
        mock_task.to_dict.return_value = {
            "task_id": "test-123",
            "status": "running",
            "description": "Test task",
        }

        mock_db = AsyncMock()
        mock_db.get_task = AsyncMock(return_value=mock_task)

        with patch("src.task_manager.get_database", return_value=mock_db):
            result = await get_task_data("test-123")

            mock_db.get_task.assert_called_once_with("test-123")
            assert result == {
                "task_id": "test-123",
                "status": "running",
                "description": "Test task",
            }

    @pytest.mark.asyncio
    async def test_get_task_data_not_exists(self):
        """Test getting task data when task doesn't exist"""
        mock_db = AsyncMock()
        mock_db.get_task = AsyncMock(return_value=None)

        with patch("src.task_manager.get_database", return_value=mock_db):
            result = await get_task_data("test-123")

            mock_db.get_task.assert_called_once_with("test-123")
            assert result is None
