#!/usr/bin/env python3
"""
Script to identify completed tasks and mark them as inactive.
This helps maintain a clean active task list by moving completed
tasks to history.
"""

from database import get_database
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def deactivate_completed_tasks():
    """Find completed tasks and mark them as inactive"""
    db = await get_database()

    # Get all active tasks
    active_tasks = await db.get_active_tasks()

    completed_statuses = ["completed", "failed", "timeout", "stopped"]
    tasks_to_deactivate = []

    print(f"Found {len(active_tasks)} active tasks")

    for task in active_tasks:
        if task.status in completed_statuses:
            tasks_to_deactivate.append(task)
            print(
                f"Task {task.task_id}: {task.status} - "
                f"'{task.task_description[:50]}...'"
            )

    if not tasks_to_deactivate:
        print("No completed active tasks found to deactivate")
        return

    print(f"\nDeactivating {len(tasks_to_deactivate)} completed tasks...")

    for task in tasks_to_deactivate:
        await db.mark_task_inactive(task.task_id)
        print(f"Deactivated task {task.task_id}")

    print(f"\nSuccessfully deactivated {len(tasks_to_deactivate)} tasks")

    # Show updated statistics
    stats = await db.get_task_statistics()
    print(f"\nTask Statistics:")
    print(f"Total tasks: {stats['total_tasks']}")
    print(f"Active tasks: {stats['active_tasks']}")
    print(f"Completed tasks: {stats['completed_tasks']}")


if __name__ == "__main__":
    asyncio.run(deactivate_completed_tasks())
