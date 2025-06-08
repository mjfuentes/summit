"""
PostgreSQL Database Models for Summit AI Platform
Unified database schema for all Summit components
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority enumeration"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class AgentStatus(str, Enum):
    """Agent status enumeration"""

    OFFLINE = "offline"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


class TaskSource(str, Enum):
    """Task source enumeration"""

    INTERNAL = "internal"
    GOOGLE_TASKS = "google_tasks"
    API = "api"
    MANUAL = "manual"
    WEBHOOK = "webhook"


# Core Tables


class AgentTask(Base):
    """Agent tasks for the Summit coordination system"""

    __tablename__ = "agent_tasks"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    priority = Column(
        SQLEnum(TaskPriority), nullable=False, default=TaskPriority.NORMAL
    )
    status = Column(
        SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING
    )

    # Assignment and execution
    assigned_role = Column(
        String(50), nullable=True
    )  # engineering, infrastructure, etc.
    agent_id = Column(String(100), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Task metadata
    source = Column(
        SQLEnum(TaskSource), nullable=False, default=TaskSource.INTERNAL
    )
    external_id = Column(String(200), nullable=True)  # ID from external system
    context = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Retry and timeout handling
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=300)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    logs = relationship(
        "TaskLog", back_populates="task", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_agent_tasks_status_priority", "status", "priority"),
        Index("idx_agent_tasks_assigned_role", "assigned_role"),
        Index("idx_agent_tasks_agent_id", "agent_id"),
        Index("idx_agent_tasks_created_at", "created_at"),
        Index("idx_agent_tasks_external_id", "external_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "task_type": self.task_type,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_role": self.assigned_role,
            "agent_id": self.agent_id,
            "source": self.source.value,
            "external_id": self.external_id,
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "claimed_at": (
                self.claimed_at.isoformat() if self.claimed_at else None
            ),
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class Agent(Base):
    """Agent registration and status tracking"""

    __tablename__ = "agents"

    # Primary fields
    id = Column(String(100), primary_key=True)  # agent-{uuid}
    name = Column(String(200), nullable=True)
    roles = Column(JSON, nullable=False)  # List of role names
    capabilities = Column(JSON, nullable=False)  # List of capabilities
    version = Column(String(50), nullable=True)

    # Status and health
    status = Column(
        SQLEnum(AgentStatus), nullable=False, default=AgentStatus.OFFLINE
    )
    current_task_id = Column(UUID(as_uuid=True), nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    last_task_completed = Column(DateTime, nullable=True)

    # Configuration
    max_concurrent_tasks = Column(Integer, nullable=False, default=1)
    google_tasks_list_id = Column(String(200), nullable=True)

    # Metrics
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    total_execution_time = Column(
        Float, nullable=False, default=0.0
    )  # seconds

    # Timestamps
    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    task_logs = relationship("TaskLog", back_populates="agent")

    # Indexes
    __table_args__ = (
        Index("idx_agents_status", "status"),
        Index("idx_agents_last_heartbeat", "last_heartbeat"),
        Index("idx_agents_roles", "roles"),  # GIN index for JSON searching
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "roles": self.roles,
            "capabilities": self.capabilities,
            "version": self.version,
            "status": self.status.value,
            "current_task_id": (
                str(self.current_task_id) if self.current_task_id else None
            ),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "google_tasks_list_id": self.google_tasks_list_id,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_execution_time": self.total_execution_time,
            "last_heartbeat": (
                self.last_heartbeat.isoformat()
                if self.last_heartbeat
                else None
            ),
            "last_task_completed": (
                self.last_task_completed.isoformat()
                if self.last_task_completed
                else None
            ),
            "registered_at": (
                self.registered_at.isoformat() if self.registered_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


class TaskLog(Base):
    """Detailed logging for task execution"""

    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=False
    )
    agent_id = Column(String(100), ForeignKey("agents.id"), nullable=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)  # Additional structured data
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    task = relationship("AgentTask", back_populates="logs")
    agent = relationship("Agent", back_populates="task_logs")

    # Indexes
    __table_args__ = (
        Index("idx_task_logs_task_id", "task_id"),
        Index("idx_task_logs_agent_id", "agent_id"),
        Index("idx_task_logs_timestamp", "timestamp"),
        Index("idx_task_logs_level", "level"),
    )


class AgentContext(Base):
    """Shared context data between agents"""

    __tablename__ = "agent_context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    context_type = Column(
        String(50), nullable=False
    )  # file_analysis, code_review, etc.
    key = Column(String(500), nullable=False)  # file_path, pr_number, etc.
    value = Column(JSON, nullable=False)  # The actual context data
    agent_id = Column(String(100), ForeignKey("agents.id"), nullable=False)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=True
    )

    # Metadata
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    version = Column(Integer, nullable=False, default=1)
    tags = Column(JSON, nullable=True)  # For categorization and search

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "context_type", "key", name="unique_context_type_key"
        ),
        Index("idx_agent_context_type", "context_type"),
        Index("idx_agent_context_key", "key"),
        Index("idx_agent_context_agent_id", "agent_id"),
        Index("idx_agent_context_task_id", "task_id"),
        Index("idx_agent_context_expires_at", "expires_at"),
    )


class WebTask(Base):
    """Web application tasks (from autonomous_server.py)"""

    __tablename__ = "web_tasks"

    # Primary fields
    task_id = Column(String(36), primary_key=True)
    task_description = Column(Text, nullable=False)
    repository_url = Column(String(500))
    github_token = Column(String(200))  # Will be encrypted in production
    target_branch = Column(String(100))
    timeout_minutes = Column(Integer, default=60)
    save_word = Column(String(100))
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Text)
    logs = Column(JSON, default=list)  # Store as JSON array

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at = Column(DateTime)

    # Execution details
    container_id = Column(String(100))
    claude_code_url = Column(String(200))
    log_file = Column(String(500))
    full_logs = Column(Text)
    error = Column(Text)
    is_active = Column(Boolean, default=True)

    # CI/CD tracking fields
    pr_number = Column(Integer)  # GitHub PR number
    pr_url = Column(String(500))  # GitHub PR URL
    commit_sha = Column(String(40))  # Git commit SHA
    branch_name = Column(String(100))
    ci_status = Column(
        String(20)
    )  # CI/CD status: pending, success, failure, error
    workflow_runs = Column(JSON, default=list)  # Store workflow run data
    last_ci_check = Column(DateTime)  # Last time CI status was checked

    # Enhanced task metadata fields
    task_name = Column(String(200))  # Concise task name
    task_scope = Column(String(20))  # small, medium, large
    task_priority = Column(String(20))  # low, medium, high
    task_type = Column(String(50))  # bug_fix, feature, refactor, etc.
    estimated_duration_minutes = Column(Integer)  # Estimated duration
    requirements = Column(Text)  # JSON string of requirements
    acceptance_criteria = Column(Text)  # JSON string of acceptance criteria
    user_context = Column(Text)  # Additional context from user

    # Indexes
    __table_args__ = (
        Index("idx_web_tasks_status", "status"),
        Index("idx_web_tasks_created_at", "created_at"),
        Index("idx_web_tasks_is_active", "is_active"),
        Index("idx_web_tasks_task_type", "task_type"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary format"""
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "repository_url": self.repository_url,
            "github_token": self.github_token,
            "target_branch": self.target_branch,
            "timeout_minutes": self.timeout_minutes,
            "save_word": self.save_word,
            "status": self.status,
            "progress": self.progress,
            "logs": self.logs or [],
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "container_id": self.container_id,
            "claude_code_url": self.claude_code_url,
            "log_file": self.log_file,
            "full_logs": self.full_logs,
            "error": self.error,
            "is_active": self.is_active,
            # CI/CD fields
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "commit_sha": self.commit_sha,
            "branch_name": self.branch_name,
            "ci_status": self.ci_status,
            "workflow_runs": self.workflow_runs or [],
            "last_ci_check": (
                self.last_ci_check.isoformat() if self.last_ci_check else None
            ),
            # Enhanced task metadata
            "task_name": self.task_name,
            "task_scope": self.task_scope,
            "task_priority": self.task_priority,
            "task_type": self.task_type,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "requirements": self.requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "user_context": self.user_context,
        }


# Database connection and session management


class DatabaseManager:
    """PostgreSQL database manager with connection pooling"""

    def __init__(self, database_url: str):
        self.database_url = database_url

        # Configure engine options based on database type
        engine_kwargs = {"echo": False}  # Set to True for SQL debugging

        if "postgresql" in database_url:
            # PostgreSQL-specific pool settings
            engine_kwargs.update(
                {
                    "pool_size": 20,  # For 20 concurrent agents
                    "max_overflow": 30,  # Additional connections during spikes
                    "pool_timeout": 30,  # Wait up to 30 seconds for connection
                    "pool_recycle": 3600,  # Recycle connections every hour
                }
            )
        # SQLite doesn't support pool settings

        self.engine = create_async_engine(database_url, **engine_kwargs)
        self.SessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_database(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.SessionLocal()

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database_manager(database_url: str):
    """Initialize the global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_database_manager() -> DatabaseManager:
    """Get the global database manager"""
    if _db_manager is None:
        raise RuntimeError(
            "Database manager not initialized. Call init_database_manager() first."
        )
    return _db_manager
