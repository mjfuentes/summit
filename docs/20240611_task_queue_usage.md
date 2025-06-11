# Summit Task Queue System

## Overview

The Summit Task Queue System provides a hybrid approach to task distribution, combining:

1. **PostgreSQL Database** - For reliable task storage and state management
2. **Google Cloud Tasks** - For scalable task distribution and delivery
3. **FastMCP Server API** - For task creation, assignment, and completion

This architecture provides several advantages:
- Database as single source of truth for task state
- Reliable atomic task claiming to prevent race conditions
- Scalable task distribution with automatic retries
- Per-role task queues for better organization
- Deterministic task assignment based on priority
- Support for agent role specialization

## Agent Role Support

Summit now supports role-based task distribution, allowing agents to specialize in different types of tasks:

- Agents can declare multiple roles in order of preference
- Tasks are assigned to specific roles (e.g., "engineering", "code_review")
- Agents receive tasks from their preferred roles first
- See [AGENT_ROLES.md](AGENT_ROLES.md) for detailed documentation on the role system

> **TODO**: Future versions will replace the current database polling approach with a more efficient Redis-based queue system or Pub/Sub for better scalability.

## Key Components

### Task Queue Manager

The Task Queue Manager (`src/task_queue_manager.py`) handles the integration between PostgreSQL and Cloud Tasks:

- Creates and manages per-role Cloud Tasks queues
- Submits tasks to the appropriate queue
- Handles task claiming through atomic database operations
- Tracks task completion and lifecycle stages

### FastMCP Server API

The FastMCP Server provides the following tools for task management:

- `summit_get_next_task` - Get the next highest priority task for an agent based on its role
- `summit_complete_task` - Complete a task with results or error information
- `summit_register_agent` - Register a new agent with the platform

The server uses the FastMCP framework which provides:
- Multiple transport protocols (stdio, SSE, streamable-http)
- Structured progress reporting
- Typesafe request validation with Pydantic
- Comprehensive logging and error handling

### Agent Endpoints Server

The Agent Endpoints server (`web/agent_endpoints.py`) provides an HTTP endpoint that receives task assignments from Cloud Tasks and makes them available for assignment.

## Task Lifecycle

1. **Task Creation**
   - Task is created in database with PENDING status
   - Task is submitted to Cloud Tasks queue for the assigned role

2. **Task Distribution**
   - Cloud Tasks delivers the task to the Agent Endpoints server
   - Tasks are made available for assignment in the database

3. **Task Assignment**
   - Agent calls `summit_get_next_task` with their role(s)
   - System automatically selects and assigns highest priority task
   - Task is atomically claimed and status changes to RUNNING

4. **Task Execution**
   - Agent performs the task
   - Progress can be tracked through stage transitions

5. **Task Completion**
   - Agent completes task via `summit_complete_task`
   - Task status changes to COMPLETED or FAILED
   - Results are recorded in the database

## Usage Examples

### Task Submission

```python
from src.database_models import TaskPriority
from src.task_queue_manager import get_task_queue_manager

async def submit_code_review_task(pr_number, branch_name):
    # Get task queue manager
    task_queue_manager = await get_task_queue_manager()
    
    # Submit task
    task_id = await task_queue_manager.submit_task(
        task_type="code_review",
        payload={
            "pr_number": pr_number,
            "branch_name": branch_name,
        },
        priority=TaskPriority.HIGH,
        assigned_role="quality",
        delay_seconds=0,
    )
    
    return task_id
```

### Getting and Starting Tasks

```python
from src.summit_client import SummitClient

async def get_next_task(agent_id, role):
    # Initialize Summit client
    async with SummitClient() as client:
        # Get the next task for this role
        response = await client.get_next_task(
            agent_id=agent_id,
            role=role  # e.g., "engineering"
        )
        
        # Check if a task was assigned
        if response.get("status") == "success" and "task" in response:
            task = response["task"]
            return task["id"]
        
        return None
```

### Completing Tasks

```python
from src.summit_client import SummitClient

async def complete_task(task_id, agent_id, success=True, result=None):
    # Initialize Summit client
    async with SummitClient() as client:
        # Complete the task
        response = await client.complete_task(
            task_id=task_id,
            agent_id=agent_id,
            success=success,
            result=result or {},
            summary="Task execution completed",
            files_modified=["file1.py", "file2.py"],
            error_message="" if success else "Task failed"
        )
        
        return response.get("status") == "success"
```

## Running the System

The system can be run using Docker Compose:

```bash
# Start the system
docker-compose up -d

# Start the FastMCP server directly
./start_mcp_server.sh

# Start with specific transport
./start_mcp_server.sh --transport sse --port 8080

# Submit a test task
python scripts/submit_test_task.py --type test_task --role engineering --priority high

# Test the full task lifecycle
python scripts/test_task_lifecycle.py
```

## Configuration

The system can be configured using environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GCP_LOCATION` - Google Cloud region
- `AGENT_ENDPOINT_URL` - URL of the Agent Endpoints server
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google Cloud credentials file
- `MCP_TRANSPORT` - Transport protocol (stdio, sse, streamable-http)
- `PORT` - Port number for the FastMCP server
- `HOST` - Host address for the FastMCP server

## Monitoring

The task queue system provides logging for monitoring:

- Task submission logs
- Task claiming logs
- Task completion logs
- Cloud Tasks queue creation logs
- Error logs for failed operations

Additionally, Cloud Tasks provides monitoring metrics through Google Cloud Monitoring. 