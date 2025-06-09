# FastMCP 2.0 Tests

This directory contains tests for FastMCP 2.0 integration with Summit.

## Files

- `fastmcp_only_test.py`: Standalone test for FastMCP 2.0 without external dependencies

## Running Tests

To run the FastMCP test:

```bash
python tests/fastmcp/fastmcp_only_test.py
```

This will test the basic functionality of FastMCP 2.0 integration, including:
- Resource registration
- Tool registration
- Server initialization
- Mock database integration

The test uses in-memory mocks to avoid dependencies on external systems. 