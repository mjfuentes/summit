#!/usr/bin/env python3
"""
Database initialization script for Summit task persistence.
Run this script to set up the database and verify it's working correctly.
"""


# Add src to path
sys.path.insert(

    0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")

)







async def main():

    """Initialize database and run basic tests"""

    print("Initializing Summit task database...")



    try:

        # Initialize database

        await init_database()

        print(" Database initialized successfully")



        # Get database manager

        await DatabaseManager().init_database()

        db_manager = DatabaseManager()

        await db_manager.init_database()



        # Test basic operations

        print("\nTesting database operations...")



        # Create a test task

        test_task_data = {

            "task_id": "test-123",

            "task_description": "Test database connectivity",

            "status": "completed",

            "progress": "Test completed",

            "logs": ["Database test started", "Database test completed"],

            "is_active": False,

        }



        await db_manager.create_task(test_task_data)

        print(" Task creation test passed")



        # Retrieve the task

        retrieved_task = await db_manager.get_task("test-123")

        if (

            retrieved_task

            and retrieved_task.task_description == "Test database connectivity"

        ):

            print(" Task retrieval test passed")

        else:

            print(" Task retrieval test failed")

            return False



        # Update the task

        await db_manager.update_task("test-123", {"status": "archived"})

        updated_task = await db_manager.get_task("test-123")

        if updated_task and updated_task.status == "archived":

            print(" Task update test passed")

        else:

            print(" Task update test failed")

            return False



        # Get statistics

        stats = await db_manager.get_task_statistics()

        print(f" Database statistics: {stats}")



        # Clean up test data

        from sqlalchemy import delete

        from database import Task



        async with db_manager.get_session() as session:

            await session.execute(

                delete(Task).where(Task.task_id == "test-123")

            )



        print(" Test cleanup completed")



        await db_manager.close()

        print("\n Database is ready for use!")

        print(f"Database location: {db_manager.database_url}")



        return True



    except Exception as e:

        print(f"\n Database initialization failed: {e}")

        import traceback



        traceback.print_exc()

        return False





if __name__ == "__main__":

    success = asyncio.run(main())

    sys.exit(0 if success else 1)

