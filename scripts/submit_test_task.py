#!/usr/bin/env python3
"""
Submit a test task to the task queue manager
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database_models import TaskPriority
from src.task_queue_manager import get_task_queue_manager


async def submit_task(task_type, payload, priority, role, delay):
    """Submit a task to the queue manager"""
    # Initialize task queue manager
    task_queue_manager = await get_task_queue_manager()

    # Convert priority string to enum
    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
    }

    priority_enum = priority_map.get(priority.lower(), TaskPriority.NORMAL)

    # Submit task
    task_id = await task_queue_manager.submit_task(
        task_type=task_type,
        payload=payload,
        priority=priority_enum,
        assigned_role=role,
        delay_seconds=delay,
    )

    print(f"Task submitted: {task_id}")
    print(f"  Type: {task_type}")
    print(f"  Role: {role}")
    print(f"  Priority: {priority}")

    if delay > 0:
        print(f"  Delay: {delay} seconds")

    return task_id


def main():
    """Parse arguments and submit task"""
    parser = argparse.ArgumentParser(description="Submit a test task")

    parser.add_argument(
        "--type",
        default="test_task",
        help="Task type",
    )

    parser.add_argument(
        "--payload",
        default=json.dumps(
            {"test": True, "timestamp": datetime.utcnow().isoformat()}
        ),
        help="Task payload as JSON string",
    )

    parser.add_argument(
        "--priority",
        default="normal",
        choices=["low", "normal", "high", "urgent"],
        help="Task priority",
    )

    parser.add_argument(
        "--role",
        default="engineering",
        help="Role assigned to the task",
    )

    parser.add_argument(
        "--delay",
        type=int,
        default=0,
        help="Delay in seconds before task execution",
    )

    args = parser.parse_args()

    try:
        # Parse payload
        payload = json.loads(args.payload)
    except json.JSONDecodeError:
        print("Error: Invalid JSON payload")
        return 1

    # Submit task
    asyncio.run(
        submit_task(
            task_type=args.type,
            payload=payload,
            priority=args.priority,
            role=args.role,
            delay=args.delay,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
