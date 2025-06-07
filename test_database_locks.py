#!/usr/bin/env python3
"""
Test script to verify database lock fix with concurrent operations.
"""

import asyncio
import os
import tempfile

from src.database import DatabaseManager


async def test_concurrent_database_operations():
    """Test concurrent database operations to verify lock fix"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite+aiosqlite:///{tmp.name}"

    db = DatabaseManager(db_url)
    await db.init_database()

    async def create_task(task_id):
        """Create a task and update it"""
        task_data = {
            "task_id": task_id,
            "task_description": f"Concurrent test task {task_id}",
            "status": "pending",
            "logs": ["Task created"],
            "is_active": True,
        }

        # Create task
        await db.create_task(task_data)

        # Update task multiple times to test locking
        for i in range(5):
            updates = {
                "status": "running",
                "progress": f"Step {i+1}",
                "logs": [f"Step {i+1} completed"],
            }
            await db.update_task(task_id, updates)

    # Run multiple concurrent operations
    tasks = []
    for i in range(10):
        tasks.append(create_task(f"concurrent-task-{i}"))

    # Execute all tasks concurrently
    await asyncio.gather(*tasks)

    # Verify all tasks were created successfully
    all_tasks = await db.get_all_tasks()

    await db.close()

    # Clean up
    try:
        os.unlink(tmp.name)
    except Exception:
        pass

    return len(all_tasks) == 10


async def main():
    """Run the database lock test"""
    print("Testing database lock fix with concurrent operations...")

    try:
        result = await test_concurrent_database_operations()
        if result:
            print(
                "✓ Database lock test PASSED - all concurrent operations completed successfully"
            )
        else:
            print("✗ Database lock test FAILED - some operations were lost")
        return result
    except Exception as e:
        print(f"✗ Database lock test FAILED with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
