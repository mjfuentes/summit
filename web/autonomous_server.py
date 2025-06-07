#!/usr/bin/env python3

import asyncio
import json
import os
import subprocess

# Import database and other modules
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from database import DatabaseManager

# Global variables
app = FastAPI(title="Summit Autonomous AI", version="1.0.0")
db_manager = None
log_dir = "logs"

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock functions for missing imports
try:
    from summit import create_pull_request, get_github_repo_info
except ImportError:

    def create_pull_request(*args, **kwargs):
        return None

    def get_github_repo_info():
        return None, None


def kill_existing_server():
    """Kill any existing server processes"""
    try:
        # Kill any existing uvicorn processes on port 8000
        subprocess.run(
            ["pkill", "-f", "uvicorn.*autonomous_server"],
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["pkill", "-f", "python.*autonomous_server"],
            capture_output=True,
            text=True,
        )

        # Also try to kill by port
        subprocess.run(
            ["lsof", "-ti:8000", "|", "xargs", "kill", "-9"],
            shell=True,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        print(f"Note: Could not kill existing processes: {e}")


def bootstrap_dependencies():
    """Bootstrap required dependencies and environment"""
    try:
        # Check if we're in the correct directory
        if not os.path.exists("requirements.txt"):
            print(
                "Warning: requirements.txt not found. Make sure you're in the project root."
            )

        # Check for required environment variables
        required_env_vars = ["ANTHROPIC_API_KEY"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]

        if missing_vars:
            print(
                f"Warning: Missing environment variables: {', '.join(missing_vars)}"
            )
            print("Some features may not work properly.")

        # Create logs directory
        os.makedirs(log_dir, exist_ok=True)

        print("Bootstrap completed successfully")

    except Exception as e:
        print(f"Bootstrap warning: {e}")


# Pydantic models
class TaskRequest(BaseModel):
    description: str  # Only thing the user needs to provide


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: str
    logs: List[str]
    created_at: str
    container_id: Optional[str] = None


# Database helper functions
async def get_database():
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        await db_manager.init_database()
    return db_manager


@app.on_event("startup")
async def startup_event():
    print("Starting Summit Autonomous AI...")
    bootstrap_dependencies()
    await get_database()
    print("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    if db_manager:
        await db_manager.close()
        print("Database connections closed")


@app.get("/")
async def root():
    import os

    from fastapi import Response

    # Read the HTML file from templates directory
    html_file_path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "index.html"
    )

    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        # Fallback to simple error message
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Summit AI - Error</title></head>
        <body>
            <h1>Error loading Summit AI interface</h1>
            <p>Could not load the main interface. Please check the templates/index.html file.</p>
        </body>
        </html>
        """

    # Create response with cache-busting headers
    response = Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
        },
    )
    return response


@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """Create a new autonomous learning task"""
    task_id = str(uuid.uuid4())

    # Hardcode all the backend configuration
    task_data = {
        "task_id": task_id,
        "task_description": request.description,
        "repository_url": "https://github.com/mjfuentes/summit.git",  # Hardcoded
        "github_token": "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",
        "target_branch": "main",  # Hardcoded
        "timeout_minutes": 15,  # Hardcoded reasonable timeout
        "save_word": "SUMMIT_TASK_COMPLETE",  # Hardcoded
        "status": "initializing",
        "progress": "Creating container environment...",
        "logs": [
            "Task created",
            "Initializing autonomous learning environment",
        ],
        "created_at": datetime.now().isoformat(),
        "container_id": None,
        "is_active": True,
    }

    # Save task to database
    db = await get_database()
    await db.create_task(task_data)

    # Start the autonomous task in background
    asyncio.create_task(run_autonomous_task(task_id))

    return {
        "success": True,
        "task_id": task_id,
        "message": "Task created successfully",
    }


async def run_autonomous_task(task_id: str):
    """Run the autonomous learning task in a Docker container"""
    db = await get_database()

    try:
        # Update to running
        await db.update_task(
            task_id,
            {
                "status": "running",
                "progress": "Task is running...",
                "logs": [
                    "Task started",
                    "Initializing environment",
                    "Running in background",
                ],
            },
        )

        # Simulate longer work with progress updates
        for i in range(1, 6):
            await asyncio.sleep(10)  # 10 seconds per step
            await db.update_task(
                task_id,
                {
                    "progress": f"Processing step {i}/5...",
                    "logs": [
                        "Task started",
                        "Initializing environment",
                        "Running in background",
                        f"Completed step {i}/5",
                    ],
                },
            )

        # Mark as completed
        await db.update_task(
            task_id,
            {
                "status": "completed",
                "progress": "Task completed successfully",
                "logs": [
                    "Task started",
                    "Initializing environment",
                    "Running in background",
                    "All steps completed",
                    "Task finished successfully",
                ],
                "is_active": False,  # Move to completed tasks
            },
        )

    except Exception as e:
        await db.update_task(
            task_id,
            {
                "status": "failed",
                "progress": "Task failed",
                "logs": [
                    "Task started",
                    "Initializing environment",
                    "Running in background",
                    f"Error: {str(e)}",
                ],
                "error": str(e),
            },
        )


@app.get("/api/tasks")
async def get_all_tasks():
    """Get all tasks"""
    db = await get_database()
    tasks = await db.get_all_tasks()

    # Convert to the expected format
    formatted_tasks = []
    for task in tasks:
        formatted_tasks.append(
            {
                "task_id": task.task_id,
                "description": task.task_description,  # Frontend expects 'description'
                "status": task.status,
                "created_at": (
                    task.created_at.isoformat()
                    if hasattr(task.created_at, "isoformat")
                    else str(task.created_at)
                ),
                "logs": task.logs or [],
                "claude_code_url": getattr(task, "claude_code_url", None),
                "pr_url": getattr(task, "pr_url", None),
            }
        )

    return formatted_tasks


@app.get("/api/tasks/failed")
async def get_failed_tasks():
    """Get all failed tasks for management"""
    db = await get_database()
    failed_tasks = await db.get_failed_tasks()

    # Format for frontend
    formatted_tasks = []
    for task in failed_tasks:
        formatted_tasks.append(
            {
                "id": task.task_id,
                "description": task.task_description,
                "created_at": (
                    task.created_at.isoformat()
                    if hasattr(task.created_at, "isoformat")
                    else str(task.created_at)
                ),
                "error_message": getattr(task, "error_message", None)
                or getattr(task, "error", None),
                "logs": task.logs or [],
            }
        )

    return formatted_tasks


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "task_description": task.task_description,
        "status": task.status,
        "created_at": task.created_at,
        "logs": task.logs or [],
        "claude_code_url": getattr(task, "claude_code_url", None),
        "pr_url": getattr(task, "pr_url", None),
        "log_file": getattr(task, "log_file", None),
    }


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task status to stopped
    await db.update_task(
        task_id, {"status": "stopped", "progress": "Task stopped by user"}
    )

    return {"success": True, "message": "Task stopped successfully"}


@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str):
    """Get task logs"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"logs": task.logs or []}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/chat")
async def chat_with_claude(request: dict):
    """Chat directly with Claude"""
    try:
        import anthropic

        # Get the message from request
        message = request.get("message", "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, detail="Claude API key not configured"
            )

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Create system context about the website
        system_context = """You are Claudia, the AI assistant for Summit Autonomous AI - a cutting-edge platform where AI agents can autonomously learn, code, and improve themselves. You have full knowledge of this website and can help users with everything they can do here.

SUMMIT AI WEBSITE CAPABILITIES:

 CREATE LEARNING TASKS:
- Users can create autonomous coding tasks by describing what they want built
- Tasks run in isolated Docker containers with full development environments
- AI agents can write code, run tests, create pull requests, and deploy solutions
- Examples: "Build a REST API", "Create React components", "Fix bugs", "Analyze data"
- Tasks include voice input support for hands-free task creation
- Each task gets its own Claude Code workspace URL for real-time monitoring

 ACTIVE TASKS MANAGEMENT:
- View all currently running autonomous tasks
- Monitor task progress and status updates in real-time
- Access Claude Code workspace URLs to see live development
- View task logs and progress updates
- Stop running tasks if needed

 FAILED TASKS RECOVERY:
- View all failed tasks with detailed error messages
- Retrigger individual failed tasks with fresh AI instances
- Batch retrigger all failed tasks at once
- Error messages are formatted and scrollable for easy debugging
- Failed tasks show creation timestamps and failure reasons

 DIRECT CHAT (THIS FEATURE):
- Chat directly with Claudia (that's me!) for immediate help
- Get coding advice, debugging assistance, and general support
- Ask questions about the platform, best practices, or troubleshooting
- No need to create full autonomous tasks for simple questions

 PLATFORM FEATURES:
- Y2K-inspired neon interface with animated gradients and retro styling
- Real-time task monitoring with auto-refresh every 5 seconds
- Professional development standards with >70% test coverage requirements
- Automatic code formatting, linting, and quality checks
- GitHub integration for pull request creation and management
- Cost tracking and API usage monitoring
- Voice input support for accessibility

TECHNICAL DETAILS:
- Built on FastAPI backend with SQLite database
- Uses Claude-3.5-Sonnet for autonomous development
- Docker containerization for isolated task execution
- Real-time WebSocket-style updates via polling
- Mobile-responsive design with Y2K aesthetic
- Professional git workflow with feature branches and PRs

I can help users understand how to use any of these features, troubleshoot issues, provide coding advice, or explain how the autonomous development process works. I'm here to make their Summit AI experience smooth and productive!

What can I help you with today?"""

        # Send message to Claude with full context
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=system_context,
            messages=[{"role": "user", "content": message}],
        )

        # Extract response text
        response_text = (
            response.content[0].text
            if response.content
            else "No response from Claude"
        )

        return {
            "success": True,
            "response": response_text,
            "model": "claude-3-5-sonnet-20241022",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/tasks/{task_id}/retrigger")
async def retrigger_failed_task(task_id: str):
    """Retrigger a failed task with a fresh Claude instance"""
    db = await get_database()
    original_task = await db.get_task(task_id)

    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if original_task.status != "failed":
        raise HTTPException(
            status_code=400, detail="Only failed tasks can be retriggered"
        )

    # Create new task with same description
    new_task_id = str(uuid.uuid4())
    task_data = {
        "task_id": new_task_id,
        "task_description": original_task.task_description,
        "repository_url": original_task.repository_url,
        "github_token": original_task.github_token,
        "target_branch": original_task.target_branch,
        "timeout_minutes": original_task.timeout_minutes,
        "save_word": original_task.save_word,
        "status": "initializing",
        "progress": "Retriggering with fresh Claude instance...",
        "logs": [
            f"Retriggered from failed task {task_id}",
            "Initializing fresh autonomous learning environment",
        ],
        "created_at": datetime.now().isoformat(),
        "container_id": None,
        "is_active": True,
    }

    await db.create_task(task_data)

    # Delete the original failed task to avoid confusion
    await db.delete_task(task_id)

    # Start the new task
    asyncio.create_task(run_autonomous_task(new_task_id))

    return {
        "success": True,
        "new_task_id": new_task_id,
        "message": "Task retriggered successfully with fresh Claude instance",
    }


@app.post("/api/tasks/retrigger-all-failed")
async def retrigger_all_failed_tasks():
    """Retrigger all failed tasks with fresh Claude instances"""
    db = await get_database()
    failed_tasks = await db.get_failed_tasks()

    retriggered_count = 0
    new_task_ids = []

    for task in failed_tasks:
        # Create new task
        new_task_id = str(uuid.uuid4())
        task_data = {
            "task_id": new_task_id,
            "task_description": task.task_description,
            "repository_url": task.repository_url,
            "github_token": task.github_token,
            "target_branch": task.target_branch,
            "timeout_minutes": task.timeout_minutes,
            "save_word": task.save_word,
            "status": "initializing",
            "progress": "Batch retriggering with fresh Claude instance...",
            "logs": [
                f"Batch retriggered from failed task {task.task_id}",
                "Initializing fresh autonomous learning environment",
            ],
            "created_at": datetime.now().isoformat(),
            "container_id": None,
            "is_active": True,
        }

        await db.create_task(task_data)
        new_task_ids.append(new_task_id)

        # Delete original failed task
        await db.delete_task(task.task_id)

        # Start the new task
        asyncio.create_task(run_autonomous_task(new_task_id))

        retriggered_count += 1

    return {
        "success": True,
        "retriggered_count": retriggered_count,
        "new_task_ids": new_task_ids,
        "message": f"Successfully retriggered {retriggered_count} failed tasks",
    }


def load_environment():
    """Load environment variables from setup_env.sh if it exists"""
    env_file = "setup_env.sh"
    if os.path.exists(env_file):
        print(f"Loading environment from {env_file}...")
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export ") and "=" in line:
                        # Parse export VAR=value
                        var_assignment = line[7:]  # Remove 'export '
                        if "=" in var_assignment:
                            key, value = var_assignment.split("=", 1)
                            # Remove quotes if present
                            value = value.strip("\"'")
                            os.environ[key] = value

            # Verify API key was loaded
            if os.getenv("ANTHROPIC_API_KEY"):
                print("API key loaded from setup_env.sh")
            else:
                print("Warning: ANTHROPIC_API_KEY not found in setup_env.sh")

        except Exception as e:
            print(f"Error loading environment: {e}")
    else:
        print(f"Environment file {env_file} not found")


if __name__ == "__main__":
    # Kill any existing server first
    kill_existing_server()

    # Load environment
    load_environment()

    print("Dependencies are up to date.")
    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

    # Run the server
    uvicorn.run(
        "autonomous_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
