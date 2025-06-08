"""
Unified Database Manager for Summit AI Platform
Consolidates all database operations into a single PostgreSQL-based system
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from database_models import (
    Agent,
    AgentContext,
    AgentStatus,
    AgentTask,
    Base,
    DatabaseManager,
    TaskComment,
    TaskLog,
    TaskPriority,
    TaskReview,
    TaskSource,
    TaskStatus,
    WebTask,
    get_database_manager,
    init_database_manager,
)


class UnifiedDatabaseManager:
    """
    Unified database manager that provides both web task and agent task functionality
    Uses PostgreSQL as the single source of truth
    """

    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            # Check environment variable first
            database_url = os.getenv("DATABASE_URL")

            if not database_url:
                # Detect CI/CD environments and development environments
                is_ci = any(
                    os.getenv(var)
                    for var in [
                        "CI",
                        "CONTINUOUS_INTEGRATION",
                        "GITHUB_ACTIONS",
                        "TRAVIS",
                        "CIRCLECI",
                        "JENKINS_URL",
                        "BUILDKITE",
                    ]
                )

                if is_ci:
                    # Use SQLite for CI/CD environments
                    db_dir = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), "data"
                    )
                    os.makedirs(db_dir, exist_ok=True)
                    database_url = f"sqlite+aiosqlite:///{db_dir}/summit_ci.db"
                    print(
                        f"CI environment detected, using SQLite: {database_url}"
                    )
                else:
                    # For local development, try PostgreSQL first, fallback to SQLite
                    try:
                        # Check if asyncpg is available for PostgreSQL
                        import asyncpg

                        database_url = "postgresql+asyncpg://postgres:postgres@localhost/summit_unified"
                        print(
                            f"Local development, attempting PostgreSQL: {database_url}"
                        )
                    except ImportError:
                        # Fall back to SQLite for development
                        db_dir = os.path.join(
                            os.path.dirname(os.path.dirname(__file__)), "data"
                        )
                        os.makedirs(db_dir, exist_ok=True)
                        database_url = (
                            f"sqlite+aiosqlite:///{db_dir}/summit_unified.db"
                        )
                        print(
                            f"asyncpg not available, using SQLite: {database_url}"
                        )

        # Initialize the global database manager
        # If PostgreSQL connection fails, we'll catch it in init_database
        init_database_manager(database_url)
        self.db_manager = get_database_manager()

    async def init_database(self):
        """Initialize all database tables with PostgreSQL fallback to SQLite"""
        try:
            await self.db_manager.init_database()
        except Exception as e:
            # If PostgreSQL connection fails, fallback to SQLite
            if "postgresql" in self.db_manager.database_url.lower():
                print(f"PostgreSQL connection failed: {e}")
                print("Falling back to SQLite for database operations...")

                # Create SQLite fallback
                db_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "data"
                )
                os.makedirs(db_dir, exist_ok=True)
                sqlite_url = f"sqlite+aiosqlite:///{db_dir}/summit_fallback.db"

                # Reinitialize with SQLite
                init_database_manager(sqlite_url)
                self.db_manager = get_database_manager()
                await self.db_manager.init_database()
                print(f"Successfully switched to SQLite: {sqlite_url}")
            else:
                # Re-raise if it's not a PostgreSQL connection issue
                raise

    @asynccontextmanager
    async def get_session(self):
        """Get database session with proper cleanup"""
        session = await self.db_manager.get_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Web Task Operations (compatible with old database.py interface)

    async def create_task(self, task_data: Dict[str, Any]) -> WebTask:
        """Create a new web task in the database"""
        async with self.get_session() as session:
            # Convert datetime strings to datetime objects if needed
            if isinstance(task_data.get("created_at"), str):
                task_data["created_at"] = datetime.fromisoformat(
                    task_data["created_at"].replace("Z", "+00:00")
                )

            task = WebTask(**task_data)
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task

    async def get_task(self, task_id: str) -> Optional[WebTask]:
        """Get a web task by ID"""
        async with self.get_session() as session:
            result = await session.execute(
                select(WebTask).where(WebTask.task_id == task_id)
            )
            return result.scalar_one_or_none()

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[WebTask]:
        """Update a web task with new data"""
        async with self.get_session() as session:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()

            # Handle completed_at timestamp
            if updates.get("status") in [
                "completed",
                "failed",
                "timeout",
                "stopped",
            ]:
                if not updates.get("completed_at"):
                    updates["completed_at"] = datetime.utcnow()

            result = await session.execute(
                update(WebTask)
                .where(WebTask.task_id == task_id)
                .values(**updates)
                .returning(WebTask)
            )
            task = result.scalar_one_or_none()
            return task

    async def get_active_tasks(self) -> List[WebTask]:
        """Get all active web tasks"""
        async with self.get_session() as session:
            result = await session.execute(
                select(WebTask)
                .where(WebTask.is_active.is_(True))
                .order_by(WebTask.created_at.desc())
            )
            return list(result.scalars().all())

    async def get_completed_tasks(self, limit: int = 50) -> List[WebTask]:
        """Get completed web tasks (most recent first)"""
        async with self.get_session() as session:
            result = await session.execute(
                select(WebTask)
                .where(WebTask.is_active.is_(False))
                .order_by(WebTask.completed_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def mark_task_inactive(self, task_id: str) -> Optional[WebTask]:
        """Mark a web task as inactive (move to history)"""
        return await self.update_task(task_id, {"is_active": False})

    async def get_all_tasks(self, limit: int = 100) -> List[WebTask]:
        """Get all web tasks (active and inactive)"""
        async with self.get_session() as session:
            result = await session.execute(
                select(WebTask)
                .order_by(WebTask.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def delete_old_tasks(self, days_old: int = 30):
        """Delete web tasks older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        async with self.get_session() as session:
            await session.execute(
                delete(WebTask)
                .where(WebTask.created_at < cutoff_date)
                .where(WebTask.is_active.is_(False))
            )

    async def delete_task(self, task_id: str) -> bool:
        """Delete a specific web task by ID"""
        async with self.get_session() as session:
            result = await session.execute(
                delete(WebTask).where(WebTask.task_id == task_id)
            )
            return result.rowcount > 0

    async def get_failed_tasks(self) -> List[WebTask]:
        """Get all failed web tasks"""
        async with self.get_session() as session:
            result = await session.execute(
                select(WebTask)
                .where(WebTask.status == "failed")
                .order_by(WebTask.created_at.desc())
            )
            return list(result.scalars().all())

    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get web task statistics"""
        async with self.get_session() as session:
            # Count by status
            result = await session.execute(
                select(
                    WebTask.status, func.count(WebTask.task_id).label("count")
                ).group_by(WebTask.status)
            )
            status_counts = {row.status: row.count for row in result}

            # Count active vs inactive
            active_result = await session.execute(
                select(func.count(WebTask.task_id)).where(
                    WebTask.is_active.is_(True)
                )
            )
            active_count = active_result.scalar()

            total_result = await session.execute(
                select(func.count(WebTask.task_id))
            )
            total_count = total_result.scalar()

            return {
                "total_tasks": total_count,
                "active_tasks": active_count,
                "completed_tasks": total_count - active_count,
                "status_distribution": status_counts,
            }

    # Agent Task Operations (from postgres_task_manager.py)

    async def get_agent_task(self, task_id) -> Optional[AgentTask]:
        """Get an agent task by ID"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            result = await session.execute(
                select(AgentTask).where(AgentTask.id == task_uuid)
            )
            return result.scalar_one_or_none()

    async def get_tasks_for_role(
        self, role: str, limit: int = 10
    ) -> List[AgentTask]:
        """Get pending agent tasks assigned to a specific role"""
        async with self.get_session() as session:
            # Order by priority value in descending order (URGENT=4, HIGH=3, NORMAL=2, LOW=1)
            # Then by creation time for tasks with same priority
            from sqlalchemy import case

            priority_order = case(
                (AgentTask.priority == TaskPriority.URGENT, 4),
                (AgentTask.priority == TaskPriority.HIGH, 3),
                (AgentTask.priority == TaskPriority.NORMAL, 2),
                (AgentTask.priority == TaskPriority.LOW, 1),
                else_=0,
            ).desc()

            result = await session.execute(
                select(AgentTask)
                .where(
                    AgentTask.status == TaskStatus.PENDING,
                    AgentTask.assigned_role == role,
                )
                .order_by(priority_order, AgentTask.created_at)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def claim_agent_task(self, task_id, agent_id: str) -> bool:
        """
        Atomically claim a task for an agent

        TODO: This is a basic implementation. For better backpressure and
        distribution, consider migrating to Cloud Tasks or Pub/Sub.
        """
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            # Atomic update - only claim if still pending
            result = await session.execute(
                update(AgentTask)
                .where(
                    AgentTask.id == task_uuid,
                    AgentTask.status == TaskStatus.PENDING,
                )
                .values(
                    status=TaskStatus.RUNNING,
                    agent_id=agent_id,
                    started_at=datetime.utcnow(),
                )
            )

            # Return True if we successfully claimed the task
            return result.rowcount > 0

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register an agent"""
        async with self.get_session() as session:
            # Check if agent already exists
            result = await session.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            existing_agent = result.scalar_one_or_none()

            if existing_agent:
                # Update existing agent
                await session.execute(
                    update(Agent)
                    .where(Agent.id == agent_id)
                    .values(
                        roles=agent_info.get("roles", []),
                        capabilities=agent_info.get("capabilities", []),
                        version=agent_info.get("version"),
                        status=AgentStatus.READY,
                        last_heartbeat=datetime.utcnow(),
                    )
                )
            else:
                # Create new agent
                agent = Agent(
                    id=agent_id,
                    name=agent_info.get("name"),
                    roles=agent_info.get("roles", []),
                    capabilities=agent_info.get("capabilities", []),
                    version=agent_info.get("version"),
                    status=AgentStatus.READY,
                    last_heartbeat=datetime.utcnow(),
                    max_concurrent_tasks=agent_info.get(
                        "max_concurrent_tasks", 1
                    ),
                    google_tasks_list_id=agent_info.get(
                        "google_tasks_list_id"
                    ),
                )
                session.add(agent)

    async def update_agent_heartbeat(self, agent_id: str, status: AgentStatus):
        """Update agent heartbeat and status"""
        async with self.get_session() as session:
            await session.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(
                    status=status,
                    last_heartbeat=datetime.utcnow(),
                )
            )

    async def increment_agent_completed_tasks(self, agent_id: str):
        """Increment completed tasks counter for agent"""
        async with self.get_session() as session:
            await session.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(
                    tasks_completed=Agent.tasks_completed + 1,
                    last_task_completed=datetime.utcnow(),
                )
            )

    async def increment_agent_failed_tasks(self, agent_id: str):
        """Increment failed tasks counter for agent"""
        async with self.get_session() as session:
            await session.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(
                    tasks_failed=Agent.tasks_failed + 1,
                )
            )

    async def close(self):
        """Close database connections"""
        await self.db_manager.close()

    async def get_all_agents(self) -> List[Agent]:
        """Get all registered agents"""
        async with self.get_session() as session:
            result = await session.execute(select(Agent))
            return list(result.scalars().all())

    async def get_tasks_since(
        self, since_date: datetime, limit: int = None
    ) -> List[AgentTask]:
        """Get tasks created since a specific date"""
        async with self.get_session() as session:
            query = select(AgentTask).where(AgentTask.created_at >= since_date)
            if limit:
                query = query.limit(limit)
            query = query.order_by(AgentTask.created_at.desc())
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_tasks_between(
        self, start_date: datetime, end_date: datetime
    ) -> List[AgentTask]:
        """Get tasks between two dates"""
        async with self.get_session() as session:
            result = await session.execute(
                select(AgentTask).where(
                    AgentTask.created_at >= start_date,
                    AgentTask.created_at < end_date,
                )
            )
            return list(result.scalars().all())

    # Task Comment Operations

    async def create_task_comment(
        self,
        task_id: str,
        agent_id: str,
        comment_type: str,
        content: str,
        **kwargs,
    ) -> TaskComment:
        """Create a new task comment"""
        async with self.get_session() as session:
            # Handle both string and UUID types for task_id
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            # Handle parent_comment_id conversion
            if "parent_comment_id" in kwargs and kwargs["parent_comment_id"]:
                if isinstance(kwargs["parent_comment_id"], str):
                    kwargs["parent_comment_id"] = UUID(
                        kwargs["parent_comment_id"]
                    )

            comment = TaskComment(
                task_id=task_uuid,
                agent_id=agent_id,
                comment_type=comment_type,
                content=content,
                **kwargs,
            )
            session.add(comment)
            await session.flush()
            await session.refresh(comment)
            return comment

    async def get_task_comments(
        self, task_id: str, include_internal: bool = True
    ) -> List[TaskComment]:
        """Get all comments for a task"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            query = select(TaskComment).where(TaskComment.task_id == task_uuid)

            if not include_internal:
                query = query.where(TaskComment.is_internal.is_(False))

            query = query.order_by(TaskComment.created_at)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_comment_by_id(
        self, comment_id: str
    ) -> Optional[TaskComment]:
        """Get a specific comment by ID"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(comment_id, str):
                comment_uuid = UUID(comment_id)
            else:
                comment_uuid = comment_id

            result = await session.execute(
                select(TaskComment).where(TaskComment.id == comment_uuid)
            )
            return result.scalar_one_or_none()

    async def update_task_comment(
        self, comment_id: str, updates: Dict[str, Any]
    ) -> Optional[TaskComment]:
        """Update a task comment"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(comment_id, str):
                comment_uuid = UUID(comment_id)
            else:
                comment_uuid = comment_id

            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()

            result = await session.execute(
                update(TaskComment)
                .where(TaskComment.id == comment_uuid)
                .values(**updates)
                .returning(TaskComment)
            )
            comment = result.scalar_one_or_none()
            return comment

    async def delete_task_comment(self, comment_id: str) -> bool:
        """Delete a task comment"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(comment_id, str):
                comment_uuid = UUID(comment_id)
            else:
                comment_uuid = comment_id

            result = await session.execute(
                delete(TaskComment).where(TaskComment.id == comment_uuid)
            )
            return result.rowcount > 0

    # Task Review Operations

    async def create_task_review(
        self,
        task_id: str,
        reviewer_agent_id: str,
        review_type: str,
        decision: str,
        summary: str,
        **kwargs,
    ) -> TaskReview:
        """Create a new task review"""
        async with self.get_session() as session:
            # Handle both string and UUID types for task_id
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            review = TaskReview(
                task_id=task_uuid,
                reviewer_agent_id=reviewer_agent_id,
                review_type=review_type,
                decision=decision,
                summary=summary,
                **kwargs,
            )
            session.add(review)
            await session.flush()
            await session.refresh(review)
            return review

    async def get_task_reviews(
        self, task_id: str, review_type: Optional[str] = None
    ) -> List[TaskReview]:
        """Get all reviews for a task"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            query = select(TaskReview).where(TaskReview.task_id == task_uuid)

            if review_type:
                query = query.where(TaskReview.review_type == review_type)

            query = query.order_by(TaskReview.created_at.desc())

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_review_by_id(self, review_id: str) -> Optional[TaskReview]:
        """Get a specific review by ID"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(review_id, str):
                review_uuid = UUID(review_id)
            else:
                review_uuid = review_id

            result = await session.execute(
                select(TaskReview).where(TaskReview.id == review_uuid)
            )
            return result.scalar_one_or_none()

    async def update_task_review(
        self, review_id: str, updates: Dict[str, Any]
    ) -> Optional[TaskReview]:
        """Update a task review"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(review_id, str):
                review_uuid = UUID(review_id)
            else:
                review_uuid = review_id

            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()

            result = await session.execute(
                update(TaskReview)
                .where(TaskReview.id == review_uuid)
                .values(**updates)
                .returning(TaskReview)
            )
            review = result.scalar_one_or_none()
            return review

    # Task Operations with Comments and Reviews

    async def get_task_with_collaboration_data(
        self, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get task with all comments and reviews"""
        task = await self.get_agent_task(task_id)
        if not task:
            return None

        comments = await self.get_task_comments(task_id)
        reviews = await self.get_task_reviews(task_id)

        task_dict = task.to_dict()
        task_dict["comments"] = [comment.to_dict() for comment in comments]
        task_dict["reviews"] = [review.to_dict() for review in reviews]

        return task_dict

    async def get_agent_task_activity(
        self, agent_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Get recent task activity for an agent"""
        async with self.get_session() as session:
            # Get recent comments
            comment_result = await session.execute(
                select(TaskComment)
                .where(TaskComment.agent_id == agent_id)
                .order_by(TaskComment.created_at.desc())
                .limit(limit)
            )
            comments = list(comment_result.scalars().all())

            # Get recent reviews
            review_result = await session.execute(
                select(TaskReview)
                .where(TaskReview.reviewer_agent_id == agent_id)
                .order_by(TaskReview.created_at.desc())
                .limit(limit)
            )
            reviews = list(review_result.scalars().all())

            return {
                "agent_id": agent_id,
                "recent_comments": [comment.to_dict() for comment in comments],
                "recent_reviews": [review.to_dict() for review in reviews],
                "total_comments": len(comments),
                "total_reviews": len(reviews),
            }

    async def update_agent_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[AgentTask]:
        """Update an agent task with new data"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()

            result = await session.execute(
                update(AgentTask)
                .where(AgentTask.id == task_uuid)
                .values(**updates)
                .returning(AgentTask)
            )
            task = result.scalar_one_or_none()
            return task

    async def create_agent_task(self, task_data: Dict[str, Any]) -> AgentTask:
        """Create a new agent task"""
        async with self.get_session() as session:
            task = AgentTask(**task_data)
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task

    async def delete_agent_task(self, task_id: str) -> bool:
        """Delete an agent task"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            result = await session.execute(
                delete(AgentTask).where(AgentTask.id == task_uuid)
            )
            return result.rowcount > 0


# Global unified database manager instance
_unified_db_manager: Optional[UnifiedDatabaseManager] = None


async def init_database():
    """Initialize the unified database (compatible with old interface)"""
    global _unified_db_manager
    try:
        _unified_db_manager = UnifiedDatabaseManager()
        await _unified_db_manager.init_database()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        # If the manager was created but init failed, try again with SQLite fallback
        if _unified_db_manager and "postgresql" in str(e).lower():
            print("Attempting SQLite fallback for database initialization...")
            _unified_db_manager = UnifiedDatabaseManager(
                "sqlite+aiosqlite:///data/summit_emergency.db"
            )
            await _unified_db_manager.init_database()
            print("Emergency SQLite database initialized successfully")
        else:
            raise


async def get_database() -> UnifiedDatabaseManager:
    """Get the unified database manager (compatible with old interface)"""
    if _unified_db_manager is None:
        await init_database()
    return _unified_db_manager


async def close_database():
    """Close database connections (compatible with old interface)"""
    if _unified_db_manager:
        await _unified_db_manager.close()


# Alias for backward compatibility
DatabaseManager = UnifiedDatabaseManager

# For compatibility with existing imports
Task = WebTask
