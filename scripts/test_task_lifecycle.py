#!/usr/bin/env python3
"""
Test the full task lifecycle - submitting, claiming, and completing a task
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database_models import TaskPriority, TaskStatus
from src.task_queue_manager import get_task_queue_manager
from src.unified_database import get_database


async def run_test(
    role="engineering", process_delay=2, simulate_failure=False
):
    """Run the full task lifecycle test"""
    # Generate unique agent ID for this test
    agent_id = f"test-agent-{uuid.uuid4()}"
    print(f"Test agent ID: {agent_id}")

    # Initialize task queue manager and database
    task_queue_manager = await get_task_queue_manager()
    db = await get_database()

    # Step 1: Submit a test task
    print("\n=== Step 1: Submitting task ===")
    task_type = "test_lifecycle"
    payload = {
        "test": True,
        "timestamp": datetime.utcnow().isoformat(),
        "description": "Test task for lifecycle testing",
    }

    task_id = await task_queue_manager.submit_task(
        task_type=task_type,
        payload=payload,
        priority=TaskPriority.HIGH,
        assigned_role=role,
        delay_seconds=0,
    )

    print(f"Task submitted: {task_id}")
    print(f"  Type: {task_type}")
    print(f"  Role: {role}")
    print(f"  Priority: HIGH")

    # Step 2: Get available tasks
    print("\n=== Step 2: Getting available tasks ===")
    tasks = await task_queue_manager.get_next_available_task(
        agent_id=agent_id,
        roles=[role],
        limit=5,
    )

    if not tasks:
        print("No tasks available!")
        return

    print(f"Found {len(tasks)} available tasks:")
    for i, task in enumerate(tasks):
        print(
            f"  {i+1}. {task.id} - {task.task_type} (Priority: {task.priority.name})"
        )

    # Check if our submitted task is in the available tasks
    submitted_task = None
    for task in tasks:
        if str(task.id) == task_id:
            submitted_task = task
            break

    if not submitted_task:
        print("Submitted task not found in available tasks!")

        # Check if it exists in the database
        task = await db.get_agent_task(task_id)
        if task:
            print(f"Task exists in database with status: {task.status.name}")
        else:
            print("Task not found in database!")
        return

    # Step 3: Claim the task
    print("\n=== Step 3: Claiming task ===")
    claimed_task = await task_queue_manager.claim_task(
        task_id=task_id,
        agent_id=agent_id,
    )

    if not claimed_task:
        print("Failed to claim task!")
        return

    print(f"Task claimed: {claimed_task.id}")
    print(f"  Agent: {agent_id}")
    print(f"  Status: {claimed_task.status.name}")

    # Step 4: Simulate task processing
    print(
        f"\n=== Step 4: Processing task (waiting {process_delay} seconds) ==="
    )
    time.sleep(process_delay)

    # Step 5: Complete the task
    print("\n=== Step 5: Completing task ===")
    success = not simulate_failure
    result = {
        "processed_at": datetime.utcnow().isoformat(),
        "processing_time": f"{process_delay} seconds",
        "output": (
            "Task processed successfully"
            if success
            else "Task processing failed"
        ),
    }

    summary = (
        "Task completed successfully"
        if success
        else "Task failed during processing"
    )
    files_modified = ["file1.txt", "file2.py", "file3.md"] if success else []
    error_message = "Simulated task failure" if simulate_failure else None

    completed = await task_queue_manager.complete_task(
        task_id=task_id,
        agent_id=agent_id,
        success=success,
        result=result,
        summary=summary,
        files_modified=files_modified,
        error_message=error_message,
    )

    if not completed:
        print("Failed to complete task!")
        return

    print(f"Task {'completed' if success else 'failed'}: {task_id}")
    print(f"  Agent: {agent_id}")
    print(f"  Summary: {summary}")

    # Step 6: Verify final task state
    print("\n=== Step 6: Verifying final task state ===")
    final_task = await db.get_agent_task(task_id)

    if not final_task:
        print("Task not found!")
        return

    expected_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
    print(
        f"Task status: {final_task.status.name} (Expected: {expected_status.name})"
    )
    print(f"Agent ID: {final_task.agent_id} (Expected: {agent_id})")

    if (
        final_task.status == expected_status
        and final_task.agent_id == agent_id
    ):
        print("\n Test completed successfully!")
    else:
        print(
            "\n Test failed: Final task state does not match expected state!"
        )


def main():
    """Parse arguments and run test"""
    parser = argparse.ArgumentParser(description="Test task lifecycle")

    parser.add_argument(
        "--role",
        default="engineering",
        help="Role to assign the task to",
    )

    parser.add_argument(
        "--delay",
        type=int,
        default=2,
        help="Simulated processing time in seconds",
    )

    parser.add_argument(
        "--fail",
        action="store_true",
        help="Simulate task failure",
    )

    args = parser.parse_args()

    # Run test
    asyncio.run(
        run_test(
            role=args.role,
            process_delay=args.delay,
            simulate_failure=args.fail,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
