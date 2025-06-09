# Migration to FastMCP Server

## Overview

Summit has migrated from a custom MCP server implementation to a modern FastMCP-based architecture. This document outlines the changes made and provides guidance for developers working with the new system.

## Key Changes

1. **New Server Implementation**: 
   - Replaced `src/mcp_server.py` with `src/fastmcp_server.py`
   - Uses FastMCP framework (version 0.4.1+) for standardized server implementation
   - Supports multiple transport protocols (stdio, SSE, streamable-http)

2. **New Client Implementation**:
   - Replaced `src/summit_mcp_client.py` with `src/summit_client.py`
   - Provides a modern async context manager interface
   - Supports all server functionality with clean API

3. **Backward Compatibility**:
   - `src/summit.py` maintained as a wrapper that redirects to FastMCP server
   - Existing integrations continue to work without changes
   - Legacy code shows deprecation warnings

4. **Infrastructure Updates**:
   - Updated Kubernetes deployment to use new FastMCP server
   - Updated Docker container configuration
   - Added start script (`start_mcp_server.sh`) for easy server launching

5. **Tests**:
   - Updated test files to directly test FastMCP endpoints
   - Removed obsolete test files

## FastMCP Advantages

FastMCP provides several advantages over the custom implementation:

- **Multiple Transport Protocols**: Support for stdio (CLI), SSE (browsers), and streamable-http (modern clients)
- **Structured Progress Reporting**: Real-time progress updates to clients
- **Typesafe Request Validation**: Pydantic models for request validation
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Resource Management**: Clean startup and shutdown handlers
- **Documentation Resources**: Built-in documentation endpoints

## Server Configuration

The FastMCP server can be configured using environment variables:

```bash
# Transport protocol (stdio, sse, streamable-http)
export MCP_TRANSPORT="sse"

# Server host and port (for network transports)
export HOST="0.0.0.0"
export PORT="8080"
```

## Starting the Server

Use the provided script to start the server:

```bash
# Start with default settings (SSE transport on port 8080)
./start_mcp_server.sh

# Start with specific transport
./start_mcp_server.sh --transport streamable-http --port 8000

# Start in stdio mode (for CLI use)
./start_mcp_server.sh --transport stdio
```

## Client Usage

The new client provides a simple async interface:

```python
from src.summit_client import SummitClient

async def example():
    async with SummitClient() as client:
        # Register an agent
        reg_response = await client.register_agent(
            agent_id="example-agent",
            role="engineering",
            capabilities=["coding", "testing"]
        )
        
        # Get a task
        task_response = await client.get_next_task(
            agent_id="example-agent",
            role="engineering"
        )
        
        # Complete a task
        if task_response.get("status") == "success" and "task" in task_response:
            task_id = task_response["task"]["id"]
            await client.complete_task(
                task_id=task_id,
                agent_id="example-agent",
                success=True,
                summary="Task completed successfully",
                files_modified=["example.py"]
            )
```

## Future Plans

1. **Complete Deprecation**:
   - The legacy `summit.py` wrapper will be completely removed in a future version
   - All code should migrate to using FastMCP directly

2. **Additional Features**:
   - Enhanced monitoring and metrics collection
   - More specialized agent tools
   - Improved error handling and retry mechanisms

3. **Client Libraries**:
   - Language-specific client libraries for Python, JavaScript, and other languages
   - Enhanced developer tooling and debugging helpers

## Migration Checklist

If you're updating existing code to use the new system:

1. Replace imports from `summit_mcp_client` with `summit_client`
2. Update client instantiation to use async context manager pattern
3. Replace `call_tool()` with direct method calls
4. Update response parsing to use structured JSON responses
5. Use typehints for better developer experience

## Architecture Diagram

```
       
                                            
   Summit Agent     Summit Client    
                                            
       
                                    
                                    
                                    
                          
                                              
                             FastMCP Server   
                                              
                          
                                    
                                    
                                    
                          
                                              
                             Task Queue Mgr   
                                              
                          
                                    
                                    
                                    
                  
                                                          
                PostgreSQL DB            Cloud Tasks      
                                                          
                  
``` 