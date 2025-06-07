#!/usr/bin/env python3
"""
Script to check current task status and details.
"""

from database import get_database
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def check_task_status():
    """Check status of all tasks"""
    db = await get_database()

    # Get all tasks
    all_tasks = await db.get_all_tasks()

    print(f"Total tasks in database: {len(all_tasks)}")
    print("\nTask Details:")
    print("-" * 80)

    for task in all_tasks:
        print(
            f"ID: {task.task_id}\n"
            f"Status: {task.status}\n"
            f"Active: {task.is_active}\n"
            f"Description: {task.task_description[:100]}...\n"
            f"Created: {task.created_at}\n"
            f"Updated: {task.updated_at}\n"
        )
        print("-" * 80)

    # Show statistics
    stats = await db.get_task_statistics()
    print(f"\nTask Statistics:")
    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Active tasks: {stats['active_tasks']}")
    print(f"Completed tasks: {stats['completed_tasks']}")
    print(f"Status distribution: {stats['status_distribution']}")


if __name__ == "__main__":
    asyncio.run(check_task_status())
