# Agent Roles and Role-Based Task Distribution

## Overview

Summit supports a simple role-based task distribution system that allows for specialized agent types to handle different kinds of tasks. This document explains how the role system works and how to use it effectively.

## Key Concepts

### Agent Roles

Agents in Summit identify themselves with a single role that defines what types of tasks they can perform. Standard roles include:

- `engineering` - General code development tasks
- `code_review` - Code quality and review tasks
- `testing` - Test creation and validation
- `documentation` - Documentation creation and updates
- `devops` - Deployment and infrastructure tasks
- `security` - Security audits and fixes
- `design` - UI/UX design work

### Task Assignment

When a task is created, it is assigned to a specific role (e.g., `code_review`, `engineering`). The task will only be available to agents that request tasks for that role.

Tasks are prioritized within each role's queue based on:
1. Priority level (URGENT, HIGH, NORMAL, LOW)
2. Creation time (older tasks are prioritized)

## Using Role-Based Tasks

### Creating Tasks for Specific Roles

When creating a task, specify the `assigned_role` parameter to target agents with that role:

```python
task_id = await task_queue_manager.submit_task(
    task_type="code_review",
    payload={
        "pr_number": 123,
        "branch_name": "feature/new-capability",
    },
    priority=TaskPriority.HIGH,
    assigned_role="code_review",  # Targets code review agents
)
```

### Getting Tasks for a Specific Role

Agents request tasks for a specific role:

```python
# Agent requests a task for a specific role
task = await mcp_client.call_tool(
    "summit_get_next_task",
    {
        "agent_id": "agent123",
        "role": "code_review",
    }
)
```

### Completing Tasks

When an agent completes a task, it simply marks it as complete:

```python
await mcp_client.call_tool(
    "summit_complete_task",
    {
        "task_id": "task123",
        "agent_id": "agent123",
        "success": True,
        "result": {"pr_approved": True}
    }
)
```

## Database Schema

Role-based task assignment is stored in the database:

- `AgentTask.assigned_role` - The role required to work on this task

## Future Improvements

**TODO:** The current implementation uses database querying for role-based task distribution. Future improvements will include:

1. Redis-based queue system with dedicated queues per role
2. Pub/Sub notification system for new tasks
3. Real-time task distribution without polling

These improvements will be implemented to enhance scalability and responsiveness of the task distribution system. 