#!/usr/bin/env python3
"""
Database models and connection handling for Summit task persistence.
Provides SQLite-based storage for tasks to survive pod restarts.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Boolean
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete
from contextlib import asynccontextmanager

Base = declarative_base()

class Task(Base):
    """SQLAlchemy model for tasks"""
    __tablename__ = 'tasks'
    
    task_id = Column(String(36), primary_key=True)
    task_description = Column(Text, nullable=False)
    repository_url = Column(String(500))
    github_token = Column(String(200))  # Will be encrypted in production
    target_branch = Column(String(100))
    timeout_minutes = Column(Integer, default=60)
    save_word = Column(String(100))
    status = Column(String(20), nullable=False, default='pending')
    progress = Column(Text)
    logs = Column(JSON, default=list)  # Store as JSON array
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    container_id = Column(String(100))
    claude_code_url = Column(String(200))
    log_file = Column(String(500))
    full_logs = Column(Text)
    error = Column(Text)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary format"""
        return {
            'task_id': self.task_id,
            'task_description': self.task_description,
            'repository_url': self.repository_url,
            'github_token': self.github_token,
            'target_branch': self.target_branch,
            'timeout_minutes': self.timeout_minutes,
            'save_word': self.save_word,
            'status': self.status,
            'progress': self.progress,
            'logs': self.logs or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'container_id': self.container_id,
            'claude_code_url': self.claude_code_url,
            'log_file': self.log_file,
            'full_logs': self.full_logs,
            'error': self.error,
            'is_active': self.is_active
        }

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Default to SQLite database in data directory
            db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(db_dir, exist_ok=True)
            database_url = f"sqlite+aiosqlite:///{db_dir}/tasks.db"
        
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.SessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_database(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with proper cleanup"""
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task in the database"""
        async with self.get_session() as session:
            # Convert datetime strings to datetime objects if needed
            if isinstance(task_data.get('created_at'), str):
                task_data['created_at'] = datetime.fromisoformat(task_data['created_at'].replace('Z', '+00:00'))
            
            task = Task(**task_data)
            session.add(task)
            await session.flush()
            await session.refresh(task)
            return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        async with self.get_session() as session:
            result = await session.execute(select(Task).where(Task.task_id == task_id))
            return result.scalar_one_or_none()
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update a task with new data"""
        async with self.get_session() as session:
            # Add updated_at timestamp
            updates['updated_at'] = datetime.utcnow()
            
            # Handle completed_at timestamp
            if updates.get('status') in ['completed', 'failed', 'timeout', 'stopped']:
                if not updates.get('completed_at'):
                    updates['completed_at'] = datetime.utcnow()
            
            result = await session.execute(
                update(Task)
                .where(Task.task_id == task_id)
                .values(**updates)
                .returning(Task)
            )
            task = result.scalar_one_or_none()
            return task
    
    async def get_active_tasks(self) -> List[Task]:
        """Get all active tasks"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.is_active == True)
                .order_by(Task.created_at.desc())
            )
            return result.scalars().all()
    
    async def get_completed_tasks(self, limit: int = 50) -> List[Task]:
        """Get completed tasks (most recent first)"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.is_active == False)
                .order_by(Task.completed_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def mark_task_inactive(self, task_id: str) -> Optional[Task]:
        """Mark a task as inactive (move to history)"""
        return await self.update_task(task_id, {'is_active': False})
    
    async def get_all_tasks(self, limit: int = 100) -> List[Task]:
        """Get all tasks (active and inactive)"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Task)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    async def delete_old_tasks(self, days_old: int = 30):
        """Delete tasks older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        async with self.get_session() as session:
            await session.execute(
                delete(Task)
                .where(Task.created_at < cutoff_date)
                .where(Task.is_active == False)
            )
    
    async def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics"""
        async with self.get_session() as session:
            # Count by status
            from sqlalchemy import func
            result = await session.execute(
                select(Task.status, func.count(Task.task_id).label('count'))
                .group_by(Task.status)
            )
            status_counts = {row.status: row.count for row in result}
            
            # Count active vs inactive
            active_result = await session.execute(
                select(func.count(Task.task_id)).where(Task.is_active == True)
            )
            active_count = active_result.scalar()
            
            total_result = await session.execute(
                select(func.count(Task.task_id))
            )
            total_count = total_result.scalar()
            
            return {
                'total_tasks': total_count,
                'active_tasks': active_count,
                'completed_tasks': total_count - active_count,
                'status_distribution': status_counts
            }
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

async def get_database() -> DatabaseManager:
    """Get the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        await db_manager.init_database()
    return db_manager

async def init_database():
    """Initialize the database (call this on startup)"""
    await get_database()

async def close_database():
    """Close database connections (call this on shutdown)"""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None