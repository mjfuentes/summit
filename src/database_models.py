"""
PostgreSQL Database Models for Summit AI Platform
Unified database schema for all Summit components
"""

import json
import os
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def get_json_type(postgresql_optimal=False):
    """
    Get appropriate JSON type based on database compatibility requirements.

    Args:
        postgresql_optimal: If True, use JSONB for PostgreSQL (enables GIN indexes)
                          If False, use JSON for broader compatibility
    """
    if postgresql_optimal:
        return JSONB
    else:
        return JSON


def is_postgresql_environment():
    """
    Detect if we're in a PostgreSQL environment where JSONB optimization should be enabled.
    """
    database_url = os.getenv("DATABASE_URL", "")

    # Check if running in production/Kubernetes with PostgreSQL
    is_production = any(
        [
            os.getenv("ENVIRONMENT") == "production",
            os.getenv("KUBERNETES_SERVICE_HOST"),  # Running in Kubernetes
            os.getenv("NODE_ENV") == "production",
        ]
    )

    # Check if PostgreSQL is explicitly configured
    is_postgresql = "postgresql" in database_url.lower()

    # Enable JSONB optimization for production PostgreSQL environments
    return is_production and is_postgresql


# Determine optimal JSON type for this environment
OPTIMAL_JSON_TYPE = get_json_type(
    postgresql_optimal=is_postgresql_environment()
)


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
    payload = Column(OPTIMAL_JSON_TYPE, nullable=False)
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
    context = Column(OPTIMAL_JSON_TYPE, nullable=False, default=dict)
    result = Column(OPTIMAL_JSON_TYPE, nullable=True)
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
    roles = Column(OPTIMAL_JSON_TYPE, nullable=False)  # List of role names
    capabilities = Column(
        OPTIMAL_JSON_TYPE, nullable=False
    )  # List of capabilities
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
    ) + (
        # Add GIN indexes for PostgreSQL JSONB optimization
        (
            Index("idx_agents_roles", "roles", postgresql_using="gin"),
            Index(
                "idx_agents_capabilities",
                "capabilities",
                postgresql_using="gin",
            ),
        )
        if is_postgresql_environment()
        else ()
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
    context = Column(
        OPTIMAL_JSON_TYPE, nullable=True
    )  # Additional structured data
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
    value = Column(
        OPTIMAL_JSON_TYPE, nullable=False
    )  # The actual context data
    agent_id = Column(String(100), ForeignKey("agents.id"), nullable=False)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=True
    )

    # Metadata
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    version = Column(Integer, nullable=False, default=1)
    tags = Column(
        OPTIMAL_JSON_TYPE, nullable=True
    )  # For categorization and search

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


class TaskComment(Base):
    """Comments and reviews on tasks by agents"""

    __tablename__ = "task_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=False
    )
    agent_id = Column(String(100), ForeignKey("agents.id"), nullable=False)
    comment_type = Column(
        String(50), nullable=False
    )  # comment, review, approval, rejection, question
    content = Column(Text, nullable=False)

    # Structured data for different comment types
    comment_metadata = Column(
        OPTIMAL_JSON_TYPE, nullable=True
    )  # Additional structured data

    # Review-specific fields
    rating = Column(Integer, nullable=True)  # 1-5 rating scale
    approval_status = Column(
        String(20), nullable=True
    )  # approved, rejected, needs_changes, pending

    # Threading support
    parent_comment_id = Column(
        UUID(as_uuid=True), ForeignKey("task_comments.id"), nullable=True
    )

    # Status and visibility
    is_internal = Column(
        Boolean, nullable=False, default=False
    )  # Internal agent communication
    is_resolved = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    task = relationship("AgentTask", backref="comments")
    agent = relationship("Agent")
    parent_comment = relationship(
        "TaskComment", remote_side=[id], backref="replies"
    )

    # Indexes
    __table_args__ = (
        Index("idx_task_comments_task_id", "task_id"),
        Index("idx_task_comments_agent_id", "agent_id"),
        Index("idx_task_comments_type", "comment_type"),
        Index("idx_task_comments_created_at", "created_at"),
        Index("idx_task_comments_approval_status", "approval_status"),
        Index("idx_task_comments_parent_id", "parent_comment_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "agent_id": self.agent_id,
            "comment_type": self.comment_type,
            "content": self.content,
            "metadata": self.comment_metadata,
            "rating": self.rating,
            "approval_status": self.approval_status,
            "parent_comment_id": (
                str(self.parent_comment_id) if self.parent_comment_id else None
            ),
            "is_internal": self.is_internal,
            "is_resolved": self.is_resolved,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


class TaskReview(Base):
    """Structured reviews for task evaluation"""

    __tablename__ = "task_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_tasks.id"), nullable=False
    )
    reviewer_agent_id = Column(
        String(100), ForeignKey("agents.id"), nullable=False
    )
    review_type = Column(
        String(50), nullable=False
    )  # code_review, security_review, performance_review, etc.

    # Review decision
    decision = Column(
        String(20), nullable=False
    )  # approved, rejected, needs_changes, conditional
    confidence = Column(
        Float, nullable=False, default=1.0
    )  # 0.0 to 1.0 confidence level

    # Review content
    summary = Column(Text, nullable=False)
    findings = Column(
        OPTIMAL_JSON_TYPE, nullable=False, default=list
    )  # List of findings
    recommendations = Column(
        OPTIMAL_JSON_TYPE, nullable=False, default=list
    )  # List of recommendations

    # Scoring
    quality_score = Column(Float, nullable=True)  # 0.0 to 10.0
    complexity_score = Column(Float, nullable=True)  # 0.0 to 10.0
    risk_score = Column(Float, nullable=True)  # 0.0 to 10.0

    # Review metadata
    review_criteria = Column(
        OPTIMAL_JSON_TYPE, nullable=True
    )  # Criteria used for review
    review_duration_seconds = Column(Integer, nullable=True)
    files_reviewed = Column(
        OPTIMAL_JSON_TYPE, nullable=True
    )  # List of files reviewed

    # Status
    is_final = Column(Boolean, nullable=False, default=True)
    superseded_by = Column(
        UUID(as_uuid=True), ForeignKey("task_reviews.id"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    task = relationship("AgentTask", backref="reviews")
    reviewer = relationship("Agent")
    superseding_review = relationship(
        "TaskReview", remote_side=[id], backref="superseded_reviews"
    )

    # Indexes
    __table_args__ = (
        Index("idx_task_reviews_task_id", "task_id"),
        Index("idx_task_reviews_reviewer_id", "reviewer_agent_id"),
        Index("idx_task_reviews_type", "review_type"),
        Index("idx_task_reviews_decision", "decision"),
        Index("idx_task_reviews_created_at", "created_at"),
        Index("idx_task_reviews_is_final", "is_final"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "reviewer_agent_id": self.reviewer_agent_id,
            "review_type": self.review_type,
            "decision": self.decision,
            "confidence": self.confidence,
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "quality_score": self.quality_score,
            "complexity_score": self.complexity_score,
            "risk_score": self.risk_score,
            "review_criteria": self.review_criteria,
            "review_duration_seconds": self.review_duration_seconds,
            "files_reviewed": self.files_reviewed,
            "is_final": self.is_final,
            "superseded_by": (
                str(self.superseded_by) if self.superseded_by else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


# WebTask model removed - migrated to AgentTask for MCP-based architecture


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
