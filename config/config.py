#!/usr/bin/env python3

import os

# API Configuration
ANTHROPIC_API_KEY = "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"
OPENAI_API_KEY = "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"

# Summit Configuration
SUMMIT_CONFIG = {
    "daily_budget": 10.0,
    "hourly_budget": 2.0,
    "max_recursion_depth": 3,
    "embedding_model": "text-embedding-3-small",
    "chat_model": "claude-sonnet-4-20250514",
}

# Database Configuration
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/tasks.db"),
    "task_retention_days": int(os.getenv("TASK_RETENTION_DAYS", "90")),
    "max_completed_tasks": int(
        os.getenv("MAX_COMPLETED_TASKS_IN_MEMORY", "50")
    ),
    "auto_cleanup_enabled": os.getenv("AUTO_CLEANUP_ENABLED", "true").lower()
    == "true",
    "cleanup_interval_hours": int(os.getenv("CLEANUP_INTERVAL_HOURS", "24")),
}


def setup_environment():
    """Set up environment variables from config"""
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
