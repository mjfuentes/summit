#!/usr/bin/env python3
"""
Test the task management API through the FastMCP server
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

from src.database_models import TaskPriority
from src.summit_client import SummitClient


async def run_test(
    mcp_server_url="http://localhost:8080",
    role="engineering",
    process_delay=2,
    simulate_failure=False,
):
    """Run a test of the FastMCP task API"""
    # Generate unique agent ID for this test
    agent_id = f"test-agent-{uuid.uuid4()}"
    print(f"Test agent ID: {agent_id}")

    # Initialize Summit client
    async with SummitClient(server_url=mcp_server_url) as client:
        # Step 1: Submit a test task via task queue manager directly
        # (Normally tasks would be created through other means)
        print("\n=== Step 1: Creating task in database ===")
        from src.task_queue_manager import get_task_queue_manager

        task_queue_manager = await get_task_queue_manager()

        task_id = await task_queue_manager.submit_task(
            task_type="test_mcp_api",
            payload={
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "description": "Test task for FastMCP API testing",
            },
            priority=TaskPriority.HIGH,
            assigned_role=role,
            delay_seconds=0,
        )

        print(f"Task created: {task_id}")
        print(f"  Type: test_mcp_api")
        print(f"  Role: {role}")

        # Step 2: Get and claim the next task via FastMCP API
        print(
            "\n=== Step 2: Getting and claiming next task via FastMCP API ==="
        )
        response = await client.get_next_task(
            agent_id=agent_id,
            role=role,
        )

        print(f"Response from FastMCP API:")
        print(json.dumps(response, indent=2))

        # Parse task ID from response
        if response.get("status") != "success" or "task" not in response:
            print("Failed to get and claim task!")
            return

        # Extract task ID from response
        task_id = response["task"]["id"]
        print(f"Successfully claimed task: {task_id}")

        # Step 3: Simulate task processing
        print(
            f"\n=== Step 3: Processing task (waiting {process_delay} seconds) ==="
        )
        time.sleep(process_delay)

        # Step 4: Complete the task via FastMCP API
        print("\n=== Step 4: Completing task via FastMCP API ===")
        success = not simulate_failure

        completion_response = await client.complete_task(
            task_id=task_id,
            agent_id=agent_id,
            success=success,
            result={
                "processed_at": datetime.utcnow().isoformat(),
                "processing_time": f"{process_delay} seconds",
                "output": (
                    "Task processed successfully"
                    if success
                    else "Task processing failed"
                ),
            },
            summary=(
                "Task completed successfully"
                if success
                else "Task failed during processing"
            ),
            files_modified=(
                ["file1.txt", "file2.py", "file3.md"] if success else []
            ),
            error_message="Simulated task failure" if simulate_failure else "",
        )

        print(f"Response from FastMCP API:")
        print(json.dumps(completion_response, indent=2))

        if completion_response.get("status") != (
            "success" if success else "error"
        ):
            print("Failed to complete task with expected status!")
            return

        # Step 5: Verify final task state
        print("\n=== Step 5: Verifying final task state ===")
        from src.database_models import TaskStatus
        from src.unified_database import get_database

        db = await get_database()
        final_task = await db.get_agent_task(task_id)

        if not final_task:
            print("Task not found!")
            return

        expected_status = (
            TaskStatus.COMPLETED if success else TaskStatus.FAILED
        )
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
    parser = argparse.ArgumentParser(description="Test FastMCP task API")

    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="FastMCP server URL",
    )

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
            mcp_server_url=args.url,
            role=args.role,
            process_delay=args.delay,
            simulate_failure=args.fail,
        )
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
