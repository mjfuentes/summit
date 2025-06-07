#!/usr/bin/env python3
"""
Task management utilities for database operations.
Provides helper functions to update tasks in the database consistently.
"""

from typing import Dict, List, Any, Optional
from database import get_database

async def update_task_status(task_id: str, status: str, progress: str = None, error: str = None):
    """Update task status in database"""
    db = await get_database()
    updates = {"status": status}
    if progress:
        updates["progress"] = progress
    if error:
        updates["error"] = error
    await db.update_task(task_id, updates)

async def add_task_log(task_id: str, message: str):
    """Add a log message to a task"""
    db = await get_database()
    task = await db.get_task(task_id)
    if task:
        logs = task.logs or []
        logs.append(message)
        await db.update_task(task_id, {"logs": logs})

async def update_task_container_info(task_id: str, container_id: str, claude_code_url: str):
    """Update task with container information"""
    db = await get_database()
    await db.update_task(task_id, {
        "container_id": container_id,
        "claude_code_url": claude_code_url
    })

async def update_task_log_file(task_id: str, log_file_path: str):
    """Update task with log file path"""
    db = await get_database()
    await db.update_task(task_id, {"log_file": log_file_path})

async def mark_task_completed(task_id: str, success: bool, full_logs: str = None):
    """Mark task as completed or failed"""
    db = await get_database()
    updates = {
        "status": "completed" if success else "failed",
        "is_active": False
    }
    if full_logs:
        updates["full_logs"] = full_logs
    await db.update_task(task_id, updates)

async def get_task_data(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task data as dictionary"""
    db = await get_database()
    task = await db.get_task(task_id)
    return task.to_dict() if task else None