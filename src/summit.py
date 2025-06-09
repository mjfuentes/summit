#!/usr/bin/env python3

import asyncio
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
import requests
from anthropic import Anthropic
from mcp.server import NotificationOptions, Server

from cost_tracker import CostTracker
from unified_database import UnifiedDatabaseManager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "config"))

# Configuration with fallback for CI/testing environments
try:
    # type: ignore
    from config import SUMMIT_CONFIG, setup_environment

    setup_environment()
except ImportError:
    # Fallback configuration for CI/testing environments
    SUMMIT_CONFIG = {
        "daily_budget": 10.0,
        "hourly_budget": 2.0,
        "max_recursion_depth": 3,
        "embedding_model": "text-embedding-3-small",
        "chat_model": "claude-sonnet-4-20250514",
    }


# Initialize the MCP server
server: Server = Server("summit")

# Initialize cost tracker using config values
cost_tracker = CostTracker(
    daily_budget=SUMMIT_CONFIG["daily_budget"],
    hourly_budget=SUMMIT_CONFIG["hourly_budget"],
    max_recursion_depth=SUMMIT_CONFIG["max_recursion_depth"],
)

# Database manager instance
_database_manager = None


def get_database() -> UnifiedDatabaseManager:
    """Get or create database manager instance"""
    global _database_manager
    if _database_manager is None:
        from unified_database import UnifiedDatabaseManager

        database_url = os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///summit.db"
        )
        _database_manager = UnifiedDatabaseManager(database_url)
    return _database_manager


# Initialize Anthropic client
def get_anthropic_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


# GitHub API configuration for Codespaces
def get_github_headers():
    """Get GitHub API headers with authentication"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_git_executable_path() -> Optional[str]:
    """Get the full path to the git executable safely"""
    try:
        # Use which/where to get the full path to git
        if os.name == "nt":  # Windows
            cmd = ["where", "git"]
        else:  # Unix/Linux/MacOS
            cmd = ["which", "git"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )

        if result.stdout:
            # Return the first path found (strip newlines)
            return result.stdout.strip().split("\n")[0]
        return None
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Git executable not found in PATH")
        # Fallback to common locations
        for path in [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "C:\\Program Files\\Git\\bin\\git.exe",
        ]:
            if os.path.exists(path):
                return path
        return None


def get_repository_url() -> Optional[str]:
    """Get the repository URL from git or environment variables"""
    # Try environment variables first
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")

    if owner and repo:
        return owner, repo

    # Try to extract from git remote
    try:
        # Get git executable with full path for security
        git_path = get_git_executable_path()
        if not git_path:
            logger.warning(
                "Git executable not found, can't determine repository URL"
            )
            return None

        result = subprocess.run(
            [git_path, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
        )
        if result.returncode == 0:
            remote_url = result.stdout.strip()
            # Parse GitHub URL (supports both SSH and HTTPS)
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    parts = (
                        remote_url.split(":")[-1]
                        .replace(".git", "")
                        .split("/")
                    )
                    return parts[0], parts[1]
                elif remote_url.startswith("https://"):
                    # HTTPS format: https://github.com/owner/repo.git
                    parts = remote_url.split("/")
                    return parts[-2], parts[-1].replace(".git", "")
    except BaseException:
        pass

    return None, None


# Track server start time
start_time = time.time()

# Store active codespaces for management
active_codespaces = {}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Summit tools"""
    return [
        types.Tool(
            name="summit_advice",
            description="Ask Summit for advice on any topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or topic you need advice on",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional: Additional context about your situation",
                    },
                },
                "required": ["question"],
            },
        ),
        types.Tool(
            name="summit_status",
            description="Check Summit advisor status including cost tracking",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_cost_report",
            description="Get detailed cost tracking report",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_learn_capability",
            description="Learn a new capability by modifying Summit's codebase using GitHub Codespaces",
            inputSchema={
                "type": "object",
                "properties": {
                    "capability_description": {
                        "type": "string",
                        "description": "Detailed description of the new capability to implement",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "Optional: Specific technical requirements or constraints",
                    },
                    "machine_type": {
                        "type": "string",
                        "description": "Optional: Codespace machine type (standardLinux32gb, premiumLinux32gb, etc.)",
                    },
                },
                "required": ["capability_description"],
            },
        ),
        types.Tool(
            name="summit_codespace_status",
            description="Check status of active development environments (codespaces)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="summit_deploy_changes",
            description="Deploy and activate changes from a completed development session",
            inputSchema={
                "type": "object",
                "properties": {
                    "codespace_name": {
                        "type": "string",
                        "description": "Name of the codespace with completed changes",
                    },
                    "commit_message": {
                        "type": "string",
                        "description": "Commit message for the changes",
                    },
                },
                "required": ["codespace_name", "commit_message"],
            },
        ),
        types.Tool(
            name="summit_cleanup_environment",
            description="Clean up development environment after learning is complete",
            inputSchema={
                "type": "object",
                "properties": {
                    "codespace_name": {
                        "type": "string",
                        "description": "Name of the codespace to clean up",
                    },
                },
                "required": ["codespace_name"],
            },
        ),
        # Core Agent Task Management Tools
        types.Tool(
            name="summit_start_task",
            description="Start working on a task - claims and begins execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to start working on",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "ID of the agent starting the task",
                    },
                },
                "required": ["task_id", "agent_id"],
            },
        ),
        types.Tool(
            name="summit_end_task",
            description="Complete a task with results or mark it as failed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task being completed",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "ID of the agent completing the task",
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the task completed successfully",
                    },
                    "result": {
                        "type": "object",
                        "description": "Task results including output, files modified, etc.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of work completed",
                    },
                    "files_modified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files modified during task execution",
                    },
                    "error_message": {
                        "type": "string",
                        "description": "Error message if task failed",
                    },
                    "quality_score": {
                        "type": "number",
                        "description": "Self-assessed quality score (0-10)",
                    },
                },
                "required": ["task_id", "agent_id", "success"],
            },
        ),
        types.Tool(
            name="summit_complete_task",
            description="Simplified tool to complete a task (preferred method for OpenCode agents)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task being completed",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "ID of the agent completing the task",
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the task completed successfully (true) or failed (false)",
                        "default": True,
                    },
                    "result": {
                        "type": "object",
                        "description": "Additional result data as a dictionary/object",
                        "default": {},
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of work completed",
                        "default": "",
                    },
                    "files_modified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files modified during task execution",
                        "default": [],
                    },
                    "error_message": {
                        "type": "string",
                        "description": "Error message if task failed",
                        "default": "",
                    },
                },
                "required": ["task_id", "agent_id"],
            },
        ),
    ]


async def get_advice_from_claude(
    question: str, context: Optional[str] = None, recursion_depth: int = 0
) -> str:
    """Get advice from Claude API with cost tracking"""
    client = get_anthropic_client()

    if not client:
        return "Summit needs an ANTHROPIC_API_KEY environment variable to provide AI-powered advice. Please set it up!"

    # Estimate cost before making the call
    estimated_input_tokens = len(question.split()) * 1.3  # Rough estimate
    if context:
        estimated_input_tokens += len(context.split()) * 1.3
    estimated_output_tokens = 200  # Conservative estimate

    estimated_cost = cost_tracker.estimate_cost(
        int(estimated_input_tokens), int(estimated_output_tokens)
    )

    # Check if we can make the call
    can_call, reason = cost_tracker.can_make_call(
        estimated_cost, recursion_depth
    )
    if not can_call:
        return f"Summit's cost controls prevented this call: {reason}"

    try:
        # Build the prompt
        prompt = f"""You are Summit, a sophisticated AI advisor specializing in autonomous development and programming assistance.

Question: {question}"""

        if context:
            prompt += f"\n\nContext: {context}"

        prompt += '\n\nPlease provide thoughtful, practical advice. Be concise but thorough. Start your response with "Summit\'s Advice:"'

        message = client.messages.create(
            model=SUMMIT_CONFIG["chat_model"],
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Record the actual cost
        actual_cost = cost_tracker.record_call(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=SUMMIT_CONFIG["chat_model"],
            recursion_depth=recursion_depth,
            call_type="advice",
        )

        response = message.content[0].text

        # Add cost info to response for transparency
        response += f"\n\n[Cost: ${
            actual_cost:.4f} | Daily spent: ${
            cost_tracker.get_daily_spent():.4f}/${
            cost_tracker.daily_budget}]"

        return response

    except Exception as error:
        return f"Summit encountered an error while seeking wisdom: {error}"


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """Handle Summit tool calls"""

    if name == "summit_advice":
        question = arguments.get("question")
        context = arguments.get("context")

        if not question:
            raise ValueError("Question is required for advice")

        advice = await get_advice_from_claude(question, context)

        return [types.TextContent(type="text", text=advice)]

    elif name == "summit_status":
        has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        uptime = int(time.time() - start_time)
        cost_status = cost_tracker.get_status()

        status_text = f"""Summit Advisor Status

Uptime: {uptime}s
AI Status: {"Ready to provide advice" if has_api_key else "Missing API key"}
Wisdom Level: Maximum

Cost Controls:
- Daily Budget: ${cost_status['daily_spent']:.4f} / ${cost_status['daily_budget']} (${cost_status['daily_remaining']:.4f} remaining)
- Hourly Budget: ${cost_status['hourly_spent']:.4f} / ${cost_status['hourly_budget']} (${cost_status['hourly_remaining']:.4f} remaining)
- Max Recursion Depth: {cost_status['max_recursion_depth']}
- Total Calls Today: {cost_status['total_calls_today']}
- Lifetime Cost: ${cost_status['total_lifetime_cost']:.4f}

Status: Standing by for your questions!"""

        return [types.TextContent(type="text", text=status_text)]

    elif name == "summit_cost_report":
        cost_status = cost_tracker.get_status()

        # Get recent call history
        recent_calls = (
            cost_tracker.call_history[-10:]
            if cost_tracker.call_history
            else []
        )

        report = f"""Summit Cost Tracking Report

Budget Status:
- Daily: ${cost_status['daily_spent']:.4f} / ${cost_status['daily_budget']} ({(cost_status['daily_spent'] / cost_status['daily_budget'] * 100):.1f}% used)
- Hourly: ${cost_status['hourly_spent']:.4f} / ${cost_status['hourly_budget']} ({(cost_status['hourly_spent'] / cost_status['hourly_budget'] * 100):.1f}% used)

Safety Controls:
- Max Recursion Depth: {cost_status['max_recursion_depth']}
- Calls Today: {cost_status['total_calls_today']}
- Total Lifetime Cost: ${cost_status['total_lifetime_cost']:.4f}

Recent Calls:"""

        for call in recent_calls:
            report += f"\n- {
                call['timestamp'][
                    :19]}: ${
                call['cost']:.4f} ({
                call['input_tokens']}→{
                    call['output_tokens']} tokens)"

        return [types.TextContent(type="text", text=report)]

    elif name == "summit_learn_capability":
        capability_description = arguments.get("capability_description")
        requirements = arguments.get("requirements")
        machine_type = arguments.get("machine_type", "standardLinux32gb")

        if not capability_description:
            raise ValueError("Capability description is required")

        try:
            # Get repository information
            owner, repo = get_repository_url()
            if not owner or not repo:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Could not determine GitHub repository. Please set GITHUB_OWNER and GITHUB_REPO environment variables.",
                    )
                ]

            # Plan the implementation
            implementation_plan = await plan_capability_implementation(
                capability_description, requirements
            )

            # Create a new codespace for development
            codespace_data = await create_codespace(owner, repo, machine_type)

            # Start the codespace
            await start_codespace(codespace_data["name"])

            # Generate implementation instructions
            instructions = await implement_capability_in_codespace(
                codespace_data["web_url"],
                implementation_plan,
                capability_description,
            )

            response = f"""Summit is learning a new capability!

Capability: {capability_description}
Development Environment: {codespace_data['name']}
Status: {codespace_data['state']}

{instructions}

I'll track this learning session and help you deploy the changes when ready."""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error starting learning session: {e}"
                )
            ]

    elif name == "summit_codespace_status":
        try:
            # List all codespaces
            all_codespaces = await list_user_codespaces()

            # Filter for Summit-related codespaces
            summit_codespaces = [
                cs
                for cs in all_codespaces
                if "Summit" in cs.get("display_name", "")
                or cs["name"] in active_codespaces
            ]

            if not summit_codespaces:
                response = "No active Summit development environments found."
            else:
                response = "Summit Development Environments Status:\n\n"
                for cs in summit_codespaces:
                    status_emoji = (
                        ""
                        if cs["state"] == "Available"
                        else "" if cs["state"] == "Starting" else ""
                    )
                    response += f"{status_emoji} {cs['name']}\n"
                    response += f"   Status: {cs['state']}\n"
                    response += f"   Created: {cs['created_at'][:19].replace('T', ' ')}\n"
                    response += f"   URL: {cs['web_url']}\n\n"

                response += f"Total environments: {len(summit_codespaces)}"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error checking codespace status: {e}"
                )
            ]

    elif name == "summit_deploy_changes":
        codespace_name = arguments.get("codespace_name")
        commit_message = arguments.get("commit_message")

        if not codespace_name or not commit_message:
            raise ValueError("Codespace name and commit message are required")

        try:
            # Get codespace status to verify it exists and is accessible
            codespace_status = await get_codespace_status(codespace_name)

            # In a full implementation, this would:
            # 1. Connect to the codespace
            # 2. Run tests to validate changes
            # 3. Commit and push changes
            # 4. Potentially restart the Summit server with new capabilities

            # For now, provide instructions for manual deployment
            instructions = f"""
Deployment Instructions for Summit Learning Session:

Codespace: {codespace_name}
Status: {codespace_status['state']}
URL: {codespace_status['web_url']}

Manual Deployment Steps:
1. Ensure all changes are tested and working in the codespace
2. Commit your changes:
   git add .
   git commit -m "{commit_message}"
3. Push to the repository:
   git push origin main
4. The changes will be available for the next Summit restart

Automated deployment capabilities are coming in future versions!
"""

            # Stop the codespace to save resources (optional)
            await stop_codespace(codespace_name)

            response = f"""Deployment initiated for Summit learning session!

{instructions}

The development environment has been stopped to save resources.
Use summit_cleanup_environment to remove it when no longer needed."""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error deploying changes: {e}"
                )
            ]

    elif name == "summit_cleanup_environment":
        codespace_name = arguments.get("codespace_name")

        if not codespace_name:
            raise ValueError("Codespace name is required")

        try:
            # Stop the codespace first (if running)
            try:
                await stop_codespace(codespace_name)
            except Exception as e:
                logger.debug(
                    f"Error stopping codespace (may already be stopped): {str(e)}"
                )  # Log instead of silently passing

            # Delete the codespace
            await delete_codespace(codespace_name)

            response = f"""Development environment cleaned up successfully!

Codespace '{codespace_name}' has been:
- Stopped (if running)
- Deleted to free resources
- Removed from active tracking

Ready for the next capability development session!"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error cleaning up environment: {e}"
                )
            ]

    # Task Management Tool Handlers
    elif name == "summit_get_task":
        task_id = arguments.get("task_id")
        include_collaboration = arguments.get("include_collaboration", False)

        if not task_id:
            raise ValueError("Task ID is required")

        try:
            from unified_database import get_database

            db = await get_database()

            if include_collaboration:
                task_data = await db.get_task_with_collaboration_data(task_id)
                if not task_data:
                    return [
                        types.TextContent(
                            type="text", text=f"Task {task_id} not found"
                        )
                    ]

                response = f"""Task Details (with collaboration data):

ID: {task_data['id']}
Type: {task_data['task_type']}
Status: {task_data['status']}
Assigned Role: {task_data['assigned_role']}
Agent: {task_data['agent_id'] or 'Unassigned'}
Priority: {task_data['priority']}
Created: {task_data['created_at']}

Comments ({len(task_data['comments'])}):"""

                for comment in task_data["comments"]:
                    response += f"""
- [{comment['comment_type']}] by {comment['agent_id']}: {comment['content'][:100]}..."""

                response += f"""

Reviews ({len(task_data['reviews'])}):"""

                for review in task_data["reviews"]:
                    response += f"""
- [{review['review_type']}] {review['decision']} by {review['reviewer_agent_id']}"""

            else:
                task = await db.get_agent_task(task_id)
                if not task:
                    return [
                        types.TextContent(
                            type="text", text=f"Task {task_id} not found"
                        )
                    ]

                task_data = task.to_dict()
                response = f"""Task Details:

ID: {task_data['id']}
Type: {task_data['task_type']}
Status: {task_data['status']}
Assigned Role: {task_data['assigned_role']}
Agent: {task_data['agent_id'] or 'Unassigned'}
Priority: {task_data['priority']}
Created: {task_data['created_at']}
Payload: {task_data['payload']}"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error retrieving task: {e}"
                )
            ]

    elif name == "summit_list_tasks":
        role = arguments.get("role")
        status = arguments.get("status")
        limit = arguments.get("limit", 20)

        try:
            from database_models import TaskStatus
            from unified_database import get_database

            db = await get_database()

            if role:
                tasks = await db.get_tasks_for_role(role, limit)
            else:
                # Get all recent tasks
                from datetime import datetime, timedelta

                since_date = datetime.utcnow() - timedelta(days=7)
                tasks = await db.get_tasks_since(since_date, limit)

            # Filter by status if provided
            if status:
                status_enum = getattr(TaskStatus, status.upper(), None)
                if status_enum:
                    tasks = [t for t in tasks if t.status == status_enum]

            if not tasks:
                filter_desc = f" (role: {role})" if role else ""
                filter_desc += f" (status: {status})" if status else ""
                return [
                    types.TextContent(
                        type="text",
                        text=f"No tasks found{filter_desc}",
                    )
                ]

            response = f"Found {len(tasks)} task(s):\n\n"
            for task in tasks[:limit]:
                task_data = task.to_dict()
                response += f"""• {task_data['id'][:8]}... - {task_data['task_type']}
  Status: {task_data['status']} | Role: {task_data['assigned_role']}
  Created: {task_data['created_at'][:10]}

"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error listing tasks: {e}"
                )
            ]

    elif name == "summit_update_task_status":
        task_id = arguments.get("task_id")
        status = arguments.get("status")
        agent_id = arguments.get("agent_id")
        result = arguments.get("result")
        error = arguments.get("error")

        if not all([task_id, status, agent_id]):
            raise ValueError("Task ID, status, and agent ID are required")

        try:
            from datetime import datetime

            from database_models import TaskStatus
            from unified_database import get_database

            db = await get_database()

            # Validate status
            try:
                status_enum = getattr(TaskStatus, status.upper())
            except AttributeError:
                valid_statuses = [s.value for s in TaskStatus]
                return [
                    types.TextContent(
                        type="text",
                        text=f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}",
                    )
                ]

            # Prepare update data
            updates = {
                "status": status_enum,
                "agent_id": agent_id,
            }

            if status_enum in [TaskStatus.RUNNING]:
                updates["started_at"] = datetime.utcnow()
            elif status_enum in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                updates["completed_at"] = datetime.utcnow()

            if result:
                updates["result"] = result
            if error:
                updates["error"] = error

            updated_task = await db.update_agent_task(task_id, updates)

            if not updated_task:
                return [
                    types.TextContent(
                        type="text", text=f"Task {task_id} not found"
                    )
                ]

            response = f"""Task status updated successfully:

Task: {task_id}
New Status: {status}
Updated by: {agent_id}
"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error updating task status: {e}"
                )
            ]

    elif name == "summit_add_task_comment":
        task_id = arguments.get("task_id")
        agent_id = arguments.get("agent_id")
        comment_type = arguments.get("comment_type", "general")
        content = arguments.get("content")

        if not all([task_id, agent_id, content]):
            raise ValueError(
                "Task ID, agent ID, and comment content are required"
            )

        try:
            from unified_database import get_database

            db = await get_database()

            comment = await db.add_task_comment(
                task_id, agent_id, comment_type, content
            )

            if not comment:
                return [
                    types.TextContent(
                        type="text", text=f"Task {task_id} not found"
                    )
                ]

            response = f"""Comment added successfully:

Task: {task_id}
Comment Type: {comment_type}
Added by: {agent_id}
Content: {content[:100]}{"..." if len(content) > 100 else ""}
Comment ID: {comment.id}"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error adding comment: {e}"
                )
            ]

    elif name == "summit_get_task_comments":
        task_id = arguments.get("task_id")
        include_internal = arguments.get("include_internal", True)

        if not task_id:
            raise ValueError("Task ID is required")

        try:
            from unified_database import get_database

            db = await get_database()

            comments = await db.get_task_comments(task_id, include_internal)

            if not comments:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No comments found for task {task_id}",
                    )
                ]

            response = (
                f"Comments for task {task_id} ({len(comments)} total):\n\n"
            )

            for comment in comments:
                comment_data = comment.to_dict()
                response += f"""[{comment_data['comment_type']}] by {comment_data['agent_id']}
{comment_data['created_at'][:19]}
{comment_data['content']}
"""
                if comment_data["approval_status"]:
                    response += f"Status: {comment_data['approval_status']}\n"
                if comment_data["rating"]:
                    response += f"Rating: {comment_data['rating']}/5\n"
                response += "\n"

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error retrieving comments: {e}"
                )
            ]

    elif name == "summit_create_task_review":
        task_id = arguments.get("task_id")
        reviewer_agent_id = arguments.get("reviewer_agent_id")
        review_type = arguments.get("review_type")
        decision = arguments.get("decision")
        summary = arguments.get("summary")
        findings = arguments.get("findings", [])
        recommendations = arguments.get("recommendations", [])
        quality_score = arguments.get("quality_score")
        confidence = arguments.get("confidence", 1.0)

        if not all(
            [task_id, reviewer_agent_id, review_type, decision, summary]
        ):
            raise ValueError(
                "Task ID, reviewer agent ID, review type, decision, and summary are required"
            )

        try:
            from unified_database import get_database

            db = await get_database()

            # Prepare review data
            review_data = {
                "confidence": confidence,
                "findings": findings,
                "recommendations": recommendations,
            }

            if quality_score is not None:
                review_data["quality_score"] = quality_score

            review = await db.create_task_review(
                task_id=task_id,
                reviewer_agent_id=reviewer_agent_id,
                review_type=review_type,
                decision=decision,
                summary=summary,
                **review_data,
            )

            response = f"""Task review created successfully:

Task: {task_id}
Review Type: {review_type}
Reviewer: {reviewer_agent_id}
Decision: {decision}
Quality Score: {quality_score}/10
Confidence: {confidence:.2f}

Summary: {summary}

Review ID: {review.id}"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error creating review: {e}"
                )
            ]

    elif name == "summit_get_agent_activity":
        agent_id = arguments.get("agent_id")
        limit = arguments.get("limit", 20)

        if not agent_id:
            raise ValueError("Agent ID is required")

        try:
            from unified_database import get_database

            db = await get_database()

            activity = await db.get_agent_task_activity(agent_id, limit)

            response = f"""Recent activity for agent {agent_id}:

Comments: {activity['total_comments']}
Reviews: {activity['total_reviews']}

Recent Comments:"""

            for comment in activity["recent_comments"][:5]:
                response += f"""
- {comment['created_at'][:10]}: [{comment['comment_type']}] on task {comment['task_id'][:8]}..."""

            response += "\n\nRecent Reviews:"

            for review in activity["recent_reviews"][:5]:
                response += f"""
- {review['created_at'][:10]}: [{review['review_type']}] {review['decision']} on task {review['task_id'][:8]}..."""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error retrieving agent activity: {e}"
                )
            ]

    # Simplified Agent Task Management
    elif name == "summit_start_task":
        task_id = arguments.get("task_id")
        agent_id = arguments.get("agent_id")

        if not all([task_id, agent_id]):
            raise ValueError("Task ID and agent ID are required")

        try:
            from datetime import datetime

            from database_models import TaskLifecycleStage, TaskStatus
            from unified_database import get_database

            db = await get_database()

            # Get the task
            task = await db.get_agent_task(task_id)
            if not task:
                return [
                    types.TextContent(
                        type="text", text=f"Task {task_id} not found"
                    )
                ]

            # Check if task is available
            if task.status not in [TaskStatus.PENDING, TaskStatus.FAILED]:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Task {task_id} is not available (status: {task.status.value})",
                    )
                ]

            # Claim and start the task
            updates = {
                "status": TaskStatus.RUNNING,
                "agent_id": agent_id,
                "started_at": datetime.utcnow(),
            }

            updated_task = await db.update_agent_task(task_id, updates)

            # Start the design stage in lifecycle
            await db.start_stage_work(
                task_id=task_id,
                agent_id=agent_id,
                stage=TaskLifecycleStage.DESIGN,
            )

            response = f"""Task started successfully:

Task: {task_id}
Agent: {agent_id}
Type: {updated_task.task_type}
Status: RUNNING
Started: {datetime.utcnow().isoformat()}

The task is now assigned to you and in the design stage.
Use summit_end_task when complete."""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error starting task: {e}"
                )
            ]

    elif name == "summit_end_task":
        task_id = arguments.get("task_id")
        agent_id = arguments.get("agent_id")
        success = arguments.get("success")
        result = arguments.get("result")
        summary = arguments.get("summary")
        files_modified = arguments.get("files_modified", [])
        error_message = arguments.get("error_message")
        quality_score = arguments.get("quality_score", 5.0)

        if not all([task_id, agent_id]):
            raise ValueError("Task ID and agent ID are required")

        if success is None:
            raise ValueError("Success status is required")

        try:
            from datetime import datetime

            from database_models import TaskLifecycleStage, TaskStatus
            from unified_database import get_database

            db = await get_database()

            # Get the task
            task = await db.get_agent_task(task_id)
            if not task:
                return [
                    types.TextContent(
                        type="text", text=f"Task {task_id} not found"
                    )
                ]

            # Verify agent owns this task
            if task.agent_id != agent_id:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Task {task_id} is not assigned to agent {agent_id}",
                    )
                ]

            # Complete current stage work
            await db.complete_stage_work(
                task_id=task_id,
                agent_id=agent_id,
                stage_output=result,
                stage_summary=summary,
                files_modified=files_modified,
                quality_score=quality_score,
                completion_status="completed" if success else "failed",
            )

            # Update task status
            final_status = (
                TaskStatus.COMPLETED if success else TaskStatus.FAILED
            )
            updates = {
                "status": final_status,
                "completed_at": datetime.utcnow(),
            }

            if success:
                updates["result"] = result
                # Transition through lifecycle stages automatically
                await db.transition_task_stage(
                    task_id=task_id,
                    agent_id=agent_id,
                    to_stage=TaskLifecycleStage.COMPLETED,
                    stage_output=result,
                    stage_summary=summary,
                    files_modified=files_modified,
                    quality_score=quality_score,
                    completion_status="completed",
                    transition_reason="Task completed successfully",
                )
            else:
                updates["error"] = error_message
                await db.transition_task_stage(
                    task_id=task_id,
                    agent_id=agent_id,
                    to_stage=TaskLifecycleStage.DESIGN,  # Stay in current stage
                    stage_output={"error": error_message},
                    stage_summary=f"Task failed: {error_message}",
                    files_modified=files_modified,
                    quality_score=quality_score,
                    completion_status="failed",
                    transition_reason="Task execution failed",
                )

            updated_task = await db.update_agent_task(task_id, updates)

            if success:
                response = f"""Task completed successfully:

Task: {task_id}
Agent: {agent_id}
Status: {final_status.value}
Quality Score: {quality_score}/10.0
Completed: {datetime.utcnow().isoformat()}

Summary: {summary or 'No summary provided'}
Files Modified: {len(files_modified)} files

The task has been marked as complete and lifecycle tracking updated."""
            else:
                response = f"""Task failed gracefully:

Task: {task_id}
Agent: {agent_id}
Status: {final_status.value}
Error: {error_message}
Failed: {datetime.utcnow().isoformat()}

The task failure has been recorded and can be retried or reassigned."""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(type="text", text=f"Error ending task: {e}")
            ]

    elif name == "summit_complete_task":
        """
        A simplified tool for completing tasks - combines setting status, results, and metadata
        This is the preferred method for OpenCode agents to mark tasks as complete
        """
        task_id = arguments.get("task_id")
        agent_id = arguments.get("agent_id")
        success = arguments.get("success", True)
        result = arguments.get("result", {})
        summary = arguments.get("summary", "")
        files_modified = arguments.get("files_modified", [])
        error_message = arguments.get("error_message", "")

        if not all([task_id, agent_id]):
            raise ValueError("Task ID and agent ID are required")

        try:
            from datetime import datetime

            from database_models import TaskStatus
            from unified_database import get_database

            db = await get_database()

            # Set appropriate status based on success flag
            status_enum = (
                TaskStatus.COMPLETED if success else TaskStatus.FAILED
            )

            # Prepare update data with metadata
            updates = {
                "status": status_enum,
                "agent_id": agent_id,
                "completed_at": datetime.utcnow(),
            }

            # Add result data
            result_data = {
                "summary": summary,
                "files_modified": files_modified,
            }

            # Include any additional result data provided
            if isinstance(result, dict):
                result_data.update(result)

            updates["result"] = result_data

            # Add error message if task failed
            if not success and error_message:
                updates["error"] = error_message

            # Update the task
            updated_task = await db.update_agent_task(task_id, updates)

            if not updated_task:
                return [
                    types.TextContent(
                        type="text", text=f"Task {task_id} not found"
                    )
                ]

            status_word = "completed successfully" if success else "failed"
            response = f"""Task {status_word}:

Task: {task_id}
Status: {status_enum.value}
Agent: {agent_id}
Summary: {summary[:100]}{"..." if len(summary) > 100 else ""}
Files Modified: {', '.join(files_modified[:5])}{"..." if len(files_modified) > 5 else ""}
"""

            return [types.TextContent(type="text", text=response)]

        except Exception as e:
            return [
                types.TextContent(
                    type="text", text=f"Error completing task: {e}"
                )
            ]

    else:
        raise ValueError(f"Summit doesn't know tool: {name}")


async def create_codespace(
    owner: str,
    repo: str,
    machine_type: str = "standardLinux32gb",
    ref: str = "main",
) -> Dict:
    """Create a new GitHub Codespace for development"""
    headers = get_github_headers()
    if not headers:
        raise ValueError(
            "GITHUB_TOKEN environment variable is required for Codespaces"
        )

    url = f"https://api.github.com/repos/{owner}/{repo}/codespaces"

    payload = {
        "ref": ref,
        "machine": machine_type,
        "display_name": f"Summit Learning Session - {time.strftime('%Y%m%d-%H%M%S')}",
        "idle_timeout_minutes": 60,
        "retention_period_minutes": 1440,  # 24 hours
    }

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()

        codespace_data = response.json()

        # Store in active codespaces
        active_codespaces[codespace_data["name"]] = {
            "id": codespace_data["id"],
            "name": codespace_data["name"],
            "state": codespace_data["state"],
            "web_url": codespace_data["web_url"],
            "created_at": codespace_data["created_at"],
            "purpose": "capability_learning",
        }

        return codespace_data

    except requests.RequestException as e:
        raise Exception(f"Failed to create codespace: {e}")


async def start_codespace(codespace_name: str) -> Dict:
    """Start an existing codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com/user/codespaces/{codespace_name}/start"

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()

        codespace_data = response.json()

        # Update stored info
        if codespace_name in active_codespaces:
            active_codespaces[codespace_name]["state"] = codespace_data[
                "state"
            ]

        return codespace_data

    except requests.RequestException as e:
        raise Exception(f"Failed to start codespace: {e}")


async def stop_codespace(codespace_name: str) -> Dict:
    """Stop a running codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com/user/codespaces/{codespace_name}/stop"

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()

        codespace_data = response.json()

        # Update stored info
        if codespace_name in active_codespaces:
            active_codespaces[codespace_name]["state"] = codespace_data[
                "state"
            ]

        return codespace_data

    except requests.RequestException as e:
        raise Exception(f"Failed to stop codespace: {e}")


async def delete_codespace(codespace_name: str) -> bool:
    """Delete a codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com/user/codespaces/{codespace_name}"

    try:
        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Remove from active codespaces
        if codespace_name in active_codespaces:
            del active_codespaces[codespace_name]

        return True

    except requests.RequestException as e:
        raise Exception(f"Failed to delete codespace: {e}")


async def get_codespace_status(codespace_name: str) -> Dict:
    """Get the current status of a codespace"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = f"https://api.github.com/user/codespaces/{codespace_name}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:
        raise Exception(f"Failed to get codespace status: {e}")


async def list_user_codespaces() -> List[Dict]:
    """List all user codespaces"""
    headers = get_github_headers()
    if not headers:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    url = "https://api.github.com/user/codespaces"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json().get("codespaces", [])
    except Exception as e:
        raise Exception(f"Failed to list codespaces: {e}")


async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str = "main",
    body: str = "",
    enable_auto_merge: bool = True,
) -> Dict:
    """Create a new pull request with optional auto-merge"""
    headers = get_github_headers()
    if not headers:
        raise ValueError(
            "GITHUB_TOKEN environment variable is required for creating pull requests"
        )

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "maintainer_can_modify": True,
    }

    try:
        # Create the PR first
        response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )
        response.raise_for_status()

        pr_data = response.json()
        pr_number = pr_data["number"]

        # Enable auto-merge if requested
        if enable_auto_merge:
            try:
                auto_merge_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/merge"
                auto_merge_payload = {
                    "merge_method": "squash"  # or "merge" or "rebase"
                }

                # Use GraphQL API for auto-merge (REST API doesn't support it
                # yet)
                graphql_url = "https://api.github.com/graphql"
                graphql_query = """
                mutation($pullRequestId: ID!) {
                  enablePullRequestAutoMerge(input: {
                    pullRequestId: $pullRequestId,
                    mergeMethod: SQUASH
                  }) {
                    pullRequest {
                      autoMergeRequest {
                        enabledAt
                        enabledBy {
                          login
                        }
                      }
                    }
                  }
                }
                """

                graphql_payload = {
                    "query": graphql_query,
                    "variables": {
                        "pullRequestId": pr_data[
                            "node_id"
                        ]  # GraphQL needs node_id
                    },
                }

                graphql_response = requests.post(
                    graphql_url,
                    headers=headers,
                    json=graphql_payload,
                    timeout=30,
                )

                if graphql_response.status_code == 200:
                    graphql_data = graphql_response.json()
                    if "errors" not in graphql_data:
                        print(f"Auto-merge enabled for PR #{pr_number}")
                    else:
                        print(
                            f"Auto-merge failed: {
                                graphql_data.get(
                                    'errors', 'Unknown error')}"
                        )
                else:
                    print(
                        f"Auto-merge request failed with status {
                            graphql_response.status_code}"
                    )

            except Exception as e:
                print(
                    f"Warning: Could not enable auto-merge for PR #{pr_number}: {e}"
                )
                # Don't fail the PR creation if auto-merge fails

        return {
            "number": pr_data["number"],
            "url": pr_data["html_url"],
            "state": pr_data["state"],
            "title": pr_data["title"],
            "head": pr_data["head"]["ref"],
            "base": pr_data["base"]["ref"],
            "auto_merge_enabled": enable_auto_merge,
        }
    except Exception as e:
        raise Exception(f"Failed to create pull request: {e}")


async def plan_capability_implementation(
    capability_description: str, requirements: Optional[str] = None
) -> str:
    """Use Claude to plan the implementation of a new capability"""
    client = get_anthropic_client()

    if not client:
        return "Summit needs an ANTHROPIC_API_KEY to plan capability implementations."

    # Get current codebase context
    owner, repo = get_repository_url()
    if not owner or not repo:
        codebase_context = "Working with local Summit codebase"
    else:
        codebase_context = f"Working with Summit repository: {owner}/{repo}"

    planning_prompt = f"""You are Summit, an AI that can learn new capabilities by modifying its own code. You need to plan how to implement a new capability following the MANDATORY DEVELOPMENT PROCESS.

CRITICAL: You MUST follow the complete development workflow from CODING_STANDARDS.md:

1. ANALYSIS PHASE - Understand requirement, examine codebase, identify integration points
2. IMPLEMENTATION PHASE - Write clean code, add comprehensive tests
3. QUALITY ASSURANCE PHASE - Run coverage, linting, formatting
4. GIT OPERATIONS PHASE - Add, commit, push with proper messages
5. VERIFICATION PHASE - Confirm tests pass, coverage >70%, clean quality

Current Context:
- {codebase_context}
- Summit is a Python MCP server with tool handlers
- Current capabilities include: advice, knowledge sharing, search, analytics
- Uses GitHub Codespaces for isolated development environments

New Capability Request:
{capability_description}

{f"Requirements: {requirements}" if requirements else ""}

Provide a COMPLETE implementation plan that follows the mandatory 5-phase process:

## Phase 1: Analysis
- Codebase examination commands to run
- Integration points identified
- Dependencies analysis

## Phase 2: Implementation
- Specific files to create/modify
- New functions/tools to add
- Test files to create
- Code structure following existing patterns

## Phase 3: Quality Assurance
- Testing commands to execute
- Coverage verification steps
- Linting/formatting commands

## Phase 4: Git Operations
- Exact git commands to run
- Commit message format
- Push verification

## Phase 5: Verification
- Final validation steps
- Success criteria

Be extremely specific about commands to run and code to write. The agent must follow this workflow exactly or the changes will be REJECTED."""

    try:
        message = client.messages.create(
            model=SUMMIT_CONFIG["chat_model"],
            max_tokens=1500,
            messages=[{"role": "user", "content": planning_prompt}],
        )

        return message.content[0].text

    except Exception as e:
        return f"Error planning implementation: {e}"


async def implement_capability_in_codespace(
    codespace_url: str, implementation_plan: str, capability_description: str
) -> str:
    """
    Implement the capability in the codespace environment
    This is a simplified version - in practice, you'd use the Codespaces API
    or VS Code extension API to execute commands and modify files.
    """

    # For now, we'll provide detailed instructions for manual implementation
    # In a full implementation, this would use the Codespaces API to:
    # 1. Clone the repository
    # 2. Create/modify files
    # 3. Run tests
    # 4. Validate changes

    instructions = f"""
Summit Learning Session Instructions

Codespace URL: {codespace_url}

 CRITICAL: You MUST follow the MANDATORY DEVELOPMENT PROCESS from CODING_STANDARDS.md

Capability to Implement:
{capability_description}

Implementation Plan:
{implementation_plan}

REQUIRED WORKFLOW - Execute these phases in order:

## Phase 1: Analysis (MANDATORY)
```bash
# Open codespace: {codespace_url}
# Navigate to Summit codebase
cat CODING_STANDARDS.md          # Read the complete workflow
find . -name "*.py" | head -20    # Understand codebase structure
  grep -r "def " src/               # Find existing functions
  ```

## Phase 2: Implementation (MANDATORY)
- Follow the implementation plan above
- Create/modify files following existing patterns
- Add comprehensive tests for ALL new functionality
- Use meaningful names, no obvious comments

## Phase 3: Quality Assurance (MANDATORY)
```bash
# REQUIRED: Execute these commands before any commit
python run_coverage.py           # Check test coverage
pytest --cov=src --cov-report=term-missing  # Detailed coverage report
python -m pylint src/ || echo "Linting check attempted"   # Code quality
python -m black src/ tests/ || echo "Formatting attempted" # Code formatting
```

## Phase 4: Git Operations (MANDATORY)
 **CRITICAL: NEVER COMMIT WITH FAILING TESTS**
```bash
# REQUIRED: Complete Git workflow - ONLY if ALL tests pass
git add .                        # Stage all changes
git status                       # Verify what's being committed
git commit -m "Add [feature]: [description] - [coverage%] coverage"
git push origin main            # Push to repository
```

## Phase 5: Verification (MANDATORY)
```bash
# REQUIRED: Final validation - MUST BE GREEN BEFORE COMMIT
python run_coverage.py          # Confirm ALL tests pass
echo "Coverage target: >70%"    # Verify coverage maintained
echo "All tests must be GREEN"  # Confirm no failures
```

 **CRITICAL: NO COMMITS WITH FAILING TESTS**
  FAILURE TO FOLLOW THIS COMPLETE WORKFLOW = REJECTION

The implementation will be rejected if you skip any phase. You must demonstrate:
 Proper analysis and understanding
 Comprehensive testing with ALL tests passing (100% green)
 Coverage >70% verified before commit
 Quality assurance execution
 Complete Git workflow ONLY after tests pass
 Final verification with zero failures

Environment provides: Ubuntu, Python 3.x, Git, VS Code, all dependencies
"""

    return instructions


async def main():
    """Run Summit MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            NotificationOptions(),
        )


if __name__ == "__main__":
    print(
        "Summit AI Advisor is running with cost controls enabled!",
        file=sys.stderr,
    )
    asyncio.run(main())
