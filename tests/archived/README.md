# Archived Tests

This directory contains test files that have been archived due to one of the following reasons:

1. They tested functionality that has been replaced or significantly refactored
2. They were dependent on deprecated APIs or implementation details
3. They have been superseded by newer, more comprehensive tests

## FastMCP Migration

The following tests were archived during the FastMCP migration because they were dependent on the old MCP server implementation:

- `test_mcp_task_management.py`: Tests for MCP task management features using the deprecated `handle_call_tool` function
- `test_task_lifecycle.py`: Task lifecycle tests using the old MCP API
- `test_summit.py`: Tests for the original Summit MCP server implementation
- `test_soundcloud_integration.py`: Tests for a deprecated integration

These tests have been replaced by:

- `test_mcp_tools.py`: Updated to test the FastMCP implementation directly
- `test_summit_basic.py`: Updated to test the FastMCP server basic functionality

## Maintenance

Tests in this directory should be periodically reviewed to determine if:

1. They can be updated and moved back to the main test directory
2. They should be permanently removed when the code they tested is fully deprecated
3. They provide historical value for understanding past implementation details

No new tests should be added to this directory. If a test is no longer needed, it should be moved here rather than deleted.

## Purpose

Test files should **never be deleted** from the Summit project as they provide critical validation and documentation of expected behavior. Instead of deletion, obsolete tests are moved here.

## When to Archive Tests

- When test files become obsolete due to major refactoring
- When functionality is completely removed but tests provide valuable documentation
- When tests need to be temporarily disabled but preserved for future reference

## Guidelines

- Maintain the original directory structure when archiving
- Add a comment at the top of archived test files explaining why they were archived
- Include the date of archiving and the commit/PR that archived them
- Consider updating archived tests before reactivating them

## Reactivating Tests

To reactivate an archived test:
1. Review and update the test for current codebase
2. Move it back to the appropriate location in `tests/`
3. Ensure it passes with current code
4. Update any outdated assertions or mocks 