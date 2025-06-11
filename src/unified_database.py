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
    TaskLifecycleHistory,
    TaskLifecycleStage,
    TaskLog,
    TaskPriority,
    TaskReview,
    TaskSource,
    TaskStatus,
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
                # Detect environment type
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

                # Detect production/Kubernetes environment
                is_production = any(
                    [
                        os.getenv("ENVIRONMENT") == "production",
                        os.getenv(
                            "KUBERNETES_SERVICE_HOST"
                        ),  # Running in Kubernetes
                        os.getenv("NODE_ENV") == "production",
                    ]
                )

                if is_ci:
                    # Use SQLite for CI/CD environments only
                    db_dir = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), "data"
                    )
                    os.makedirs(db_dir, exist_ok=True)
                    database_url = f"sqlite+aiosqlite:///{db_dir}/summit_ci.db"
                    print(
                        f"CI environment detected, using SQLite: {database_url}"
                    )
                elif is_production:
                    # Production must use PostgreSQL - no fallback
                    raise RuntimeError(
                        "Production environment detected but DATABASE_URL not set. "
                        "PostgreSQL connection is required for production deployments."
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
                        # Fall back to SQLite for development only
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
        init_database_manager(database_url)
        self.db_manager = get_database_manager()

    async def init_database(self):
        """Initialize all database tables - PostgreSQL only for production"""
        # Check if we're in production environment
        is_production = any(
            [
                os.getenv("ENVIRONMENT") == "production",
                os.getenv("KUBERNETES_SERVICE_HOST"),  # Running in Kubernetes
                os.getenv("NODE_ENV") == "production",
            ]
        )

        try:
            await self.db_manager.init_database()
            print(
                f"Database initialized successfully: {self.db_manager.database_url}"
            )
        except Exception as e:
            if is_production:
                # In production, fail fast - no SQLite fallback
                print(
                    f"FATAL: Database initialization failed in production environment: {e}"
                )
                print(
                    "PostgreSQL connection is required for production. Check your DATABASE_URL and database connectivity."
                )
                raise
            elif "postgresql" in self.db_manager.database_url.lower():
                # Only allow SQLite fallback in development/CI environments
                print(f"PostgreSQL connection failed: {e}")
                print("Falling back to SQLite for development environment...")

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

    # Web Task Operations removed - migrated to AgentTask for MCP-based architecture

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
        Atomically claim a task for an agent using database-level atomic updates.

        Note: This implementation uses database locking for atomicity. For high
        throughput scenarios, consider using Cloud Tasks or Redis pub/sub for
        better task distribution and reduced database contention.
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

    # Task Lifecycle Operations

    async def transition_task_stage(
        self,
        task_id: str,
        agent_id: str,
        to_stage: TaskLifecycleStage,
        stage_output: Optional[Dict[str, Any]] = None,
        stage_summary: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
        quality_score: Optional[float] = None,
        completion_status: str = "completed",
        transition_reason: Optional[str] = None,
        stage_metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskLifecycleHistory:
        """Transition a task to a new lifecycle stage and record the history"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            # Get the current task to determine the from_stage
            result = await session.execute(
                select(AgentTask).where(AgentTask.id == task_uuid)
            )
            task = result.scalar_one_or_none()
            if not task:
                raise ValueError(f"Task {task_id} not found")

            from_stage = task.lifecycle_stage

            # Update the task's lifecycle stage
            await session.execute(
                update(AgentTask)
                .where(AgentTask.id == task_uuid)
                .values(lifecycle_stage=to_stage, updated_at=datetime.utcnow())
            )

            # Create the lifecycle history record
            lifecycle_history = TaskLifecycleHistory(
                task_id=task_uuid,
                agent_id=agent_id,
                from_stage=from_stage,
                to_stage=to_stage,
                completed_at=datetime.utcnow(),
                stage_output=stage_output,
                stage_summary=stage_summary,
                files_modified=files_modified,
                quality_score=quality_score,
                completion_status=completion_status,
                transition_reason=transition_reason,
                stage_metadata=stage_metadata,
            )

            # Calculate duration if we have a previous stage entry
            if from_stage:
                # Find the most recent history entry for the from_stage
                prev_result = await session.execute(
                    select(TaskLifecycleHistory)
                    .where(
                        TaskLifecycleHistory.task_id == task_uuid,
                        TaskLifecycleHistory.to_stage == from_stage,
                    )
                    .order_by(TaskLifecycleHistory.started_at.desc())
                    .limit(1)
                )
                prev_history = prev_result.scalar_one_or_none()
                if prev_history:
                    duration = (
                        lifecycle_history.completed_at
                        - prev_history.started_at
                    ).total_seconds()
                    lifecycle_history.duration_seconds = int(duration)

            session.add(lifecycle_history)
            await session.flush()
            await session.refresh(lifecycle_history)
            return lifecycle_history

    async def start_stage_work(
        self,
        task_id: str,
        agent_id: str,
        stage: TaskLifecycleStage,
        stage_metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskLifecycleHistory:
        """Start work on a lifecycle stage (records start time)"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            # Create the lifecycle history record for stage start
            lifecycle_history = TaskLifecycleHistory(
                task_id=task_uuid,
                agent_id=agent_id,
                from_stage=None,  # Will be set on completion
                to_stage=stage,
                completion_status="in_progress",
                stage_metadata=stage_metadata,
            )

            session.add(lifecycle_history)
            await session.flush()
            await session.refresh(lifecycle_history)
            return lifecycle_history

    async def complete_stage_work(
        self,
        lifecycle_history_id: str,
        stage_output: Optional[Dict[str, Any]] = None,
        stage_summary: Optional[str] = None,
        files_modified: Optional[List[str]] = None,
        quality_score: Optional[float] = None,
        completion_status: str = "completed",
        transition_reason: Optional[str] = None,
    ) -> TaskLifecycleHistory:
        """Complete work on a lifecycle stage (records completion and duration)"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(lifecycle_history_id, str):
                history_uuid = UUID(lifecycle_history_id)
            else:
                history_uuid = lifecycle_history_id

            # Update the history record
            completed_at = datetime.utcnow()
            updates = {
                "completed_at": completed_at,
                "stage_output": stage_output,
                "stage_summary": stage_summary,
                "files_modified": files_modified,
                "quality_score": quality_score,
                "completion_status": completion_status,
                "transition_reason": transition_reason,
                "updated_at": completed_at,
            }

            # Get the current record to calculate duration
            result = await session.execute(
                select(TaskLifecycleHistory).where(
                    TaskLifecycleHistory.id == history_uuid
                )
            )
            history = result.scalar_one_or_none()
            if history:
                duration = (completed_at - history.started_at).total_seconds()
                updates["duration_seconds"] = int(duration)

            result = await session.execute(
                update(TaskLifecycleHistory)
                .where(TaskLifecycleHistory.id == history_uuid)
                .values(**updates)
                .returning(TaskLifecycleHistory)
            )
            return result.scalar_one()

    async def get_task_lifecycle_history(
        self, task_id: str
    ) -> List[TaskLifecycleHistory]:
        """Get the complete lifecycle history for a task"""
        async with self.get_session() as session:
            # Handle both string and UUID types
            if isinstance(task_id, str):
                task_uuid = UUID(task_id)
            else:
                task_uuid = task_id

            result = await session.execute(
                select(TaskLifecycleHistory)
                .where(TaskLifecycleHistory.task_id == task_uuid)
                .order_by(TaskLifecycleHistory.started_at)
            )
            return list(result.scalars().all())

    async def get_stage_metrics(
        self, stage: TaskLifecycleStage, days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for a specific lifecycle stage"""
        async with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get stage completion data
            result = await session.execute(
                select(TaskLifecycleHistory).where(
                    TaskLifecycleHistory.to_stage == stage,
                    TaskLifecycleHistory.started_at >= cutoff_date,
                    TaskLifecycleHistory.completion_status == "completed",
                )
            )
            completed_stages = list(result.scalars().all())

            if not completed_stages:
                return {
                    "stage": stage.value,
                    "total_completed": 0,
                    "average_duration_minutes": 0,
                    "average_quality_score": 0,
                    "agents_involved": [],
                }

            # Calculate metrics
            durations = [
                s.duration_seconds
                for s in completed_stages
                if s.duration_seconds
            ]
            quality_scores = [
                s.quality_score for s in completed_stages if s.quality_score
            ]
            agents = list(set(s.agent_id for s in completed_stages))

            return {
                "stage": stage.value,
                "total_completed": len(completed_stages),
                "average_duration_minutes": (
                    sum(durations) / len(durations) / 60 if durations else 0
                ),
                "average_quality_score": (
                    sum(quality_scores) / len(quality_scores)
                    if quality_scores
                    else 0
                ),
                "agents_involved": agents,
                "median_duration_minutes": (
                    sorted(durations)[len(durations) // 2] / 60
                    if durations
                    else 0
                ),
            }


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
# Legacy compatibility removed - WebTask migrated to AgentTask for MCP architecture
