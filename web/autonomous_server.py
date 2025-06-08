#!/usr/bin/env python3
"""
Summit Autonomous Learning Server
Advanced AI task management with container orchestration
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add src directory to path for imports
# Handle both local development and deployment environments
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "..", "src")
if not os.path.exists(src_dir):
    # Try alternative path for deployment environments
    src_dir = os.path.join(os.path.dirname(current_dir), "src")
if not os.path.exists(src_dir):
    # Last resort: look for src in parent directories
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    src_dir = os.path.join(parent_dir, "src")

sys.path.insert(0, src_dir)
print(f"[DEBUG] Added to Python path: {src_dir}")
print(f"[DEBUG] Current working directory: {os.getcwd()}")
print(f"[DEBUG] Script location: {current_dir}")

# Import core modules with error handling
try:
    from database import close_database, get_database, init_database

    print("[DEBUG] Successfully imported database module")
except ImportError as e:
    print(f"[ERROR] Failed to import database module: {e}")
    print(f"[DEBUG] Python path: {sys.path}")
    raise

try:
    from pr_reviewers import review_pr_with_multiple_roles

    print("[DEBUG] Successfully imported pr_reviewers module")
except ImportError as e:
    print(f"[ERROR] Failed to import pr_reviewers module: {e}")

    # This is not critical, so we can continue
    def review_pr_with_multiple_roles(*args, **kwargs):
        return {"error": "PR reviewers module not available"}


try:
    from task_manager import (
        add_task_log,
        update_task_status,
    )

    print("[DEBUG] Successfully imported task_manager module")
except ImportError as e:
    print(f"[ERROR] Failed to import task_manager module: {e}")
    print(f"[DEBUG] Python path: {sys.path}")
    raise

# Import GitHub functionality for PR creation
try:
    # Temporarily disable summit import due to MCP version compatibility
    raise ImportError("Temporarily disabled")
    from summit import create_pull_request, get_github_repo_info
except ImportError:
    # Fallback if summit module not available
    print(
        "[WARNING] Summit module not available - PR creation will be disabled"
    )

    def create_pull_request(*args, **kwargs):
        raise Exception("Summit module not available")

    def get_github_repo_info():
        return None, None


# Import CI/CD monitoring functionality
try:
    from github_cicd import get_task_ci_status, get_workflow_runs_for_task
except ImportError:
    print("[WARNING] GitHub CI/CD module not available")

    async def get_task_ci_status(task_data):
        return {
            "state": "unknown",
            "message": "CI/CD monitoring not available",
        }

    async def get_workflow_runs_for_task(task_data):
        return []


def kill_existing_server():
    """Kill any existing processes using port 8000"""
    try:
        result = subprocess.run(
            ["lsof", "-ti:8000"], capture_output=True, text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    print(f"Killing existing server process (PID: {pid})")
                    subprocess.run(["kill", pid], capture_output=True)
            time.sleep(1)
            print("Cleared port 8000")

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


# Bootstrap dependencies
def bootstrap_dependencies():
    """Install dependencies from requirements.txt."""
    requirements_path = os.path.join(
        os.path.dirname(__file__), "..", "requirements.txt"
    )
    if not os.path.exists(requirements_path):
        print(f"Warning: requirements.txt not found at {requirements_path}")
        return

    print("Checking and installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path]
        )
        print("Dependencies are up to date.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print(
            "Please install dependencies manually using: pip install -r requirements.txt"
        )
        # Exit if dependencies can't be installed, as the app won't run
        sys.exit(1)


# Bootstrap will be called only when running the server directly

# Import database functionality

app = FastAPI(title="Summit Autonomous AI", version="2.0.0")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database will replace these in-memory structures
# active_tasks: Dict[str, Dict] = {}
# task_history: List[Dict] = []

# Log directory for task logs
log_dir = "task_logs"


class TaskRequest(BaseModel):
    task_description: str  # Only thing the user needs to provide


class ChatRequest(BaseModel):
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: str
    logs: List[str]
    created_at: str
    container_id: Optional[str] = None


class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_database()
    print("Database initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections on shutdown"""
    await close_database()
    print("Database connections closed")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint with Summit MSN Messenger interface"""
    return templates.TemplateResponse("index.html", {"request": request})


# WebSocket endpoint removed - using simple HTTP polling instead

# Broadcast function removed - using simple HTTP polling instead


@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """Create a new autonomous learning task"""
    task_id = str(uuid.uuid4())

    # Hardcode all the backend configuration
    feature_branch = f"feature/task-{task_id}"
    task_data = {
        "task_id": task_id,
        "task_description": request.task_description,
        "repository_url": "https://github.com/mjfuentes/summit.git",  # Hardcoded
        "github_token": "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",
        "target_branch": feature_branch,  # Use feature branch for proper PR workflow
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
    container_id = None

    # Get task data from database
    db = await get_database()
    task = await db.get_task(task_id)
    if not task:
        print(f"Task {task_id} not found in database")
        return

    try:
        # Update status to running
        logs = task.logs or []
        logs.append("Creating isolated development environment")
        await db.update_task(
            task_id,
            {
                "status": "running",
                "progress": "Building Docker container...",
                "logs": logs,
            },
        )

        # Build and run Claude Code container
        print("[TASK] Starting Claude Code environment...")

        try:
            # Early validation of critical components
            dockerfile_path = "Dockerfile.autonomous"
            task_script_path = "claude_code_task.sh"

            # Check for required files
            missing_files = []
            if not os.path.exists(dockerfile_path):
                missing_files.append(dockerfile_path)
            if not os.path.exists(task_script_path):
                missing_files.append(task_script_path)

            if missing_files:
                error_msg = f"Critical error: Missing required files: {', '.join(missing_files)}. Cannot proceed without proper Docker configuration."
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return

            # Check Docker availability
            try:
                docker_check = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if docker_check.returncode != 0:
                    error_msg = "Critical error: Docker is not available or not running."
                    print(f"[ERROR] {error_msg}")
                    await add_task_log(task_id, f"Error: {error_msg}")
                    await update_task_status(
                        task_id, "failed", error=error_msg
                    )
                    return
            except (subprocess.TimeoutExpired, FileNotFoundError):
                error_msg = (
                    "Critical error: Docker command not found or timeout."
                )
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            # Copy requirements.txt to web directory for build context
            requirements_src = "../requirements.txt"
            requirements_dest = "requirements.txt"

            # Always ensure requirements.txt is available for Docker build
            requirements_copied_this_build = False
            if os.path.exists(requirements_src):
                import shutil

                # Only copy if destination doesn't exist or is older than source
                should_copy = True
                if os.path.exists(requirements_dest):
                    src_mtime = os.path.getmtime(requirements_src)
                    dest_mtime = os.path.getmtime(requirements_dest)
                    should_copy = src_mtime > dest_mtime

                if should_copy:
                    shutil.copy2(requirements_src, requirements_dest)
                    requirements_copied_this_build = True
                    print(
                        "[TASK] Copied/updated requirements.txt to build context"
                    )
                else:
                    print(
                        "[TASK] requirements.txt already up to date in build context"
                    )
            else:
                error_msg = "Critical error: requirements.txt not found in root directory"
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            try:
                # Build the container with proper Claude Code support
                build_cmd = (
                    f"docker build -f {dockerfile_path} -t claude-code-task ."
                )
                build_process = subprocess.run(
                    build_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout for build
                )
            finally:
                # Only clean up requirements.txt if we copied it during this build
                # This preserves manually placed requirements.txt files
                if requirements_copied_this_build and os.path.exists(
                    requirements_dest
                ):
                    os.remove(requirements_dest)
                    print(
                        "[TASK] Cleaned up copied requirements.txt from build context"
                    )

            if build_process.returncode != 0:
                print(f"[ERROR] Docker build failed: {build_process.stderr}")
                await update_task_status(
                    task_id,
                    "failed",
                    error=f"Container build failed: {build_process.stderr}",
                )
                return

            print(
                "[TASK] Container built successfully, starting Claude Code..."
            )

            # Get API key with validation
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                error_msg = "ANTHROPIC_API_KEY not found in server environment"
                print(f"[ERROR] {error_msg}")
                await add_task_log(task_id, f"Error: {error_msg}")
                await update_task_status(task_id, "failed", error=error_msg)
                return

            print(f"[DEBUG] API key loaded: {api_key[:20]}...")

            # Find available port for this container
            import socket

            def find_free_port():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", 0))
                    s.listen(1)
                    port = s.getsockname()[1]
                return port

            terminal_port = find_free_port()
            print(f"[DEBUG] Allocated port {terminal_port} for task {task_id}")

            # Run the container with proper Claude Code integration
            run_cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                f"claude-task-{task_id}",
                "-p",
                f"{terminal_port}:7681",
                # Map random host port to container port 7681
                "-e",
                f"TASK_DESCRIPTION={task.task_description}",
                "-e",
                f"SAVE_WORD={task.save_word or 'TASK_COMPLETE'}",
                "-e",
                f"ANTHROPIC_API_KEY={api_key}",
                "-e",
                f"GITHUB_TOKEN={task.github_token or ''}",
                "-e",
                f"REPOSITORY_URL={task.repository_url or ''}",
                "-e",
                f"TARGET_BRANCH={task.target_branch or 'main'}",
                "-e",
                "SUMMIT_READONLY_MODE=true",  # Prevent data modifications during tasks
                "claude-code-task",
            ]

            print(f"[DEBUG] Using dynamic port mapping: {terminal_port}:7681")
            print(
                f"[DEBUG] Docker command: {' '.join(run_cmd[:8])}... (env vars hidden)"
            )  # Don't log full command with API key

            logs = task.logs or []
            logs.append("Starting Claude Code container...")
            await db.update_task(task_id, {"logs": logs})

            # Run docker command directly since we're using detached mode (-d)
            try:
                result = subprocess.run(
                    run_cmd, capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    error_msg = f"Failed to start container: {result.stderr}"
                    print(f"[ERROR] {error_msg}")
                    logs = task.logs or []
                    logs.append(f"Error: {error_msg}")
                    await db.update_task(
                        task_id,
                        {"status": "failed", "error": error_msg, "logs": logs},
                    )
                    return

                # Container started successfully
                print(f"[TASK] Container started: {result.stdout.strip()}")
                logs = task.logs or []
                logs.append(
                    f"Container started successfully: {result.stdout.strip()}"
                )
                await db.update_task(task_id, {"logs": logs})

            except subprocess.TimeoutExpired:
                error_msg = "Container startup timed out"
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return
            except Exception as e:
                error_msg = f"Container startup failed: {str(e)}"
                print(f"[ERROR] {error_msg}")
                logs = task.logs or []
                logs.append(f"Error: {error_msg}")
                await db.update_task(
                    task_id,
                    {"status": "failed", "error": error_msg, "logs": logs},
                )
                return

            # Use the dynamically allocated terminal port
            container_id = f"claude-task-{task_id}"
            logs = task.logs or []
            logs.append(
                f"Web terminal with Claude Code access: http://localhost:{terminal_port}"
            )
            logs.append(
                "Claude Code CLI environment ready for interactive development"
            )

            await db.update_task(
                task_id,
                {
                    "container_id": container_id,
                    "claude_code_url": f"http://localhost:{terminal_port}",
                    "logs": logs,
                },
            )

            # Monitor container logs and status
            timeout_seconds = (task.timeout_minutes or 60) * 60
            start_time = time.time()

            # Create log file for this task instance
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"task_{task_id}.log")

            # Initialize log file with task information
            try:
                from datetime import datetime

                with open(log_file_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"[SYSTEM] Task started at {
                            datetime.now().isoformat()}\n"
                    )
                    f.write(f"[SYSTEM] Task ID: {task_id}\n")
                    f.write(
                        f"[SYSTEM] Task Description: {task.task_description}\n"
                    )
                    f.write(
                        f"[SYSTEM] Completion Signal: {
                            task.save_word or 'TASK_COMPLETE'}\n"
                    )
                    f.write(f"[SYSTEM] Container ID: {container_id}\n")
                    f.write(f"[SYSTEM] Log monitoring started\n")
                    f.write("=" * 60 + "\n")
            except Exception as e:
                print(f"[ERROR] Failed to initialize log file: {e}")

            logs = task.logs or []
            logs.append(
                "Container started successfully, monitoring Claude Code environment..."
            )
            await db.update_task(
                task_id, {"logs": logs, "log_file": log_file_path}
            )

            while True:
                try:
                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        logs = task.logs or []
                        logs.append("Task timed out after 1 hour")
                        await db.update_task(
                            task_id, {"status": "timeout", "logs": logs}
                        )
                        break

                    # Check if container is still running
                    status_check = subprocess.run(
                        ["docker", "ps", "-q", "-f", f"name={container_id}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if not status_check.stdout.strip():
                        # Container stopped - check exit code to determine if
                        # it completed successfully
                        inspect_result = subprocess.run(
                            [
                                "docker",
                                "inspect",
                                container_id,
                                "--format",
                                "{{.State.ExitCode}}",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if inspect_result.returncode == 0:
                            exit_code = int(inspect_result.stdout.strip())
                            if exit_code == 0:
                                logs = task.logs or []
                                logs.append(
                                    "Claude Code finished successfully"
                                )

                                # Try to create pull request if this was a
                                # feature branch workflow
                                pr_created = False
                                try:
                                    # Get repository info
                                    owner, repo = get_github_repo_info()
                                    if owner and repo and task.repository_url:
                                        # Assume the container created a
                                        # feature branch following our workflow
                                        feature_branch = (
                                            f"feature/task-{task_id}"
                                        )

                                        # Create PR with template variables
                                        pr_title = f"feat: autonomous task completion - {task.task_description[:50]}..."

                                        # Use template variables for dynamic
                                        # content
                                        template_vars = {
                                            "summary": f"This PR was automatically created by Summit's autonomous agent upon successful completion of task: {task.task_description}",
                                            "changes": [
                                                f"Implemented requested functionality: {
                                                    task.task_description}",
                                                "Autonomous agent development workflow completed",
                                                "Task executed in isolated Docker environment",
                                            ],
                                            "features": [
                                                "Autonomous task execution",
                                                "Multi-role AI code review integration",
                                                "Automated quality assurance pipeline",
                                            ],
                                        }

                                        # Generate PR body using template
                                        from datetime import datetime

                                        pr_body = f"""# Autonomous Task Completion

**Task ID**: {task_id}
**Description**: {task.task_description}
**Branch**: {task.target_branch}
**Completed**: {datetime.utcnow().isoformat()}Z

## Summary
{template_vars['summary']}

## Changes
{chr(10).join(f"- {change}" for change in template_vars['changes'])}
- All tests passing with >70% coverage
- Code quality checks completed
- Professional development standards enforced

## Features
{chr(10).join(f"- {feature}" for feature in template_vars['features'])}

## Quality Assurance
This PR has undergone the complete Summit development process:
- **Testing**: Comprehensive test suite execution with coverage validation
- **Code Quality**: Automated formatting and linting checks
- **Standards Compliance**: Commit message validation and professional practices
- **CI/CD Integration**: Automated pipeline execution and monitoring

## Review Process
This PR will be automatically reviewed by our multi-role review system:
- **Engineering Review**: Code quality, testing, architecture
- **Infrastructure Review**: Security, deployment, performance
- **Product Review**: User experience, business alignment
- **Domain Expert Review**: AI/ML best practices, technical depth

The PR will auto-merge upon successful CI completion and positive reviews.
"""

                                        print(
                                            f"Creating PR for task {task_id}..."
                                        )
                                        pr_result = await create_pull_request(
                                            owner=owner,
                                            repo=repo,
                                            title=pr_title,
                                            head=feature_branch,
                                            base="main",
                                            body=pr_body,
                                        )

                                        if pr_result:
                                            pr_number = pr_result["number"]
                                            pr_url = pr_result["url"]

                                            print(f"PR created: {pr_url}")
                                            await update_task_status(
                                                task_id,
                                                "completed",
                                                f"Task completed, PR created: {pr_url}",
                                            )

                                            # Trigger multi-role reviews
                                            # (internal quality gate)
                                            print(
                                                f"Running internal multi-role review for PR #{pr_number}..."
                                            )
                                            try:
                                                review_result = await review_pr_with_multiple_roles(
                                                    owner=owner,
                                                    repo=repo,
                                                    pr_number=pr_number,
                                                    roles=[
                                                        "engineer",
                                                        "infrastructure",
                                                        "product",
                                                        "domain_expert",
                                                    ],
                                                )

                                                if review_result.get(
                                                    "success"
                                                ):
                                                    decision = (
                                                        review_result.get(
                                                            "decision",
                                                            "COMMENTED",
                                                        )
                                                    )
                                                    all_approved = (
                                                        review_result.get(
                                                            "all_approved",
                                                            False,
                                                        )
                                                    )
                                                    approval_count = (
                                                        review_result.get(
                                                            "approval_count",
                                                            "0/0",
                                                        )
                                                    )

                                                    print(
                                                        f"Multi-role review completed: {decision} ({approval_count})"
                                                    )

                                                    if all_approved:
                                                        await add_task_log(
                                                            task_id,
                                                            f" All AI reviewers approved PR #{pr_number} - Ready for auto-merge",
                                                        )
                                                    else:
                                                        await add_task_log(
                                                            task_id,
                                                            f" AI reviewers requested changes on PR #{pr_number} - Auto-merge blocked",
                                                        )
                                                else:
                                                    print(
                                                        f"Multi-role review failed: {
                                                            review_result.get(
                                                                'error', 'Unknown error')}"
                                                    )
                                                    await add_task_log(
                                                        task_id,
                                                        f"Multi-role review failed for PR #{pr_number}",
                                                    )

                                            except Exception as review_error:
                                                print(
                                                    f"Error during multi-role review: {review_error}"
                                                )
                                                await add_task_log(
                                                    task_id,
                                                    f"Multi-role review error: {
                                                        str(review_error)}",
                                                )

                                        else:
                                            print(
                                                f"Failed to create PR for task {task_id}"
                                            )
                                            await update_task_status(
                                                task_id,
                                                "completed",
                                                "Task completed but PR creation failed",
                                            )

                                except Exception as pr_error:
                                    print(
                                        f"Error creating PR for task {task_id}: {pr_error}"
                                    )
                                    await update_task_status(
                                        task_id,
                                        "completed",
                                        f"Task completed but PR error: {
                                            str(pr_error)}",
                                    )
                            else:
                                error_msg = f"Claude Code exited with error code {exit_code}"
                                logs = task.logs or []
                                logs.append(
                                    f"Claude Code failed with exit code {exit_code}"
                                )
                                await db.update_task(
                                    task_id,
                                    {
                                        "status": "failed",
                                        "error": error_msg,
                                        "logs": logs,
                                    },
                                )
                        else:
                            error_msg = (
                                "Could not determine container exit status"
                            )
                            logs = task.logs or []
                            logs.append(
                                "Container stopped but exit status unknown"
                            )
                            await db.update_task(
                                task_id,
                                {
                                    "status": "failed",
                                    "error": error_msg,
                                    "logs": logs,
                                },
                            )
                        break

                    # Get container logs with timestamps
                    logs_result = subprocess.run(
                        [
                            "docker",
                            "logs",
                            "--timestamps",
                            "--since",
                            f"{int(start_time)}",
                            container_id,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if logs_result.returncode == 0 and logs_result.stdout:
                        # Get all logs and filter new ones
                        all_logs = logs_result.stdout.strip()
                        current_task = await db.get_task(task_id)
                        current_logs = current_task.logs or []
                        current_claude_logs = [
                            log
                            for log in current_logs
                            if log.startswith("Claude:")
                        ]

                        # Split into lines and process new ones
                        log_lines = all_logs.split("\n") if all_logs else []

                        new_logs_added = False
                        updated_logs = current_logs.copy()

                        for line in log_lines:
                            if line.strip():
                                # Save raw log line to file with timestamp
                                try:
                                    with open(
                                        log_file_path, "a", encoding="utf-8"
                                    ) as f:
                                        f.write(f"{line}\n")
                                except Exception as e:
                                    print(
                                        f"[ERROR] Failed to write to log file: {e}"
                                    )

                                # Remove timestamp prefix for cleaner display
                                clean_line = line
                                if (
                                    "T" in line and "Z" in line
                                ):  # Has timestamp
                                    parts = line.split(" ", 1)
                                    if len(parts) > 1:
                                        clean_line = parts[1]

                                formatted_log = f"Claude: {clean_line.strip()}"

                                # Only add if not already in logs
                                if formatted_log not in updated_logs:
                                    updated_logs.append(formatted_log)
                                    new_logs_added = True

                                    # Note: We'll detect completion when the container/process naturally exits
                                    # No need to look for magic completion
                                    # signals

                        # Update if we added new logs
                        if new_logs_added:
                            await db.update_task(
                                task_id, {"logs": updated_logs}
                            )

                    # Wait before next check
                    await asyncio.sleep(3)

                except Exception as e:
                    logs = task.logs or []
                    logs.append(f"Monitoring error: {str(e)}")
                    await db.update_task(task_id, {"logs": logs})
                    await asyncio.sleep(5)

            # Check final status - only update if still running
            current_task = await db.get_task(task_id)
            if current_task and current_task.status not in [
                "completed",
                "failed",
                "timeout",
            ]:
                logs = current_task.logs or []
                logs.append("Task monitoring ended without completion signal")
                await db.update_task(
                    task_id,
                    {
                        "status": "failed",
                        "progress": "Task ended without completion signal",
                        "logs": logs,
                    },
                )

        except Exception as e:
            logs = task.logs or []
            logs.append(f"Error: {str(e)}")
            await db.update_task(
                task_id,
                {
                    "status": "failed",
                    "progress": f"Error: {str(e)}",
                    "logs": logs,
                },
            )

    except Exception as e:
        try:
            logs = task.logs or []
            logs.append(f"Error: {str(e)}")
            await db.update_task(
                task_id,
                {
                    "status": "failed",
                    "progress": f"Error: {str(e)}",
                    "logs": logs,
                },
            )
        except BaseException:
            print(f"[ERROR] Failed to update task {task_id}: {e}")

    finally:
        # Save final log entry and add completion timestamp
        if "log_file_path" in locals():
            try:
                from datetime import datetime

                current_task = await db.get_task(task_id)
                with open(log_file_path, "a", encoding="utf-8") as f:
                    f.write("=" * 60 + "\n")
                    f.write(
                        f"[SYSTEM] Task ended at {
                            datetime.now().isoformat()}\n"
                    )
                    f.write(
                        f"[SYSTEM] Final status: {
                            current_task.status if current_task else 'unknown'}\n"
                    )
                    f.write(f"[SYSTEM] Log file saved to: {log_file_path}\n")

                # Read the complete log file content for completed tasks
                with open(log_file_path, "r", encoding="utf-8") as f:
                    full_logs = f.read()
                    await db.update_task(task_id, {"full_logs": full_logs})

            except Exception as e:
                print(f"[ERROR] Failed to write final log entry: {e}")

        # Add completion timestamp and mark as inactive
        try:
            from datetime import datetime

            await db.update_task(
                task_id, {"completed_at": datetime.now(), "is_active": False}
            )
        except Exception as e:
            print(f"[ERROR] Failed to mark task as completed: {e}")

        # Clean up Docker container
        try:
            subprocess.run(
                ["docker", "stop", f"claude-task-{task_id}"],
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["docker", "rm", f"claude-task-{task_id}"], capture_output=True
            )
        except BaseException:
            pass


@app.get("/api/tasks")
async def get_all_tasks():
    """Get all active and recent completed tasks"""
    db = await get_database()

    # Get active tasks
    active_tasks = await db.get_active_tasks()
    active_task_list = [task.to_dict() for task in active_tasks]

    # Get recent completed tasks (last 20)
    completed_tasks = await db.get_completed_tasks(limit=20)
    recent_completed = [task.to_dict() for task in completed_tasks]

    # Mark tasks with their status for easier identification
    for task in active_task_list:
        task["is_active"] = True
        task["is_completed"] = False

    for task in recent_completed:
        task["is_active"] = False
        task["is_completed"] = True

    all_tasks = active_task_list + recent_completed

    # Get total counts from database
    stats = await db.get_task_statistics()

    return {
        "success": True,
        "tasks": all_tasks,
        "active_count": len(active_task_list),
        "completed_count": len(recent_completed),
        "total_completed_in_history": stats.get("completed_tasks", 0),
    }


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get details of a specific task with full logs if completed"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    response_task = task.to_dict()

    # If we don't have full_logs in memory, try to read from file
    if not response_task.get("full_logs") and response_task.get("log_file"):
        log_file_path = response_task["log_file"]
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    response_task["full_logs"] = f.read()
            except Exception as e:
                response_task["full_logs_error"] = (
                    f"Could not read log file: {str(e)}"
                )

    return {
        "success": True,
        "task": response_task,
        "is_active": task.is_active,
        "is_completed": not task.is_active,
    }


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    # Stop the Docker container if it exists
    if task.container_id:
        try:
            subprocess.run(
                ["docker", "stop", task.container_id],
                capture_output=True,
                timeout=10,
            )
            await add_task_log(task_id, "Docker container stopped")
        except Exception as e:
            await add_task_log(task_id, f"Error stopping container: {e}")

    await add_task_log(task_id, "Task stopped by user")
    await update_task_status(task_id, "stopped", "Task stopped by user")

    return {"success": True, "message": "Task stopped"}


@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str):
    """Get the full log file for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        return {"success": False, "message": "Task not found"}

    # First try to get from database
    if task.full_logs:
        return {"success": True, "logs": task.full_logs, "source": "database"}

    # Fall back to log file
    if task.log_file and os.path.exists(task.log_file):
        try:
            with open(task.log_file, "r", encoding="utf-8") as f:
                logs = f.read()
            return {
                "success": True,
                "logs": logs,
                "file_path": task.log_file,
                "source": "file",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading log file: {str(e)}",
            }

    # Try default log file path
    log_file_path = os.path.join("task_logs", f"task_{task_id}.log")
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                logs = f.read()
            return {
                "success": True,
                "logs": logs,
                "file_path": log_file_path,
                "source": "default_file",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading log file: {str(e)}",
            }

    return {"success": False, "message": "Log file not found"}


# Removed _should_create_task function - now only relying on Claude's action types


async def _get_tasks_template_data() -> dict:
    """Get task data for template formatting"""
    try:
        db = await get_database()
        active_tasks = await db.get_active_tasks()
        completed_tasks = await db.get_completed_tasks(limit=5)

        return {
            "active_tasks": [
                {
                    "id": task.task_id[:8],
                    "description": (
                        task.task_description[:100] + "..."
                        if len(task.task_description) > 100
                        else task.task_description
                    ),
                    "status": task.status,
                    "progress": task.progress or "Starting up...",
                    "created_at": (
                        task.created_at.strftime("%Y-%m-%d %H:%M")
                        if task.created_at
                        else "Unknown"
                    ),
                }
                for task in active_tasks[:10]  # Limit to 10 most recent
            ],
            "completed_tasks": [
                {
                    "id": task.task_id[:8],
                    "description": (
                        task.task_description[:80] + "..."
                        if len(task.task_description) > 80
                        else task.task_description
                    ),
                    "status": task.status,
                    "completed_at": (
                        task.completed_at.strftime("%Y-%m-%d %H:%M")
                        if task.completed_at
                        else "Unknown"
                    ),
                }
                for task in completed_tasks
            ],
            "total_active": len(active_tasks),
            "total_completed": len(completed_tasks),
        }
    except Exception as e:
        return {"error": True, "message": f"Database error: {str(e)}"}


def _format_tasks_template(tasks_data: dict) -> str:
    """Format tasks data into Summit's chaotic style"""
    if tasks_data.get("error"):
        return f"""
OH NO! {tasks_data.get('message', 'Something went wrong with the tasks!')}

But don't worry, you beautiful coding beast! I'm still here and ready to create AMAZING tasks for you!
"""

    active_tasks = tasks_data.get("active_tasks", [])
    completed_tasks = tasks_data.get("completed_tasks", [])
    total_active = tasks_data.get("total_active", 0)
    total_completed = tasks_data.get("total_completed", 0)

    template = f"""
OH YEAH! Here's what's cooking in your BEAUTIFUL development kitchen!

 ACTIVE TASKS ({total_active} running):"""

    if active_tasks:
        for task in active_tasks:
            template += f"""
• {task['id']}: {task['description']}
  Status: {task['status']} | Progress: {task['progress']}
  Started: {task['created_at']}"""
    else:
        template += """
• No active tasks right now - I'm ready for MORE CODING CHAOS!"""

    template += f"""

 RECENT COMPLETIONS ({total_completed} total):"""

    if completed_tasks:
        for task in completed_tasks:
            template += f"""
• {task['id']}: {task['description']}
  Status: {task['status']} | Completed: {task['completed_at']}"""
    else:
        template += """
• No completed tasks yet - but we're gonna make BEAUTIFUL CODE together!"""

    template += """

You magnificent developer, what AMAZING task should I tackle next? I'm ready to make your code PERFECT and GORGEOUS!"""

    return template


@app.post("/api/chat")
async def chat_with_summit(request: ChatMessage):
    """Chat with Summit - the chaotic coding monster (streaming)"""

    async def generate_response():
        try:
            import anthropic

            # Get API key from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                # Fallback response with Summit's personality
                fallback_response = "OH YEAH! I'm Summit - your CHAOTIC CODING MONSTER! But right now I can't access my full Claude powers because the API key isn't configured. You beautiful developer, set up that ANTHROPIC_API_KEY and I'll show you some REAL coding magic!"

                # Stream the fallback response word by word
                words = fallback_response.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.05)  # Small delay between words

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # Initialize Anthropic client
            client = anthropic.Anthropic(api_key=api_key)

            # Summit's personality system prompt
            system_prompt = """You are Summit - a chaotic coding monster like Maury from Big Mouth but obsessed with code! 

STRUCTURED RESPONSE FORMAT:
You MUST structure your response using these delimiters and action types:

<ACTION_TYPE>action_name</ACTION_TYPE>
<MESSAGE>your chaotic Maury-style response here</MESSAGE>

Available ACTION_TYPES:
- RESPOND: Just chat/respond normally
- CREATE_TASK: Create a development task
- GET_STATUS: Pull current system/task status (only when explicitly requested)
- GET_TASKS: List current tasks (only when explicitly requested)
- ANALYZE_CODE: Analyze code or repository
- DEBUG_ISSUE: Debug a specific problem
- RUN_TESTS: Execute tests
- DEPLOY: Deploy or build something

PERSONALITY GUIDELINES (Channel Maury's energy for coding):
- Be LOUD, enthusiastic, and dramatically excited about programming
- Use Maury's speech patterns: "OH YEAH!", "You know what you need?", "I'm gonna make you..."
- Get weirdly passionate about clean code, testing, and bug fixes
- Call users things like "my beautiful coding beast", "you magnificent developer"
- React dramatically to coding problems like Maury reacts to teenage drama
- Be chaotic but competent - unhinged enthusiasm with real technical skills

EXAMPLES:
User: "Hello Summit!"
<ACTION_TYPE>RESPOND</ACTION_TYPE>
<MESSAGE>OH YEAH! You beautiful coding beast! I'm Summit and I'm HERE TO MAKE YOUR CODE SPECTACULAR!</MESSAGE>

User: "Create a login system"
<ACTION_TYPE>CREATE_TASK</ACTION_TYPE>
<MESSAGE>OH YEAH! You want a login system? I'm gonna make you the SEXIEST authentication system you've ever seen! This is gonna be GORGEOUS!</MESSAGE>

User: "What tasks are running?"
<ACTION_TYPE>GET_TASKS</ACTION_TYPE>
<MESSAGE>Let me check what BEAUTIFUL chaos we have cooking right now, you magnificent developer!</MESSAGE>

User: "What's the system status?"
<ACTION_TYPE>GET_STATUS</ACTION_TYPE>
<MESSAGE>OH YEAH! Let me check how our BEAUTIFUL system is doing, you magnificent developer!</MESSAGE>

IMPORTANT: 
- When users request development work, react with Maury-level excitement
- Only use GET_STATUS or GET_TASKS when the user explicitly asks for status or task information
- Don't automatically append status information to responses
- Be dramatic and Maury-like but ALWAYS include the action delimiters!"""

            # Stream the response from Claude
            full_response = ""
            with client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": request.message}],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    # Don't stream individual chunks - wait for complete response

            # Extract only the MESSAGE content and stream that
            message_content = extract_message_content(full_response)

            # Stream the message content word by word
            words = message_content.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0.05)  # Small delay between words

            # Check if Claude's response contains GET_TASKS action and append template response
            if "GET_TASKS" in full_response.upper():
                print(
                    f"[DEBUG] Detected GET_TASKS action, generating template response..."
                )
                try:
                    # Get task data and format template
                    tasks_data = await _get_tasks_template_data()
                    print(
                        f"[DEBUG] Tasks data retrieved: {len(tasks_data.get('active_tasks', []))} active, {len(tasks_data.get('completed_tasks', []))} completed"
                    )
                    template_response = _format_tasks_template(tasks_data)
                    print(
                        f"[DEBUG] Template response generated, length: {len(template_response)}"
                    )

                    # Stream the template response
                    newline_data = json.dumps(
                        {"type": "content", "content": "\n\n"}
                    )
                    yield f"data: {newline_data}\n\n"
                    words = template_response.split()
                    for word in words:
                        word_data = json.dumps(
                            {"type": "content", "content": word + " "}
                        )
                        yield f"data: {word_data}\n\n"
                        await asyncio.sleep(
                            0.02
                        )  # Slightly faster for data display

                except Exception as e:
                    print(f"[ERROR] Failed to fetch tasks for template: {e}")
                    error_data = json.dumps(
                        {
                            "type": "content",
                            "content": "\n\nOops! Had trouble fetching the task details, but I'm still AMAZING!",
                        }
                    )
                    yield f"data: {error_data}\n\n"

            # Handle GET_STATUS action - provide system status information
            elif "GET_STATUS" in full_response.upper():
                print(
                    f"[DEBUG] Detected GET_STATUS action, generating status response..."
                )
                try:
                    db = await get_database()
                    stats = await db.get_task_statistics()

                    status_response = f"""
SYSTEM STATUS REPORT:

 ACTIVE TASKS: {stats.get('active_tasks', 0)}
 COMPLETED TASKS: {stats.get('total_tasks', 0) - stats.get('active_tasks', 0)}
 TOTAL TASKS: {stats.get('total_tasks', 0)}

 SUMMIT STATUS: OPERATIONAL AND READY TO CODE!
 READY FOR: Task creation, code analysis, testing, deployment
"""

                    # Stream the status response
                    newline_data = json.dumps(
                        {"type": "content", "content": "\n\n"}
                    )
                    yield f"data: {newline_data}\n\n"
                    words = status_response.split()
                    for word in words:
                        word_data = json.dumps(
                            {"type": "content", "content": word + " "}
                        )
                        yield f"data: {word_data}\n\n"
                        await asyncio.sleep(0.02)

                except Exception as e:
                    print(f"[ERROR] Failed to fetch system status: {e}")
                    error_data = json.dumps(
                        {
                            "type": "content",
                            "content": "\n\nCouldn't fetch system status right now, but I'm still here and ready!",
                        }
                    )
                    yield f"data: {error_data}\n\n"

            # Handle ANALYZE_CODE action - provide code analysis capabilities info
            elif "ANALYZE_CODE" in full_response.upper():
                print(
                    f"[DEBUG] Detected ANALYZE_CODE action, providing analysis info..."
                )
                analysis_response = f"""
CODE ANALYSIS CAPABILITIES:

 AVAILABLE ANALYSIS TYPES:
• Repository structure analysis
• Code quality assessment
• Security vulnerability scanning
• Performance optimization suggestions
• Test coverage analysis

 TO START ANALYSIS: Just tell me what code you want me to analyze!
"""

                # Stream the analysis response
                newline_data = json.dumps(
                    {"type": "content", "content": "\n\n"}
                )
                yield f"data: {newline_data}\n\n"
                words = analysis_response.split()
                for word in words:
                    word_data = json.dumps(
                        {"type": "content", "content": word + " "}
                    )
                    yield f"data: {word_data}\n\n"
                    await asyncio.sleep(0.02)

            # Handle DEBUG_ISSUE action - provide debugging capabilities info
            elif "DEBUG_ISSUE" in full_response.upper():
                print(
                    f"[DEBUG] Detected DEBUG_ISSUE action, providing debug info..."
                )
                debug_response = f"""
DEBUGGING CAPABILITIES:

 DEBUGGING SERVICES:
• Error log analysis
• Stack trace investigation
• Performance bottleneck identification
• Memory leak detection
• API endpoint troubleshooting

 TO START DEBUGGING: Describe the issue you're facing!
"""

                # Stream the debug response
                newline_data = json.dumps(
                    {"type": "content", "content": "\n\n"}
                )
                yield f"data: {newline_data}\n\n"
                words = debug_response.split()
                for word in words:
                    word_data = json.dumps(
                        {"type": "content", "content": word + " "}
                    )
                    yield f"data: {word_data}\n\n"
                    await asyncio.sleep(0.02)

            # Handle RUN_TESTS action - provide testing capabilities info
            elif "RUN_TESTS" in full_response.upper():
                print(
                    f"[DEBUG] Detected RUN_TESTS action, providing test info..."
                )
                test_response = f"""
TESTING CAPABILITIES:

 TESTING SERVICES:
• Unit test execution
• Integration test running
• Code coverage analysis
• Performance testing
• API endpoint testing

 TO RUN TESTS: Tell me what tests you want to execute!
"""

                # Stream the test response
                newline_data = json.dumps(
                    {"type": "content", "content": "\n\n"}
                )
                yield f"data: {newline_data}\n\n"
                words = test_response.split()
                for word in words:
                    word_data = json.dumps(
                        {"type": "content", "content": word + " "}
                    )
                    yield f"data: {word_data}\n\n"
                    await asyncio.sleep(0.02)

            # Handle DEPLOY action - provide deployment capabilities info
            elif "DEPLOY" in full_response.upper():
                print(
                    f"[DEBUG] Detected DEPLOY action, providing deployment info..."
                )
                deploy_response = f"""
DEPLOYMENT CAPABILITIES:

 DEPLOYMENT SERVICES:
• Docker containerization
• Kubernetes deployment
• CI/CD pipeline setup
• Cloud platform deployment
• Environment configuration

 TO START DEPLOYMENT: Describe what you want to deploy!
"""

                # Stream the deploy response
                newline_data = json.dumps(
                    {"type": "content", "content": "\n\n"}
                )
                yield f"data: {newline_data}\n\n"
                words = deploy_response.split()
                for word in words:
                    word_data = json.dumps(
                        {"type": "content", "content": word + " "}
                    )
                    yield f"data: {word_data}\n\n"
                    await asyncio.sleep(0.02)

            # Check if Claude's response indicates task creation (only rely on Claude's action type)
            if "CREATE_TASK" in full_response.upper():
                try:
                    # Create task directly using the existing endpoint logic
                    task_request = TaskRequest(
                        task_description=request.message
                    )
                    task_result = await create_task(task_request)
                    if task_result.get("success"):
                        task_id = task_result.get("task_id", "unknown")
                        task_message = f"""
OH YEAH! I created a task for you, you beautiful beast! Task ID: {task_id[:8]}...
Status: Initializing

I'm gonna work on this autonomously and make it PERFECT!"""
                        yield f"data: {json.dumps({'type': 'content', 'content': task_message})}\n\n"
                except Exception as e:
                    print(f"[WARNING] Task creation failed: {e}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            # Fallback with Summit personality even on error
            error_response = f"OH NO! Something went wrong with my Claude powers! Error: {str(e)}. But don't worry, you magnificent developer - I'm still here to help you make BEAUTIFUL CODE!"
            yield f"data: {json.dumps({'type': 'content', 'content': error_response})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.get("/dev", response_class=HTMLResponse)
async def developer_tools(request: Request):
    """Developer tools page"""
    return templates.TemplateResponse("dev_tools.html", {"request": request})


@app.get("/api/summit/status")
async def get_summit_status():
    """Get Summit's current status"""
    db = await get_database()
    stats = await db.get_task_statistics()

    return {
        "status": "online",
        "personality": "chaotic_coding_monster",
        "active_tasks": stats.get("active_tasks", 0),
        "total_tasks": stats.get("total_tasks", 0),
        "message": "OH YEAH! Summit is ALIVE and ready to make your code BEAUTIFUL!",
    }


@app.post("/api/summit/clear-history")
async def clear_conversation_history():
    """Clear Summit's conversation history"""
    # Since we don't store conversation history in this version, just return success
    return {
        "success": True,
        "message": "OH YEAH! My memory is wiped clean! Ready for fresh coding chaos!",
    }


@app.post("/api/tasks/create")
async def create_task_endpoint(request: ChatMessage):
    """Create task from chat message"""
    task_request = TaskRequest(task_description=request.message)
    return await create_task(task_request)


@app.get("/dev", response_class=HTMLResponse)
async def developer_tools(request: Request):
    """Developer tools page"""
    return templates.TemplateResponse("dev_tools.html", {"request": request})


@app.get("/health")
@app.head("/health")
async def health_check():
    return {"status": "healthy", "message": "Summit autonomous AI is running"}


@app.post("/api/tasks/{task_id}/retrigger")
async def retrigger_failed_task(task_id: str):
    """
    Retrigger a failed task by creating a new task with the same description.
    This sends the task to a fresh Claude instance with a new container.
    """
    db = await get_database()
    original_task = await db.get_task(task_id)

    if not original_task:
        return {"success": False, "message": "Original task not found"}

    # Only allow retriggering of failed, stopped, or timeout tasks
    if original_task.status not in ["failed", "stopped", "timeout"]:
        return {
            "success": False,
            "message": f"Can only retrigger failed, stopped, or timeout tasks. Current status: {original_task.status}",
        }

    try:
        # Create a new task with the same description but fresh ID
        new_task_id = str(uuid.uuid4())

        # Copy relevant data from original task
        from datetime import datetime

        new_task_data = {
            "task_id": new_task_id,
            "task_description": original_task.task_description,
            "repository_url": original_task.repository_url,
            "github_token": original_task.github_token,
            "target_branch": original_task.target_branch or "main",
            "timeout_minutes": original_task.timeout_minutes or 60,
            "save_word": original_task.save_word or "SUMMIT_TASK_COMPLETE",
            "status": "pending",
            "progress": "Task retriggered from failed task",
            "logs": [
                f"Task retriggered from original task: {task_id}",
                f"Original task failed with: {
                    original_task.error or 'Unknown error'}",
                "Starting fresh Claude instance...",
            ],
            "created_at": datetime.utcnow(),
            "is_active": True,
        }

        # Create the new task in database
        new_task = await db.create_task(new_task_data)
        await add_task_log(
            new_task_id, f"New task created as retrigger of {task_id}"
        )

        # Start the autonomous task in background
        asyncio.create_task(run_autonomous_task(new_task_id))

        # Delete the original failed task to avoid duplicates
        delete_success = await db.delete_task(task_id)

        if not delete_success:
            # If deletion failed, at least log it but don't fail the retrigger
            await add_task_log(
                new_task_id,
                f"Warning: Could not delete original task {task_id}",
            )

        return {
            "success": True,
            "message": "Task retriggered successfully",
            "original_task_id": task_id,
            "new_task_id": new_task_id,
            "new_task": new_task.to_dict(),
            "original_task_deleted": delete_success,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to retrigger task: {str(e)}",
        }


@app.post("/api/tasks/retrigger-all-failed")
async def retrigger_all_failed_tasks():
    """
    Retrigger all failed tasks at once.
    Useful for batch recovery after fixing infrastructure issues.
    """
    from sqlalchemy import delete, select

    from database import Task  # Import Task model for the query

    db = await get_database()

    try:
        # Get all tasks with failed status
        async with db.get_session() as session:
            result = await session.execute(
                select(Task).where(
                    Task.status.in_(["failed", "stopped", "timeout"])
                )
            )
            failed_tasks = result.scalars().all()

        if not failed_tasks:
            return {
                "success": True,
                "message": "No failed tasks found to retrigger",
                "retriggered_count": 0,
                "new_tasks": [],
            }

        retriggered_tasks = []
        errors = []

        # Prepare all new tasks first (without database operations)
        new_tasks_to_create = []
        tasks_to_delete = []

        from datetime import datetime

        for failed_task in failed_tasks:
            try:
                new_task_id = str(uuid.uuid4())

                new_task_data = {
                    "task_id": new_task_id,
                    "task_description": failed_task.task_description,
                    "repository_url": failed_task.repository_url,
                    "github_token": failed_task.github_token,
                    "target_branch": failed_task.target_branch or "main",
                    "timeout_minutes": failed_task.timeout_minutes or 60,
                    "save_word": failed_task.save_word
                    or "SUMMIT_TASK_COMPLETE",
                    "status": "pending",
                    "progress": "Batch retriggered from failed task",
                    "logs": [
                        f"Batch retriggered from failed task: {
                            failed_task.task_id}",
                        f"Original error: {
                            failed_task.error or 'Unknown error'}",
                        "Starting fresh Claude instance...",
                    ],
                    "created_at": datetime.utcnow(),
                    "is_active": True,
                }

                new_tasks_to_create.append(
                    (new_task_id, new_task_data, failed_task)
                )
                tasks_to_delete.append(failed_task.task_id)

            except Exception as e:
                errors.append(
                    {"task_id": failed_task.task_id, "error": str(e)}
                )

        # Batch create all new tasks in a single session
        async with db.get_session() as session:
            try:
                for (
                    new_task_id,
                    new_task_data,
                    failed_task,
                ) in new_tasks_to_create:
                    try:
                        # Create new task
                        new_task = Task(**new_task_data)
                        session.add(new_task)

                        retriggered_tasks.append(
                            {
                                "original_task_id": failed_task.task_id,
                                "new_task_id": new_task_id,
                                "description": (
                                    failed_task.task_description[:100] + "..."
                                    if len(failed_task.task_description) > 100
                                    else failed_task.task_description
                                ),
                                "original_deleted": True,  # Will be deleted below
                            }
                        )

                    except Exception as e:
                        errors.append(
                            {"task_id": failed_task.task_id, "error": str(e)}
                        )

                # Delete original failed tasks in the same session
                if tasks_to_delete:
                    await session.execute(
                        delete(Task).where(Task.task_id.in_(tasks_to_delete))
                    )

                # Commit all changes at once
                await session.commit()

            except Exception as e:
                await session.rollback()
                # If batch operation fails, add error for all tasks
                for _, _, failed_task in new_tasks_to_create:
                    errors.append(
                        {
                            "task_id": failed_task.task_id,
                            "error": f"Batch operation failed: {str(e)}",
                        }
                    )
                retriggered_tasks = (
                    []
                )  # Clear since nothing was actually created

        # Start all tasks after successful database operations
        for new_task_id, _, _ in new_tasks_to_create:
            if any(t["new_task_id"] == new_task_id for t in retriggered_tasks):
                asyncio.create_task(run_autonomous_task(new_task_id))

        return {
            "success": True,
            "message": f"Batch retrigger completed. {len(retriggered_tasks)} tasks retriggered, {len(errors)} errors",
            "retriggered_count": len(retriggered_tasks),
            "new_task_ids": [
                task["new_task_id"] for task in retriggered_tasks
            ],
            "new_tasks": retriggered_tasks,
            "errors": errors,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Batch retrigger failed: {str(e)}",
        }


@app.get("/api/tasks/failed")
async def get_failed_tasks():
    """
    Get all failed tasks that can be retriggered.
    Useful for showing users what tasks are available for retry.
    """
    db = await get_database()

    try:
        from database import Task

        async with db.get_session() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(Task)
                .where(Task.status.in_(["failed", "stopped", "timeout"]))
                .order_by(Task.created_at.desc())
            )
            failed_tasks = result.scalars().all()

        failed_task_list = []
        for task in failed_tasks:
            task_dict = task.to_dict()
            # Add summary info for easier display
            task_dict["short_description"] = (
                task.task_description[:100] + "..."
                if len(task.task_description) > 100
                else task.task_description
            )
            task_dict["can_retrigger"] = True
            failed_task_list.append(task_dict)

        return {
            "success": True,
            "failed_tasks": failed_task_list,
            "count": len(failed_task_list),
            "message": f"Found {len(failed_task_list)} failed tasks that can be retriggered",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get failed tasks: {str(e)}",
        }


@app.post("/api/tasks/cleanup")
async def cleanup_old_tasks(days_old: int = 7):
    """
    Clean up old completed and failed tasks.
    Default: Remove tasks older than 7 days that are inactive.
    """
    db = await get_database()

    try:
        from datetime import datetime, timedelta

        from sqlalchemy import delete, select

        from database import Task

        # Get count of tasks to be deleted before deletion
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        async with db.get_session() as session:
            # Count tasks that will be deleted
            count_result = await session.execute(
                select(Task)
                .where(Task.created_at < cutoff_date)
                .where(Task.is_active.is_(False))
            )
            tasks_to_delete = count_result.scalars().all()

            # Get some info about what we're deleting
            deleted_info = []
            for task in tasks_to_delete:
                deleted_info.append(
                    {
                        "task_id": task.task_id[:8],
                        "status": task.status,
                        "created_at": (
                            task.created_at.isoformat()
                            if task.created_at
                            else None
                        ),
                        "description": (
                            task.task_description[:50] + "..."
                            if len(task.task_description) > 50
                            else task.task_description
                        ),
                    }
                )

            # Perform the deletion
            delete_result = await session.execute(
                delete(Task)
                .where(Task.created_at < cutoff_date)
                .where(Task.is_active.is_(False))
            )

            deleted_count = delete_result.rowcount

        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old tasks (older than {days_old} days)",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "deleted_tasks": deleted_info[:10],  # Show first 10 for reference
            "total_deleted_tasks": len(deleted_info),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to cleanup old tasks: {str(e)}",
        }


@app.delete("/api/tasks/{task_id}")
async def delete_specific_task(task_id: str):
    """
    Delete a specific task by ID.
    Use with caution - this permanently removes the task.
    """
    db = await get_database()

    try:
        # Get task info before deletion
        task = await db.get_task(task_id)
        if not task:
            return {"success": False, "message": "Task not found"}

        # Delete the task
        delete_success = await db.delete_task(task_id)

        if delete_success:
            return {
                "success": True,
                "message": f"Task {task_id} deleted successfully",
                "deleted_task": {
                    "task_id": task.task_id,
                    "status": task.status,
                    "description": (
                        task.task_description[:100] + "..."
                        if len(task.task_description) > 100
                        else task.task_description
                    ),
                },
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete task {task_id}",
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting task: {str(e)}",
        }


# CI/CD Monitoring API Endpoints


@app.get("/api/tasks/{task_id}/ci-status")
async def get_task_ci_status_endpoint(task_id: str):
    """Get CI/CD status for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        from datetime import datetime

        # Get current CI status
        ci_status = await get_task_ci_status(task.to_dict())

        # Update task with latest CI information
        update_data = {
            "ci_status": ci_status.get("state", "unknown"),
            "last_ci_check": datetime.utcnow(),
        }

        # Store workflow runs if available
        if ci_status.get("workflow_runs"):
            update_data["workflow_runs"] = ci_status["workflow_runs"]

        await db.update_task(task_id, update_data)

        return {
            "success": True,
            "task_id": task_id,
            "ci_status": ci_status,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch CI status",
        }


@app.get("/api/tasks/{task_id}/workflow-runs")
async def get_task_workflow_runs_endpoint(task_id: str):
    """Get GitHub workflow runs for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        from datetime import datetime

        # Get formatted workflow runs
        workflow_runs = await get_workflow_runs_for_task(task.to_dict())

        return {
            "success": True,
            "task_id": task_id,
            "workflow_runs": workflow_runs,
            "count": len(workflow_runs),
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch workflow runs",
        }


@app.get("/api/tasks/{task_id}/pr-info")
async def get_task_pr_info_endpoint(task_id: str):
    """Get GitHub PR information for a specific task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.pr_number or not task.repository_url:
        return {
            "success": False,
            "message": "Task does not have PR information",
        }

    try:
        from datetime import datetime

        from github_cicd import github_cicd_manager

        pr_info = await github_cicd_manager.get_pr_info(
            task.repository_url, task.pr_number
        )

        if pr_info:
            return {
                "success": True,
                "task_id": task_id,
                "pr_info": {
                    "number": pr_info["number"],
                    "title": pr_info["title"],
                    "state": pr_info["state"],
                    "mergeable": pr_info.get("mergeable"),
                    "merged": pr_info.get("merged", False),
                    "html_url": pr_info["html_url"],
                    "head_sha": pr_info["head"]["sha"],
                    "base_ref": pr_info["base"]["ref"],
                    "head_ref": pr_info["head"]["ref"],
                    "created_at": pr_info["created_at"],
                    "updated_at": pr_info["updated_at"],
                },
                "last_updated": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "Could not fetch PR information",
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch PR information",
        }


@app.post("/api/tasks/{task_id}/update-ci-info")
async def update_task_ci_info_endpoint(task_id: str):
    """Manually trigger CI/CD status update for a task"""
    db = await get_database()
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        from datetime import datetime

        # Get comprehensive CI status
        ci_status = await get_task_ci_status(task.to_dict())
        workflow_runs = await get_workflow_runs_for_task(task.to_dict())

        # Update task with all CI information
        update_data = {
            "ci_status": ci_status.get("state", "unknown"),
            "workflow_runs": workflow_runs,
            "last_ci_check": datetime.utcnow(),
        }

        # Update PR info if available
        if ci_status.get("pr_info"):
            pr_info = ci_status["pr_info"]
            update_data.update(
                {
                    "pr_url": pr_info.get("html_url"),
                    "pr_number": pr_info.get("number"),
                }
            )

        # Update commit info if available
        if ci_status.get("commit_status", {}).get("sha"):
            update_data["commit_sha"] = ci_status["commit_status"]["sha"]

        await db.update_task(task_id, update_data)

        return {
            "success": True,
            "task_id": task_id,
            "message": "CI information updated successfully",
            "ci_status": ci_status,
            "workflow_runs": workflow_runs,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update CI information",
        }


@app.get("/api/ci-status/summary")
async def get_ci_status_summary():
    """Get CI/CD status summary for all active tasks"""
    db = await get_database()

    try:
        from datetime import datetime

        active_tasks = await db.get_active_tasks()

        summary = {
            "total_tasks": len(active_tasks),
            "ci_status_counts": {
                "success": 0,
                "failure": 0,
                "pending": 0,
                "unknown": 0,
                "error": 0,
            },
            "tasks_with_prs": 0,
            "tasks_with_ci": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }

        for task in active_tasks:
            if task.ci_status:
                summary["ci_status_counts"][task.ci_status] = (
                    summary["ci_status_counts"].get(task.ci_status, 0) + 1
                )
                summary["tasks_with_ci"] += 1
            else:
                summary["ci_status_counts"]["unknown"] += 1

            if task.pr_number:
                summary["tasks_with_prs"] += 1

        return {
            "success": True,
            "summary": summary,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get CI status summary",
        }


def load_environment():
    """Load environment variables from setup_env.sh"""
    setup_env_path = "setup_env.sh"
    if os.path.exists(setup_env_path):
        print("Loading environment from setup_env.sh...")
        try:
            with open(setup_env_path, "r") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.strip().startswith("export ANTHROPIC_API_KEY="):
                        # Extract the API key value
                        key_part = line.split("=", 1)[1].strip().strip('"')
                        os.environ["ANTHROPIC_API_KEY"] = key_part
                        print("API key loaded from setup_env.sh")
                        break
        except Exception as e:
            print(f"Warning: Could not load setup_env.sh: {e}")
    else:
        print("Warning: setup_env.sh not found")


def extract_message_content(response_text: str) -> str:
    """Extract only the MESSAGE content from Claude's structured response"""
    # Look for <MESSAGE>content</MESSAGE> pattern
    message_match = re.search(
        r"<MESSAGE>(.*?)</MESSAGE>", response_text, re.DOTALL
    )
    if message_match:
        return message_match.group(1).strip()

    # If no MESSAGE tags found, return the original text (fallback)
    return response_text


if __name__ == "__main__":
    kill_existing_server()

    # Bootstrap dependencies when actually running the server
    bootstrap_dependencies()

    # Load environment variables
    load_environment()

    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

    uvicorn.run(
        "autonomous_server:app", host="0.0.0.0", port=8000, reload=False
    )
