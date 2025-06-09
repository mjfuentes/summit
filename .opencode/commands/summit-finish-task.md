# Summit Task Completion

When you have completed a task, use this command structure:

**For Successful Completion:**
Use the summit_update_task_status MCP tool with:
- task_id: The ID of the task you completed
- status: "completed" 
- agent_id: Your agent identifier
- result: Object containing:
  - success: true
  - summary: Brief description of what was accomplished
  - files_modified: List of files changed
  - tests_run: Whether tests were executed
  - coverage: Test coverage percentage if available
  - quality_checks: Whether linting/formatting was applied

**For Failed Tasks:**
Use the summit_update_task_status MCP tool with:
- task_id: The ID of the task that failed
- status: "failed"
- agent_id: Your agent identifier  
- error: Clear error message explaining what went wrong

**Example Usage:**
```
summit_update_task_status({
  "task_id": "task-123",
  "status": "completed",
  "agent_id": "opencode-agent-1",
  "result": {
    "success": true,
    "summary": "Implemented authentication system with JWT tokens",
    "files_modified": ["src/auth.py", "tests/test_auth.py"],
    "tests_run": true,
    "coverage": 85.3,
    "quality_checks": true
  }
})
```

**Never use manual database calls or direct API endpoints for task completion.**