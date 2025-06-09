# Summit Feature Implementation

Please implement the requested feature following these guidelines:

1. **Analysis Phase:**
   - Use summit_get_task to understand requirements
   - Explore existing codebase patterns
   - Identify integration points

2. **Implementation Phase:**
   - Follow existing code patterns
   - Maintain code quality standards
   - Add comprehensive tests
   - Update documentation

3. **Quality Assurance:**
   - Run tests and ensure >70% coverage
   - Apply code formatting (Black, isort)
   - Fix any linting issues
   - Verify functionality

4. **Task Completion:**
   - When finished, use summit_update_task_status tool to mark task as "completed"
   - Include task result data with implementation details
   - If task fails, use summit_update_task_status with "failed" status and error message

5. **Integration:**
   - Ensure proper error handling
   - Add logging where appropriate
   - Follow Summit's professional standards

**Important:** Always use the summit_update_task_status MCP tool to update task status instead of manual database calls.

Use the available tools to read, write, and test code as needed.