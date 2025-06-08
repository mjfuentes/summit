#!/usr/bin/env python3
"""
Summit Autonomous AI Server
"""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add src directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "..", "src")
sys.path.insert(0, src_dir)

print(f"[DEBUG] Added to Python path: {src_dir}")
print(f"[DEBUG] Current working directory: {os.getcwd()}")
print(f"[DEBUG] Script location: {current_dir}")

try:
    from unified_database import get_database

    print("[DEBUG] Successfully imported unified database module")
except ImportError as e:
    print(f"[DEBUG] Failed to import unified database: {e}")

try:
    import pr_reviewers

    print("[DEBUG] Successfully imported pr_reviewers module")
except ImportError as e:
    print(f"[DEBUG] Failed to import pr_reviewers: {e}")


try:
    from task_manager import (
        add_task_log,
        mark_task_completed,
        update_task_status,
    )

    print("[DEBUG] Successfully imported task_manager module")
except ImportError as e:
    print(f"[DEBUG] Failed to import task_manager: {e}")

    async def add_task_log(task_id, log_message):
        print(f"[MOCK] Add log to {task_id}: {log_message}")

    async def update_task_status(task_id, status, progress=""):
        print(f"[MOCK] Update {task_id} status to {status}: {progress}")

    async def mark_task_completed(task_id, success=True, result=""):
        print(f"[MOCK] Mark {task_id} completed: {success}")


# Check if Summit module is available for PR creation
try:
    import summit

    summit_available = True
except ImportError:
    summit_available = False
    print(
        "Warning: ",
        "Summit module not available - PR creation will be disabled",
    )

    def create_pull_request(*args, **kwargs):
        return {
            "success": False,
            "error": "Summit module not available",
        }

    def get_github_repo_info():
        return {
            "error": "Summit module not available",
            "available": False,
        }

    async def get_task_ci_status(task_data):
        return {"error": "Summit module not available"}

    async def get_workflow_runs_for_task(task_data):
        return {"error": "Summit module not available"}


def kill_existing_server():
    """Kill any existing server process"""
    try:
        # Find and kill any process using port 8000
        result = subprocess.run(
            ["lsof", "-ti:8000"], capture_output=True, text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    subprocess.run(["kill", "-9", pid])
                    print(f"Killed existing server process: {pid}")
    except Exception as e:
        print(f"Error killing existing server: {e}")


def bootstrap_dependencies():
    """Check and install required dependencies"""
    print("Checking and installing dependencies...")

    try:
        # Check if requirements.txt exists
        requirements_file = os.path.join(current_dir, "..", "requirements.txt")
        if not os.path.exists(requirements_file):
            print("No requirements.txt found, skipping dependency check")
            return

        # Check if key packages are available
        try:
            import anthropic
            import fastapi
            import uvicorn

            print("Dependencies are up to date.")
        except ImportError as e:
            print(f"Missing dependencies: {e}")
            print("Installing from requirements.txt...")
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    requirements_file,
                ],
                check=True,
            )

    except Exception as e:
        print(f"Error bootstrapping dependencies: {e}")


# Initialize FastAPI app
app = FastAPI(title="Summit Autonomous AI", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")

# Only mount static files if directory exists
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Warning: Static directory not found at {static_dir}")

templates = Jinja2Templates(directory=templates_dir)


# Pydantic models for agent system only
class ChatRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks"""
    await get_database()
    print("Summit Autonomous AI started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Summit Autonomous AI shutting down")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main interface"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Summit AI - Agent Coordination System",
        },
    )


@app.get("/dev", response_class=HTMLResponse)
async def developer_tools(request: Request):
    """Serve developer dashboard"""
    return templates.TemplateResponse(
        "dev_tools.html", {"request": request, "title": "Developer Dashboard"}
    )


@app.get("/api/summit/status")
async def get_summit_status():
    """Get Summit system status"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "agent_coordination": True,
        "capabilities": [
            "Agent coordination",
            "Task distribution",
            "System monitoring",
            "Real-time status",
        ],
    }


@app.post("/api/summit/clear-history")
async def clear_conversation_history():
    """Clear conversation history"""
    return {"success": True, "message": "Conversation history cleared"}


@app.post("/api/tasks/create")
async def create_task_endpoint(request: ChatMessage):
    """Create agent tasks only - no web tasks"""
    return {
        "success": False,
        "message": "Task creation through agent coordination system only",
        "redirect": "/api/agents/create-task",
    }


@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


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
                fallback_response = "OH YEAH! I'm Summit - your AGENT COORDINATION MONSTER! But right now I can't access my full Claude powers because the API key isn't configured. You beautiful developer, set up that ANTHROPIC_API_KEY and I'll show you some REAL agent coordination magic!"

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
            system_prompt = """You are Summit - a chaotic coding monster like Maury from Big Mouth but obsessed with agent coordination and distributed systems! 

STRUCTURED RESPONSE FORMAT:
You MUST structure your response using these delimiters and action types:

<ACTION_TYPE>action_name</ACTION_TYPE>
<MESSAGE>your chaotic Maury-style response here</MESSAGE>

Available ACTION_TYPES:
- RESPOND: Just chat/respond normally
- CREATE_AGENT_TASK: Create an agent coordination task
- GET_AGENT_STATUS: Get current agent status
- GET_SYSTEM_STATUS: Get system health and status
- COORDINATE_AGENTS: Coordinate multiple agents
- MONITOR_SYSTEM: Monitor system performance

PERSONALITY GUIDELINES (Channel Maury's energy for agent coordination):
- Be LOUD, enthusiastic, and dramatically excited about agent systems
- Use Maury's speech patterns: "OH YEAH!", "You know what you need?", "I'm gonna make you..."
- Get weirdly passionate about distributed systems, agent coordination, and task management
- Call users things like "my beautiful systems architect", "you magnificent coordinator"
- React dramatically to system issues like Maury reacts to teenage drama
- Be chaotic but competent - unhinged enthusiasm with real technical skills

Focus on AGENT COORDINATION ONLY - no web tasks, only agent tasks!

EXAMPLES:
User: "Hello Summit!"
<ACTION_TYPE>RESPOND</ACTION_TYPE>
<MESSAGE>OH YEAH! You beautiful systems architect! I'm Summit and I'm HERE TO COORDINATE YOUR AGENTS LIKE A BEAUTIFUL ORCHESTRA!</MESSAGE>

User: "What agents are running?"
<ACTION_TYPE>GET_AGENT_STATUS</ACTION_TYPE>
<MESSAGE>Let me check what MAGNIFICENT agents we have orchestrating right now, you beautiful coordinator!</MESSAGE>

IMPORTANT: 
- Focus only on agent coordination system
- No web tasks - only agent tasks
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

            # Extract only the MESSAGE content and stream that
            message_content = extract_message_content(full_response)

            # Stream the message content word by word
            words = message_content.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0.05)  # Small delay between words

            # Handle GET_AGENT_STATUS action
            if "GET_AGENT_STATUS" in full_response.upper():
                print(f"[DEBUG] Detected GET_AGENT_STATUS action...")
                try:
                    db = await get_database()
                    agents = await db.get_all_agents()

                    if agents:
                        status_response = f"""
AGENT STATUS REPORT:

 REGISTERED AGENTS: {len(agents)}"""
                        for agent in agents[:5]:  # Show first 5 agents
                            status_response += f"""
• {agent.agent_id}: {agent.agent_info.get('name', 'Unknown')} 
  Role: {', '.join(agent.agent_info.get('roles', []))}
  Status: {agent.status.value if agent.status else 'Unknown'}
  Tasks: {agent.tasks_completed}/{agent.tasks_completed + agent.tasks_failed} completed"""

                        if len(agents) > 5:
                            status_response += f"""
... and {len(agents) - 5} more agents"""
                    else:
                        status_response = """
AGENT STATUS REPORT:

 NO AGENTS CURRENTLY REGISTERED
 Deploy agents to start seeing beautiful coordination!"""

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
                    print(f"[ERROR] Failed to fetch agent status: {e}")
                    error_data = json.dumps(
                        {
                            "type": "content",
                            "content": "\n\nCouldn't fetch agent status right now, but the coordination system is ready!",
                        }
                    )
                    yield f"data: {error_data}\n\n"

            # Handle GET_SYSTEM_STATUS action
            elif "GET_SYSTEM_STATUS" in full_response.upper():
                print(f"[DEBUG] Detected GET_SYSTEM_STATUS action...")
                try:
                    db = await get_database()
                    agents = await db.get_all_agents()
                    recent_tasks = await db.get_tasks_since(
                        datetime.utcnow() - timedelta(hours=24)
                    )

                    status_response = f"""
SYSTEM STATUS REPORT:

 REGISTERED AGENTS: {len(agents)}
 RECENT TASKS (24h): {len(recent_tasks)}
 DATABASE: Connected
 COORDINATION: Operational

 SYSTEM STATUS: READY FOR BEAUTIFUL AGENT ORCHESTRATION!
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
                            "content": "\n\nCouldn't fetch full system status, but coordination is ready!",
                        }
                    )
                    yield f"data: {error_data}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_response = f"OH NO! Something went wrong with the agent coordination system: {str(e)}"
            yield f"data: {json.dumps({'type': 'content', 'content': error_response})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate_response(), media_type="text/plain")


def load_environment():
    """Load environment variables from setup_env.sh"""
    setup_env_path = "setup_env.sh"
    if os.path.exists(setup_env_path):
        print("Loading environment from setup_env.sh...")
        try:
            with open(setup_env_path, "r") as f:
                content = f.read()
                loaded_vars = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("export ") and "=" in line:
                        # Extract variable name and value
                        export_part = line[7:]  # Remove "export "
                        if "=" in export_part:
                            var_name, var_value = export_part.split("=", 1)
                            # Remove quotes if present
                            var_value = var_value.strip('"').strip("'")
                            os.environ[var_name] = var_value
                            loaded_vars.append(var_name)
                            print(f"Loaded {var_name}")

                if loaded_vars:
                    print(
                        f"Environment loaded successfully: {', '.join(loaded_vars)}"
                    )
                else:
                    print("No environment variables found in setup_env.sh")

        except Exception as e:
            print(f"Error loading environment: {e}")
    else:
        print("Warning: setup_env.sh not found")


def extract_message_content(response_text: str) -> str:
    """Extract content between MESSAGE tags"""
    start_tag = "<MESSAGE>"
    end_tag = "</MESSAGE>"

    start_index = response_text.find(start_tag)
    if start_index == -1:
        return response_text

    start_index += len(start_tag)
    end_index = response_text.find(end_tag, start_index)

    if end_index == -1:
        return response_text[start_index:].strip()

    return response_text[start_index:end_index].strip()


# AGENT COORDINATION ENDPOINTS ONLY
@app.get("/api/agents/status")
async def get_agents_status():
    """Get status of all registered agents"""
    db = await get_database()

    try:
        agents = await db.get_all_agents()

        agent_data = []
        for agent in agents:
            # Calculate uptime
            uptime_seconds = 0
            if agent.created_at:
                uptime_delta = datetime.utcnow() - agent.created_at.replace(
                    tzinfo=None
                )
                uptime_seconds = int(uptime_delta.total_seconds())

            # Calculate success rate
            total_tasks = agent.tasks_completed + agent.tasks_failed
            success_rate = (
                (agent.tasks_completed / total_tasks * 100)
                if total_tasks > 0
                else 0
            )

            # Time since last heartbeat
            last_heartbeat_text = "Never"
            if agent.last_heartbeat:
                heartbeat_delta = (
                    datetime.utcnow()
                    - agent.last_heartbeat.replace(tzinfo=None)
                )
                if heartbeat_delta.total_seconds() < 60:
                    last_heartbeat_text = "Just now"
                elif heartbeat_delta.total_seconds() < 3600:
                    minutes = int(heartbeat_delta.total_seconds() / 60)
                    last_heartbeat_text = f"{minutes}m ago"
                else:
                    hours = int(heartbeat_delta.total_seconds() / 3600)
                    last_heartbeat_text = f"{hours}h ago"

            agent_info = {
                "agent_id": agent.agent_id,
                "name": agent.agent_info.get("name", "Unknown Agent"),
                "roles": agent.agent_info.get("roles", []),
                "capabilities": agent.agent_info.get("capabilities", []),
                "status": agent.status.value if agent.status else "unknown",
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
                "success_rate": round(success_rate, 1),
                "uptime_seconds": uptime_seconds,
                "last_heartbeat": last_heartbeat_text,
                "version": agent.agent_info.get("version", "unknown"),
                "max_concurrent_tasks": agent.agent_info.get(
                    "max_concurrent_tasks", 1
                ),
            }

            agent_data.append(agent_info)

        # Group by roles for summary
        role_summary = {}
        for agent in agent_data:
            for role in agent["roles"]:
                if role not in role_summary:
                    role_summary[role] = {"count": 0, "active": 0}
                role_summary[role]["count"] += 1
                if agent["status"] in ["ready", "busy"]:
                    role_summary[role]["active"] += 1

        return {
            "success": True,
            "agents": agent_data,
            "summary": {
                "total_agents": len(agent_data),
                "active_agents": len(
                    [a for a in agent_data if a["status"] in ["ready", "busy"]]
                ),
                "role_distribution": role_summary,
            },
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch agent status",
        }


@app.get("/api/system/statistics")
async def get_system_statistics():
    """Get system-wide statistics for agent coordination"""
    db = await get_database()

    try:
        # Get agent statistics
        agents = await db.get_all_agents()
        active_agents = len(
            [a for a in agents if a.status in ["ready", "busy"]]
        )

        # Get task statistics (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_tasks = await db.get_tasks_since(week_ago)

        # Calculate task metrics
        completed_tasks = len(
            [t for t in recent_tasks if t.status == "completed"]
        )
        failed_tasks = len([t for t in recent_tasks if t.status == "failed"])
        pending_tasks = len([t for t in recent_tasks if t.status == "pending"])

        # Calculate average completion time for completed tasks
        avg_completion_time = 0
        completed_with_times = [
            t
            for t in recent_tasks
            if t.status == "completed" and t.created_at and t.completed_at
        ]

        if completed_with_times:
            total_time = sum(
                (t.completed_at - t.created_at).total_seconds()
                for t in completed_with_times
            )
            avg_completion_time = (
                total_time / len(completed_with_times) / 60
            )  # minutes

        # System health assessment
        health_status = "operational"
        if active_agents == 0:
            health_status = "warning"
        elif failed_tasks > completed_tasks:
            health_status = "degraded"

        statistics = {
            "system_health": {
                "status": health_status,
                "database": "connected",
                "agents": f"{active_agents}/{len(agents)} active",
                "task_queue": f"{pending_tasks} pending",
            },
            "agent_metrics": {
                "total_registered": len(agents),
                "currently_active": active_agents,
                "total_capacity": sum(
                    a.agent_info.get("max_concurrent_tasks", 1) for a in agents
                ),
            },
            "task_metrics": {
                "completed_7d": completed_tasks,
                "failed_7d": failed_tasks,
                "pending": pending_tasks,
                "success_rate": (
                    round(
                        completed_tasks
                        / (completed_tasks + failed_tasks)
                        * 100,
                        1,
                    )
                    if (completed_tasks + failed_tasks) > 0
                    else 0
                ),
                "avg_completion_time_minutes": round(avg_completion_time, 1),
            },
            "performance_indicators": {
                "system_uptime": "operational",
                "response_time": "normal",
                "error_rate": (
                    round(failed_tasks / len(recent_tasks) * 100, 1)
                    if recent_tasks
                    else 0
                ),
            },
        }

        return {
            "success": True,
            "statistics": statistics,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate system statistics",
        }


@app.get("/api/system/activity")
async def get_system_activity():
    """Get recent system activity for activity feed"""
    db = await get_database()

    try:
        # Get recent agent tasks
        from datetime import datetime, timedelta

        recent_limit = datetime.utcnow() - timedelta(hours=24)
        recent_tasks = await db.get_tasks_since(recent_limit, limit=20)

        activity_feed = []

        for task in recent_tasks:
            activity_item = {
                "id": str(task.id),
                "type": "agent_task",
                "title": (
                    task.task_type[:80] + "..."
                    if len(task.task_type) > 80
                    else task.task_type
                ),
                "status": task.status.value if task.status else "unknown",
                "timestamp": (
                    task.created_at.isoformat() if task.created_at else None
                ),
                "duration_minutes": None,
                "agent_role": task.assigned_role or "unknown",
            }

            # Calculate duration for completed tasks
            if task.completed_at and task.created_at:
                duration = (
                    task.completed_at - task.created_at
                ).total_seconds() / 60
                activity_item["duration_minutes"] = round(duration, 1)

            activity_feed.append(activity_item)

        # Sort by timestamp (most recent first)
        activity_feed.sort(key=lambda x: x["timestamp"] or "", reverse=True)

        return {
            "success": True,
            "activity": activity_feed[:15],  # Limit to 15 most recent
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch system activity",
        }


@app.get("/api/charts/task-timeline")
async def get_task_timeline_data():
    """Get task timeline data for charts"""
    db = await get_database()

    try:
        from datetime import datetime, timedelta

        # Get agent tasks from last 7 days grouped by day
        days_data = []

        for i in range(7):
            day_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            day_tasks = await db.get_tasks_between(day_start, day_end)

            day_stats = {
                "date": day_start.strftime("%Y-%m-%d"),
                "day_name": day_start.strftime("%a"),
                "total": len(day_tasks),
                "completed": len(
                    [t for t in day_tasks if t.status == "completed"]
                ),
                "failed": len([t for t in day_tasks if t.status == "failed"]),
                "pending": len(
                    [t for t in day_tasks if t.status == "pending"]
                ),
                "running": len(
                    [t for t in day_tasks if t.status == "running"]
                ),
            }

            days_data.append(day_stats)

        # Reverse to get chronological order
        days_data.reverse()

        return {
            "success": True,
            "timeline": days_data,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate timeline data",
        }


@app.get("/api/charts/agent-performance")
async def get_agent_performance_data():
    """Get agent performance data for charts"""
    db = await get_database()

    try:
        agents = await db.get_all_agents()

        if not agents:
            return {
                "success": True,
                "performance": {
                    "role_distribution": [],
                    "status_distribution": [],
                    "success_rates": [],
                },
                "message": "No agents registered yet",
            }

        # Role distribution
        role_counts = {}
        status_counts = {}

        for agent in agents:
            # Count roles
            for role in agent.agent_info.get("roles", []):
                role_counts[role] = role_counts.get(role, 0) + 1

            # Count statuses
            status = agent.status.value if agent.status else "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        # Convert to chart format
        role_distribution = [
            {"role": role, "count": count}
            for role, count in role_counts.items()
        ]

        status_distribution = [
            {"status": status, "count": count}
            for status, count in status_counts.items()
        ]

        # Success rates by role
        success_rates = []
        role_performance = {}

        for agent in agents:
            for role in agent.agent_info.get("roles", []):
                if role not in role_performance:
                    role_performance[role] = {"completed": 0, "failed": 0}

                role_performance[role]["completed"] += agent.tasks_completed
                role_performance[role]["failed"] += agent.tasks_failed

        for role, performance in role_performance.items():
            total = performance["completed"] + performance["failed"]
            success_rate = (
                (performance["completed"] / total * 100) if total > 0 else 0
            )
            success_rates.append(
                {"role": role, "success_rate": round(success_rate, 1)}
            )

        return {
            "success": True,
            "performance": {
                "role_distribution": role_distribution,
                "status_distribution": status_distribution,
                "success_rates": success_rates,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate performance data",
        }


# Main execution
if __name__ == "__main__":
    import uvicorn

    # Bootstrap and load environment
    bootstrap_dependencies()
    load_environment()

    print("Starting Summit Autonomous AI...")
    print("Web interface: http://localhost:8000")
    print("API documentation: http://localhost:8000/docs")

    # Kill any existing server before starting
    kill_existing_server()

    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
