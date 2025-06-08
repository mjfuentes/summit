#!/usr/bin/env python3
"""
Database Migration Script
Adds missing columns to existing Summit database
"""

import os
import sqlite3
import sys
from pathlib import Path

# Add src directory to path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
sys.path.insert(0, str(src_dir))


def migrate_database():
    """Add missing columns to existing database"""

    # Find database file
    db_paths = [
        "web/tasks.db",
        "web/data/tasks.db",
        "data/tasks.db",
        "tasks.db",
    ]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("No existing database found. Creating new one...")
        return

    print(f"Migrating database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(tasks)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Define new columns to add
    new_columns = {
        "task_name": "VARCHAR(200)",
        "task_scope": "VARCHAR(20)",
        "task_priority": "VARCHAR(20)",
        "task_type": "VARCHAR(50)",
        "estimated_duration_minutes": "INTEGER",
        "requirements": "TEXT",
        "acceptance_criteria": "TEXT",
        "user_context": "TEXT",
    }

    # Add missing columns
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(
                    f"ALTER TABLE tasks ADD COLUMN {column_name} {column_type}"
                )
                print(f"Added column: {column_name}")
            except sqlite3.Error as e:
                print(f"Error adding column {column_name}: {e}")

    # Commit changes
    conn.commit()
    conn.close()

    print("Database migration completed!")


if __name__ == "__main__":
    migrate_database()
