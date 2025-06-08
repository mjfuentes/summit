#!/usr/bin/env python3
"""
Cloud Tasks CLI - Command line interface for Summit Cloud Tasks management
"""
from cloud_task_manager import CloudTaskManager, TaskPriority
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

import click

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@click.group()
@click.option(
    "--project-id", default="summit-ai-platform", help="GCP Project ID"
)
@click.option("--location", default="us-central1", help="GCP Location")
@click.option("--queue-name", default="summit-agent-queue", help="Queue name")
@click.pass_context
def cli(ctx, project_id, location, queue_name):
    """Summit Cloud Tasks CLI"""
    ctx.ensure_object(dict)
    ctx.obj["task_manager"] = CloudTaskManager(
        project_id=project_id, location=location, queue_name=queue_name
    )


@cli.command()
@click.pass_context
async def init(ctx):
    """Initialize Cloud Tasks queue and Firestore"""
    task_manager = ctx.obj["task_manager"]

    try:
        await task_manager.initialize()
        click.echo(" Cloud Tasks queue and Firestore initialized successfully")
    except Exception as e:
        click.echo(f" Initialization failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("task_type")
@click.argument("payload_json")
@click.option(
    "--priority",
    default="normal",
    type=click.Choice(["low", "normal", "high", "urgent"]),
)
@click.option("--delay", default=0, help="Delay in seconds")
@click.pass_context
async def submit(ctx, task_type, payload_json, priority, delay):
    """Submit a new task"""
    task_manager = ctx.obj["task_manager"]

    try:
        # Parse payload JSON
        payload = json.loads(payload_json)

        # Convert priority
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT,
        }

        task_id = await task_manager.submit_task(
            task_type=task_type,
            payload=payload,
            priority=priority_map[priority],
            delay_seconds=delay,
        )

        click.echo(f" Task submitted: {task_id}")
        click.echo(f"  Type: {task_type}")
        click.echo(f"  Priority: {priority}")
        if delay > 0:
            click.echo(f"  Delay: {delay} seconds")

    except json.JSONDecodeError:
        click.echo(" Invalid JSON payload", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f" Task submission failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("task_id")
@click.pass_context
async def status(ctx, task_id):
    """Get task status"""
    task_manager = ctx.obj["task_manager"]

    try:
        task = await task_manager.get_task_status(task_id)

        if not task:
            click.echo(f" Task {task_id} not found", err=True)
            sys.exit(1)

        click.echo(f"Task: {task.id}")
        click.echo(f"  Type: {task.type}")
        click.echo(f"  Status: {task.status.value}")
        click.echo(f"  Priority: {task.priority.name}")
        click.echo(f"  Created: {task.created_at}")

        if task.agent_id:
            click.echo(f"  Agent: {task.agent_id}")

        if task.started_at:
            click.echo(f"  Started: {task.started_at}")

        if task.completed_at:
            click.echo(f"  Completed: {task.completed_at}")
            duration = (task.completed_at - task.started_at).total_seconds()
            click.echo(f"  Duration: {duration:.2f}s")

        if task.result:
            click.echo("  Result:")
            click.echo(f"    {json.dumps(task.result, indent=4)}")

        if task.error:
            click.echo(f"  Error: {task.error}")

    except Exception as e:
        click.echo(f" Failed to get task status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
async def stats(ctx):
    """Get queue statistics"""
    task_manager = ctx.obj["task_manager"]

    try:
        stats = await task_manager.get_queue_stats()
        agents = await task_manager.list_active_agents()

        click.echo("Queue Statistics:")
        click.echo(f"  Queue: {stats.get('queue_name', 'unknown')}")
        click.echo(f"  State: {stats.get('queue_state', 'unknown')}")
        click.echo(
            f"  Max Dispatches/sec: {stats.get('max_dispatches_per_second', 0)}"
        )
        click.echo(
            f"  Max Concurrent: {stats.get('max_concurrent_dispatches', 0)}"
        )
        click.echo()

        click.echo("Task Counts:")
        click.echo(f"  Pending: {stats.get('pending', 0)}")
        click.echo(f"  Running: {stats.get('running', 0)}")
        click.echo(f"  Completed: {stats.get('completed', 0)}")
        click.echo(f"  Failed: {stats.get('failed', 0)}")
        click.echo()

        click.echo("Agents:")
        click.echo(f"  Total: {len(agents)}")
        active_agents = [
            a for a in agents if a.get("status") in ["ready", "busy"]
        ]
        click.echo(f"  Active: {len(active_agents)}")

        if active_agents:
            click.echo("  Active Agents:")
            for agent in active_agents:
                status_icon = "" if agent.get("status") == "ready" else ""
                click.echo(
                    f"    {status_icon} {agent.get('agent_id', 'unknown')} ({agent.get('status', 'unknown')})"
                )
                if agent.get("current_task"):
                    click.echo(f"      Current task: {agent['current_task']}")

    except Exception as e:
        click.echo(f" Failed to get statistics: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
async def agents(ctx):
    """List all agents"""
    task_manager = ctx.obj["task_manager"]

    try:
        agents = await task_manager.list_active_agents()

        if not agents:
            click.echo("No active agents found")
            return

        click.echo(f"Active Agents ({len(agents)}):")
        click.echo()

        for agent in agents:
            status = agent.get("status", "unknown")
            status_icon = {"ready": "", "busy": "", "offline": ""}.get(
                status, ""
            )

            click.echo(f"{status_icon} {agent.get('agent_id', 'unknown')}")
            click.echo(f"  Status: {status}")

            if agent.get("hostname"):
                click.echo(f"  Hostname: {agent['hostname']}")

            if agent.get("current_task"):
                click.echo(f"  Current Task: {agent['current_task']}")

            if agent.get("registered_at"):
                uptime = datetime.utcnow() - agent["registered_at"]
                click.echo(f"  Uptime: {uptime}")

            if agent.get("capabilities"):
                click.echo(
                    f"  Capabilities: {', '.join(agent['capabilities'])}"
                )

            click.echo()

    except Exception as e:
        click.echo(f" Failed to list agents: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--days", default=7, help="Delete tasks older than N days")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
async def cleanup(ctx, days, confirm):
    """Clean up old completed/failed tasks"""
    task_manager = ctx.obj["task_manager"]

    if not confirm:
        click.confirm(f"Delete tasks older than {days} days?", abort=True)

    try:
        await task_manager.cleanup_old_tasks(days=days)
        click.echo(f" Cleaned up tasks older than {days} days")

    except Exception as e:
        click.echo(f" Cleanup failed: {e}", err=True)
        sys.exit(1)


@cli.group()
def examples():
    """Example task submissions"""
    pass


@examples.command()
@click.option("--files", multiple=True, help="Files to analyze")
@click.pass_context
async def code_analysis(ctx, files):
    """Submit code analysis task"""
    task_manager = ctx.obj["task_manager"]

    payload = {"files": list(files) if files else ["src/"]}

    try:
        task_id = await task_manager.submit_task(
            task_type="code_analysis",
            payload=payload,
            priority=TaskPriority.NORMAL,
        )

        click.echo(f" Code analysis task submitted: {task_id}")
        click.echo(f"  Files: {', '.join(payload['files'])}")

    except Exception as e:
        click.echo(f" Failed to submit code analysis: {e}", err=True)


@examples.command()
@click.option("--test-files", multiple=True, help="Specific test files to run")
@click.pass_context
async def run_tests(ctx, test_files):
    """Submit test execution task"""
    task_manager = ctx.obj["task_manager"]

    payload = {"test_files": list(test_files) if test_files else []}

    try:
        task_id = await task_manager.submit_task(
            task_type="run_tests",
            payload=payload,
            priority=TaskPriority.NORMAL,
        )

        click.echo(f" Test execution task submitted: {task_id}")
        if test_files:
            click.echo(f"  Test files: {', '.join(test_files)}")
        else:
            click.echo("  Running all tests")

    except Exception as e:
        click.echo(f" Failed to submit test execution: {e}", err=True)


@examples.command()
@click.argument("pr_number", type=int)
@click.option("--files", multiple=True, help="Files to review")
@click.pass_context
async def pr_review(ctx, pr_number, files):
    """Submit PR review task"""
    task_manager = ctx.obj["task_manager"]

    payload = {"pr_number": pr_number, "files": list(files) if files else []}

    try:
        task_id = await task_manager.submit_task(
            task_type="pr_review", payload=payload, priority=TaskPriority.HIGH
        )

        click.echo(f" PR review task submitted: {task_id}")
        click.echo(f"  PR Number: {pr_number}")
        if files:
            click.echo(f"  Files: {', '.join(files)}")

    except Exception as e:
        click.echo(f" Failed to submit PR review: {e}", err=True)


def run_async_command(func):
    """Decorator to run async commands"""

    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


# Apply async decorator to all async commands
for command_name in ["init", "submit", "status", "stats", "agents", "cleanup"]:
    if command_name in cli.commands:
        command = cli.commands[command_name]
        command.callback = run_async_command(command.callback)

for command_name in ["code_analysis", "run_tests", "pr_review"]:
    if command_name in examples.commands:
        command = examples.commands[command_name]
        command.callback = run_async_command(command.callback)


if __name__ == "__main__":
    cli()
